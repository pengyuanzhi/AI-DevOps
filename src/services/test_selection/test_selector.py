"""
智能测试选择器

整合多种策略，选择最需要运行的测试
"""

from typing import List, Set, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .git_analyzer import GitAnalyzer, FileChange
from .dependency_graph import DependencyGraph, DependencyGraphBuilder
from .historical_analyzer import HistoricalAnalyzer, TestImpact
from ....services.test.base import TestSuite, TestCase, TestStatus
from ....services.test.registry import TestRegistry, TestMetadata, TestPriority
from ....core.logging.logger import get_logger

logger = get_logger(__name__)


class SelectionStrategy(str, Enum):
    """选择策略"""
    CONSERVATIVE = "conservative"  # 保守：选择更多测试
    BALANCED = "balanced"  # 平衡：兼顾速度和准确性
    AGGRESSIVE = "aggressive"  # 激进：选择最少的测试
    FAST_FAIL = "fast_fail"  # 快速失败：优先运行可能失败的测试


@dataclass
class SelectionScore:
    """选择评分"""
    test: TestCase
    score: float
    reason: str

    # 评分明细
    dependency_score: float = 0.0  # 依赖关系得分
    historical_score: float = 0.0  # 历史得分
    coverage_score: float = 0.0  # 覆盖率得分
    priority_score: float = 0.0  # 优先级得分


