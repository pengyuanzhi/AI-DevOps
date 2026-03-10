"""
历史数据分析器

分析测试历史执行数据，优化测试选择策略
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

from ....services.test.registry import TestRegistry, TestMetadata
from ....core.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TestHistory:
    """测试历史记录"""
    test_id: str
    test_name: str

    # 执行历史
    total_runs: int = 0
    passed_runs: int = 0
    failed_runs: int = 0
    flaky_runs: int = 0  # 成功后又失败的次数

    # 时间统计
    avg_duration_ms: float = 0.0
    last_run: Optional[datetime] = None
    last_status: Optional[str] = None

    # 失败模式
    recent_failures: List[datetime] = field(default_factory=list)
    common_failures: Dict[str, int] = field(default_factory=dict)  # 失败原因 -> 次数

    # 变更关联
    associated_files: Set[str] = field(default_factory=set)  # 经常一起变更的文件
    associated_tests: Set[str] = field(default_factory=set)  # 经常一起失败的测试


@dataclass
class TestImpact:
    """测试影响评估"""
    test_id: str
    test_name: str

    # 影响评分 (0-100)
    impact_score: float = 0.0

    # 各维度评分
    failure_probability: float = 0.0  # 失败概率
    execution_time: float = 0.0  # 执行时间（归一化）
    coverage_importance: float = 0.0  # 覆盖重要性
    regression_risk: float = 0.0  # 回归风险

    # 建议
    priority: str = "medium"  # critical, high, medium, low
    reason: str = ""


class HistoricalAnalyzer:
    """
    历史数据分析器

    分析测试历史执行数据，提供智能建议。
    """

    def __init__(self):
        self.histories: Dict[str, TestHistory] = {}
        self.analysis_window_days = 30  # 分析窗口（天）

    def load_from_registry(self, registry: TestRegistry) -> None:
        """
        从测试注册中心加载历史数据

        Args:
            registry: 测试注册中心
        """
        tests = registry.get_all_tests()

        for test in tests:
            history = TestHistory(
                test_id=test.test_id,
                test_name=test.name,
                total_runs=test.total_runs,
                passed_runs=test.passed_runs,
                failed_runs=test.failed_runs,
                flaky_runs=test.flaky_count,
                avg_duration_ms=test.avg_duration_ms,
                last_run=test.last_run,
                last_status=test.last_status.value if test.last_status else None,
                associated_files=set(test.source_files),
            )

            self.histories[test.test_id] = history

        logger.info(
            "historical_data_loaded",
            total_tests=len(tests),
            window_days=self.analysis_window_days,
        )

    def analyze_test_impact(
        self,
        test_ids: List[str],
        changed_files: Set[str],
        registry: TestRegistry,
    ) -> List[TestImpact]:
        """
        分析测试影响

        Args:
            test_ids: 测试ID列表
            changed_files: 变更的文件
            registry: 测试注册中心

        Returns:
            测试影响评估列表
        """
        impacts = []

        for test_id in test_ids:
            test = registry.get_test(test_id)
            history = self.histories.get(test_id)

            if not test or not history:
                continue

            impact = TestImpact(
                test_id=test_id,
                test_name=test.name,
            )

            # 计算各维度评分
            impact.failure_probability = self._calculate_failure_probability(history)
            impact.execution_time = self._normalize_execution_time(history.avg_duration_ms)
            impact.coverage_importance = self._calculate_coverage_importance(test, changed_files)
            impact.regression_risk = self._calculate_regression_risk(history, changed_files)

            # 综合评分（加权平均）
            impact.impact_score = (
                impact.failure_probability * 0.4 +
                impact.execution_time * 0.1 +
                impact.coverage_importance * 0.3 +
                impact.regression_risk * 0.2
            )

            # 确定优先级
            impact.priority = self._determine_priority(impact.impact_score)
            impact.reason = self._generate_reason(impact, history, changed_files)

            impacts.append(impact)

        # 按影响评分排序
        impacts.sort(key=lambda x: x.impact_score, reverse=True)

        return impacts

    def find_flaky_tests(
        self,
        registry: TestRegistry,
        min_runs: int = 10,
        flaky_threshold: float = 0.3,
    ) -> List[TestHistory]:
        """
        查找不稳定测试

        Args:
            registry: 测试注册中心
            min_runs: 最少运行次数
            flaky_threshold: 不稳定阈值（失败后通过的比例）

        Returns:
            不稳定测试列表
        """
        flaky_tests = []

        for test in registry.get_all_tests():
            if test.total_runs < min_runs:
                continue

            history = self.histories.get(test.test_id)
            if not history:
                continue

            # 计算不稳定率
            if history.flaky_runs > 0:
                flaky_rate = history.flaky_runs / history.total_runs
                if flaky_rate >= flaky_threshold:
                    flaky_tests.append(history)

        flaky_tests.sort(key=lambda x: x.flaky_runs, reverse=True)

        logger.info(
            "flaky_tests_found",
            count=len(flaky_tests),
            min_runs=min_runs,
            threshold=flaky_threshold,
        )

        return flaky_tests

    def find_slow_tests(
        self,
        registry: TestRegistry,
        threshold_ms: float = 5000,
    ) -> List[TestHistory]:
        """
        查找慢速测试

        Args:
            registry: 测试注册中心
            threshold_ms: 时间阈值（毫秒）

        Returns:
            慢速测试列表
        """
        slow_tests = []

        for test in registry.get_all_tests():
            if test.avg_duration_ms >= threshold_ms:
                history = self.histories.get(test.test_id)
                if history:
                    slow_tests.append(history)

        slow_tests.sort(key=lambda x: x.avg_duration_ms, reverse=True)

        logger.info(
            "slow_tests_found",
            count=len(slow_tests),
            threshold_ms=threshold_ms,
        )

        return slow_tests

    def get_test_correlations(
        self,
        test_id: str,
        registry: TestRegistry,
    ) -> Dict[str, float]:
        """
        获取测试关联度

        找出经常一起失败或一起通过的测试

        Args:
            test_id: 测试ID
            registry: 测试注册中心

        Returns:
            测试ID -> 关联度 (0-1)
        """
        target = self.histories.get(test_id)
        if not target:
            return {}

        correlations = {}

        # 基于共同失败文件计算关联
        for other_id, other in self.histories.items():
            if other_id == test_id:
                continue

            # 计算文件关联度
            common_files = target.associated_files & other.associated_files
            if common_files:
                correlation = len(common_files) / max(
                    len(target.associated_files),
                    len(other.associated_files),
                    1
                )
                correlations[other_id] = correlation

        # 按关联度排序
        correlations = dict(sorted(correlations.items(), key=lambda x: x[1], reverse=True))

        return correlations

    def predict_failure_probability(
        self,
        test_id: str,
        changed_files: Set[str],
    ) -> float:
        """
        预测测试失败概率

        Args:
            test_id: 测试ID
            changed_files: 变更的文件

        Returns:
            失败概率 (0-1)
        """
        history = self.histories.get(test_id)
        if not history:
            return 0.5  # 未知测试，中等概率

        # 基础失败率
        base_rate = history.failed_runs / max(history.total_runs, 1)

        # 如果变更的文件与测试相关，增加失败概率
        file_impact = 0.0
        if changed_files & history.associated_files:
            file_impact = 0.3

        # 如果最近有失败记录，增加失败概率
        recent_failure_boost = 0.0
        if history.recent_failures:
            recent_failure_boost = min(len(history.recent_failures) * 0.1, 0.3)

        # 综合预测
        probability = min(base_rate + file_impact + recent_failure_boost, 1.0)

        return probability

    def _calculate_failure_probability(self, history: TestHistory) -> float:
        """计算失败概率 (0-100)"""
        if history.total_runs == 0:
            return 50.0  # 未知测试

        failure_rate = history.failed_runs / history.total_runs

        # 考虑不稳定性
        if history.flaky_runs > 0:
            flaky_penalty = history.flaky_runs / history.total_runs * 20
            failure_rate = min(failure_rate + flaky_penalty, 1.0)

        return min(failure_rate * 100, 100.0)

    def _normalize_execution_time(self, duration_ms: float) -> float:
        """
        归一化执行时间 (0-100)

        越快的测试得分越高
        """
        # 使用对数缩放
        # 0ms -> 100分
        # 100ms -> 90分
        # 1000ms -> 70分
        # 10000ms -> 50分
        # 超过10000ms -> 低分

        if duration_ms <= 0:
            return 100.0

        if duration_ms < 100:
            return 100.0 - (duration_ms / 100) * 10
        elif duration_ms < 1000:
            return 90.0 - ((duration_ms - 100) / 900) * 20
        elif duration_ms < 10000:
            return 70.0 - ((duration_ms - 1000) / 9000) * 20
        else:
            return max(50.0 - ((duration_ms - 10000) / 90000) * 30, 10.0)

    def _calculate_coverage_importance(
        self,
        test: TestMetadata,
        changed_files: Set[str],
    ) -> float:
        """
        计算覆盖重要性 (0-100)

        测试覆盖了越多的变更文件，得分越高
        """
        if not changed_files:
            return 50.0

        covered_files = set(test.source_files) & changed_files

        if not covered_files:
            return 20.0  # 没有覆盖任何变更文件

        # 覆盖比例
        coverage_ratio = len(covered_files) / len(changed_files)

        # 优先级加成
        priority_bonus = {
            "critical": 30,
            "high": 20,
            "medium": 10,
            "low": 0,
        }.get(test.priority.value, 10)

        return min(coverage_ratio * 70 + priority_bonus, 100.0)

    def _calculate_regression_risk(
        self,
        history: TestHistory,
        changed_files: Set[str],
    ) -> float:
        """
        计算回归风险 (0-100)

        基于历史失败模式和变更文件计算
        """
        risk = 0.0

        # 如果变更的文件与历史失败相关
        if changed_files & history.associated_files:
            risk += 40.0

        # 如果最近有失败
        if history.recent_failures:
            recent_failures_count = len(history.recent_failures)
            risk += min(recent_failures_count * 10, 30.0)

        # 如果历史不稳定
        if history.flaky_runs > 0:
            risk += min(history.flaky_runs * 5, 20.0)

        return min(risk, 100.0)

    def _determine_priority(self, impact_score: float) -> str:
        """确定优先级"""
        if impact_score >= 80:
            return "critical"
        elif impact_score >= 60:
            return "high"
        elif impact_score >= 40:
            return "medium"
        else:
            return "low"

    def _generate_reason(
        self,
        impact: TestImpact,
        history: TestHistory,
        changed_files: Set[str],
    ) -> str:
        """生成选择原因"""
        reasons = []

        if impact.failure_probability >= 70:
            reasons.append(f"高失败概率 ({impact.failure_probability:.0f}%)")

        if impact.regression_risk >= 60:
            reasons.append("高回归风险")

        if impact.coverage_importance >= 70:
            reasons.append("覆盖关键变更")

        if history.flaky_runs > 0:
            reasons.append(f"不稳定测试 ({history.flaky_runs}次波动)")

        if history.associated_files & changed_files:
            reasons.append("直接相关文件变更")

        if not reasons:
            reasons.append("常规测试")

        return "; ".join(reasons)

    def save_history(self, output_dir: str) -> None:
        """保存历史数据到文件"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        history_file = output_path / "test_history.json"

        # 转换为可序列化格式
        data = {
            test_id: {
                "test_id": h.test_id,
                "test_name": h.test_name,
                "total_runs": h.total_runs,
                "passed_runs": h.passed_runs,
                "failed_runs": h.failed_runs,
                "flaky_runs": h.flaky_runs,
                "avg_duration_ms": h.avg_duration_ms,
                "last_run": h.last_run.isoformat() if h.last_run else None,
                "last_status": h.last_status,
                "associated_files": list(h.associated_files),
                "associated_tests": list(h.associated_tests),
            }
            for test_id, h in self.histories.items()
        }

        with open(history_file, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info("history_saved", path=str(history_file))

    def load_history(self, input_dir: str) -> None:
        """从文件加载历史数据"""
        history_file = Path(input_dir) / "test_history.json"

        if not history_file.exists():
            logger.warning("history_file_not_found", path=str(history_file))
            return

        with open(history_file, 'r') as f:
            data = json.load(f)

        self.histories = {}
        for test_id, h_data in data.items():
            history = TestHistory(
                test_id=h_data["test_id"],
                test_name=h_data["test_name"],
                total_runs=h_data["total_runs"],
                passed_runs=h_data["passed_runs"],
                failed_runs=h_data["failed_runs"],
                flaky_runs=h_data["flaky_runs"],
                avg_duration_ms=h_data["avg_duration_ms"],
                last_run=datetime.fromisoformat(h_data["last_run"]) if h_data["last_run"] else None,
                last_status=h_data["last_status"],
                associated_files=set(h_data.get("associated_files", [])),
                associated_tests=set(h_data.get("associated_tests", [])),
            )
            self.histories[test_id] = history

        logger.info("history_loaded", path=str(history_file), count=len(self.histories))


# 全局单例
historical_analyzer = HistoricalAnalyzer()