class SmartTestSelector:
    """
    智能测试选择器

    整合依赖分析、历史数据和优先级，智能选择测试。
    """

    def __init__(self):
        self.git_analyzer = GitAnalyzer()
        self.graph_builder = DependencyGraphBuilder()
        self.historical_analyzer = HistoricalAnalyzer()
        self.dependency_graph: Optional[DependencyGraph] = None

    async def select_tests(
        self,
        repo_path: str,
        source_branch: str,
        target_branch: str,
        all_tests: List[TestSuite],
        registry: TestRegistry,
        strategy: SelectionStrategy = SelectionStrategy.BALANCED,
        dependency_graph: Optional[DependencyGraph] = None,
        max_tests: Optional[int] = None,
    ) -> Tuple[List[TestCase], List[TestCase], Dict[str, Any]]:
        """
        智能选择测试

        Args:
            repo_path: 仓库路径
            source_branch: 源分支
            target_branch: 目标分支
            all_tests: 所有可用的测试套件
            registry: 测试注册中心
            strategy: 选择策略
            dependency_graph: 预构建的依赖图
            max_tests: 最大测试数量限制

        Returns:
            (选择的测试列表, 跳过的测试列表, 元数据)
        """
        logger.info(
            "smart_test_selection_started",
            repo_path=repo_path,
            strategy=strategy.value,
            total_tests=sum(len(s.tests) for s in all_tests),
        )

        # 1. 分析代码变更
        file_changes = self.git_analyzer.analyze_mr_changes(
            repo_path,
            source_branch,
            target_branch,
        )

        if not file_changes:
            # 无变更，跳过所有测试
            all_test_cases = self._flatten_tests(all_tests)
            return [], all_test_cases, {"reason": "no_changes", "confidence": 1.0}

        # 2. 加载历史数据
        self.historical_analyzer.load_from_registry(registry)

        # 3. 构建或使用依赖图
        if dependency_graph:
            self.dependency_graph = dependency_graph
        else:
            self.dependency_graph = self.graph_builder.build_from_source(repo_path)

        # 4. 分析影响域
        changed_files = set(fc.path for fc in file_changes)
        affected_files, affected_functions = self._analyze_impact(
            file_changes,
            strategy,
        )

        # 5. 评分和排序所有测试
        all_test_cases = self._flatten_tests(all_tests)
        scored_tests = []

        for test in all_test_cases:
            score = self._score_test(
                test,
                file_changes,
                changed_files,
                affected_files,
                affected_functions,
                registry,
                strategy,
            )
            scored_tests.append(score)

        # 6. 按策略过滤和排序
        selected_tests, skipped_tests = self._apply_strategy(
            scored_tests,
            strategy,
            max_tests,
        )

        # 7. 准备元数据
        metadata = {
            "strategy": strategy.value,
            "total_tests": len(all_test_cases),
            "selected_count": len(selected_tests),
            "skipped_count": len(skipped_tests),
            "changed_files": len(file_changes),
            "affected_files": len(affected_files),
            "confidence": self._calculate_confidence(scored_tests, selected_tests),
        }

        logger.info(
            "smart_test_selection_completed",
            selected_count=len(selected_tests),
            skipped_count=len(skipped_tests),
            confidence=metadata["confidence"],
        )

        return selected_tests, skipped_tests, metadata

    def _score_test(
        self,
        test: TestCase,
        file_changes: List[FileChange],
        changed_files: Set[str],
        affected_files: Set[str],
        affected_functions: Set[str],
        registry: TestRegistry,
        strategy: SelectionStrategy,
    ) -> SelectionScore:
        """
        为测试打分

        Args:
            test: 测试用例
            file_changes: 文件变更列表
            changed_files: 变更的文件集合
            affected_files: 受影响的文件集合
            affected_functions: 受影响的函数集合
            registry: 测试注册中心
            strategy: 选择策略

        Returns:
            选择评分
        """
        score = SelectionScore(
            test=test,
            score=0.0,
            reason="",
        )

        # 1. 依赖关系得分 (0-40分)
        score.dependency_score = self._calculate_dependency_score(
            test,
            changed_files,
            affected_files,
            affected_functions,
            registry,
        )

        # 2. 历史得分 (0-30分)
        score.historical_score = self._calculate_historical_score(
            test,
            changed_files,
            registry,
        )

        # 3. 覆盖率得分 (0-20分)
        score.coverage_score = self._calculate_coverage_score(
            test,
            changed_files,
            registry,
        )

        # 4. 优先级得分 (0-10分)
        score.priority_score = self._calculate_priority_score(
            test,
            registry,
        )

        # 5. 根据策略调整权重
        weights = self._get_strategy_weights(strategy)
        total_score = (
            score.dependency_score * weights["dependency"] +
            score.historical_score * weights["historical"] +
            score.coverage_score * weights["coverage"] +
            score.priority_score * weights["priority"]
        )

        score.score = total_score
        score.reason = self._generate_score_reason(score)

        return score

    def _calculate_dependency_score(
        self,
        test: TestCase,
        changed_files: Set[str],
        affected_files: Set[str],
        affected_functions: Set[str],
        registry: TestRegistry,
    ) -> float:
        """
        计算依赖关系得分 (0-40)

        直接相关: 40分
        间接相关（1级）: 25分
        间接相关（2级）: 15分
        无关: 0分
        """
        test_meta = registry.get_test(f"{test.suite}:{test.name}")
        if not test_meta:
            return 20.0  # 未知测试，中等得分

        score = 0.0

        # 检查测试文件是否被修改
        if any("test" in fc.path.lower() for fc in changed_files):
            if test.name in fc.path or test.suite in fc.path:
                return 40.0  # 测试文件本身被修改

        # 检查覆盖的源文件
        test_files = set(test_meta.source_files)
        direct_overlap = test_files & changed_files
        if direct_overlap:
            score += 30.0

        # 检查函数匹配
        if affected_functions:
            for func in affected_functions:
                if func.lower() in test.name.lower():
                    score += 35.0
                    break

        # 检查受影响的文件
        affected_overlap = test_files & affected_files
        if affected_overlap and not direct_overlap:
            score += 20.0

        return min(score, 40.0)

    def _calculate_historical_score(
        self,
        test: TestCase,
        changed_files: Set[str],
        registry: TestRegistry,
    ) -> float:
        """
        计算历史得分 (0-30)

        基于历史执行数据和失败概率
        """
        test_meta = registry.get_test(f"{test.suite}:{test.name}")
        if not test_meta:
            return 15.0  # 未知测试，中等得分

        # 使用历史分析器预测失败概率
        failure_prob = self.historical_analyzer.predict_failure_probability(
            test_meta.test_id,
            changed_files,
        )

        # 失败概率越高，得分越高（应该运行）
        return failure_prob * 30

    def _calculate_coverage_score(
        self,
        test: TestCase,
        changed_files: Set[str],
        registry: TestRegistry,
    ) -> float:
        """
        计算覆盖率得分 (0-20)

        测试覆盖的变更文件越多，得分越高
        """
        test_meta = registry.get_test(f"{test.suite}:{test.name}")
        if not test_meta:
            return 10.0

        if not changed_files:
            return 10.0

        test_files = set(test_meta.source_files)
        covered_files = test_files & changed_files

        if not covered_files:
            return 5.0  # 没有覆盖任何变更文件

        # 覆盖比例
        coverage_ratio = len(covered_files) / len(changed_files)

        return coverage_ratio * 20

    def _calculate_priority_score(
        self,
        test: TestCase,
        registry: TestRegistry,
    ) -> float:
        """
        计算优先级得分 (0-10)

        critical: 10分
        high: 7分
        medium: 4分
        low: 1分
        """
        test_meta = registry.get_test(f"{test.suite}:{test.name}")
        if not test_meta:
            return 4.0  # 默认中等优先级

        priority_scores = {
            TestPriority.CRITICAL: 10.0,
            TestPriority.HIGH: 7.0,
            TestPriority.MEDIUM: 4.0,
            TestPriority.LOW: 1.0,
        }

        return priority_scores.get(test_meta.priority, 4.0)

    def _get_strategy_weights(self, strategy: SelectionStrategy) -> Dict[str, float]:
        """获取策略权重"""
        if strategy == SelectionStrategy.CONSERVATIVE:
            # 保守：更重视依赖关系和优先级
            return {
                "dependency": 0.4,
                "historical": 0.2,
                "coverage": 0.2,
                "priority": 0.2,
            }
        elif strategy == SelectionStrategy.AGGRESSIVE:
            # 激进：只选择高相关的测试
            return {
                "dependency": 0.6,
                "historical": 0.2,
                "coverage": 0.1,
                "priority": 0.1,
            }
        elif strategy == SelectionStrategy.FAST_FAIL:
            # 快速失败：优先运行可能失败的测试
            return {
                "dependency": 0.2,
                "historical": 0.5,
                "coverage": 0.2,
                "priority": 0.1,
            }
        else:  # BALANCED
            return {
                "dependency": 0.35,
                "historical": 0.25,
                "coverage": 0.25,
                "priority": 0.15,
            }

    def _apply_strategy(
        self,
        scored_tests: List[SelectionScore],
        strategy: SelectionStrategy,
        max_tests: Optional[int],
    ) -> Tuple[List[TestCase], List[TestCase]]:
        """
        应用策略选择测试

        Args:
            scored_tests: 评分的测试列表
            strategy: 选择策略
            max_tests: 最大测试数量

        Returns:
            (选择的测试, 跳过的测试)
        """
        # 按得分排序
        if strategy == SelectionStrategy.FAST_FAIL:
            # 快速失败：失败概率高的排前面
            scored_tests.sort(key=lambda x: x.historical_score, reverse=True)
        else:
            # 其他策略：总分高的排前面
            scored_tests.sort(key=lambda x: x.score, reverse=True)

        # 应用阈值
        threshold = self._get_strategy_threshold(strategy)

        selected = []
        skipped = []

        for score in scored_tests:
            if score.score >= threshold:
                selected.append(score.test)
            else:
                skipped.append(score.test)

        # 应用数量限制
        if max_tests and len(selected) > max_tests:
            selected = selected[:max_tests]
            skipped = [s.test for s in scored_tests[max_tests:]]

        return selected, skipped

    def _get_strategy_threshold(self, strategy: SelectionStrategy) -> float:
        """获取策略阈值"""
        thresholds = {
            SelectionStrategy.CONSERVATIVE: 20.0,  # 保守：低阈值，选择更多
            SelectionStrategy.BALANCED: 35.0,  # 平衡：中等阈值
            SelectionStrategy.AGGRESSIVE: 50.0,  # 激进：高阈值，选择更少
            SelectionStrategy.FAST_FAIL: 30.0,  # 快速失败：中等阈值
        }
        return thresholds.get(strategy, 35.0)

    def _analyze_impact(
        self,
        file_changes: List[FileChange],
        strategy: SelectionStrategy,
    ) -> Tuple[Set[str], Set[str]]:
        """
        分析影响域

        Args:
            file_changes: 文件变更列表
            strategy: 选择策略

        Returns:
            (受影响的文件集合, 受影响的函数集合)
        """
        affected_files = set()
        affected_functions = set()

        for file_change in file_changes:
            affected_files.add(file_change.path)
            if file_change.modified_functions:
                affected_functions.update(file_change.modified_functions)
            if file_change.added_functions:
                affected_functions.update(file_change.added_functions)

        # 使用依赖图分析下游影响
        if self.dependency_graph:
            max_depth = 3 if strategy == SelectionStrategy.CONSERVATIVE else 2

            for file_path in affected_files:
                file_id = f"file:{file_path}"
                downstream = self.dependency_graph.get_downstream(
                    file_id,
                    max_depth=max_depth,
                )

                for dep_id in downstream:
                    if dep_id.startswith("file:"):
                        affected_files.add(dep_id.replace("file:", ""))
                    elif dep_id.startswith("function:"):
                        parts = dep_id.split(":")
                        if len(parts) >= 3:
                            affected_functions.add(parts[2])

        return affected_files, affected_functions

    def _calculate_confidence(
        self,
        scored_tests: List[SelectionScore],
        selected_tests: List[TestCase],
    ) -> float:
        """
        计算选择置信度 (0-1)

        考虑因素：
        - 选择的测试数量
        - 得分分布
        - 依赖图完整性
        """
        if not selected_tests:
            return 1.0  # 没有选择任何测试也是高置信度

        confidence = 0.5  # 基础置信度

        # 选择的测试比例合理
        total_tests = len(scored_tests)
        selection_ratio = len(selected_tests) / total_tests

        if 0.1 <= selection_ratio <= 0.8:
            confidence += 0.2  # 合理的选择比例
        elif selection_ratio > 0.9:
            confidence += 0.1  # 几乎全选，降低置信度

        # 得分分布合理
        if selected_tests:
            avg_score = sum(s.score for s in scored_tests if s.test in selected_tests) / len(selected_tests)
            if avg_score >= 50:
                confidence += 0.2  # 高平均分
            elif avg_score >= 30:
                confidence += 0.1

        # 有依赖图
        if self.dependency_graph:
            confidence += 0.1

        return min(confidence, 1.0)

    def _flatten_tests(self, test_suites: List[TestSuite]) -> List[TestCase]:
        """将测试套件展平为测试用例列表"""
        test_cases = []
        for suite in test_suites:
            test_cases.extend(suite.tests)
        return test_cases

    def _generate_score_reason(self, score: SelectionScore) -> str:
        """生成评分原因"""
        reasons = []

        if score.dependency_score >= 30:
            reasons.append("直接依赖变更")
        elif score.dependency_score >= 15:
            reasons.append("间接依赖变更")

        if score.historical_score >= 20:
            reasons.append("高失败风险")
        elif score.historical_score >= 10:
            reasons.append("中等失败风险")

        if score.coverage_score >= 15:
            reasons.append("覆盖关键变更")

        if score.priority_score >= 7:
            reasons.append("高优先级测试")

        return "; ".join(reasons) if reasons else "常规选择"


# 全局单例
smart_test_selector = SmartTestSelector()
