"""
失败模式数据库

持久化和管理失败模式，支持模式学习和演进
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict

from sqlalchemy.orm import Session
from typing import Any, Dict

from ....utils.logger import get_logger
from .failure_classifier import FailurePattern, FailureType, FailureSeverity

logger = get_logger(__name__)


@dataclass
class PatternOccurrence:
    """模式出现记录"""
    pattern_id: str
    occurrence_id: str
    timestamp: datetime
    project_id: int
    pipeline_id: str
    job_id: str

    # 上下文
    failure_log: str
    changed_files: List[str] = field(default_factory=list)
    commit_hash: str = ""

    # 分类信息
    confidence: float = 0.0
    error_location: Optional[str] = None

    # 修复信息
    fix_attempted: bool = False
    fix_successful: bool = False
    fix_description: Optional[str] = None


@dataclass
class PatternStatistics:
    """模式统计信息"""
    pattern_id: str
    total_occurrences: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    # 项目分布
    projects: Set[int] = field(default_factory=set)

    # 成功率
    fix_attempts: int = 0
    fix_successes: int = 0

    # 时间趋势（最近30天）
    recent_trend: List[int] = field(default_factory=list)

    def get_fix_success_rate(self) -> float:
        """获取修复成功率"""
        if self.fix_attempts == 0:
            return 0.0
        return self.fix_successes / self.fix_attempts

    def get_frequency(self, days: int = 30) -> float:
        """获取出现频率（次/天）"""
        if not self.first_seen or not self.last_seen:
            return 0.0

        time_span = (self.last_seen - self.first_seen).days
        if time_span == 0:
            return float(self.total_occurrences)

        return self.total_occurrences / max(time_span, days)


class PatternDatabase:
    """
    失败模式数据库

    持久化失败模式，跟踪出现历史，支持模式学习
    """

    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir is None:
            # 使用项目目录下的data/patterns
            import os
            project_root = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            storage_dir = project_root / "data" / "patterns"

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.patterns: Dict[str, FailurePattern] = {}
        self.statistics: Dict[str, PatternStatistics] = {}

        self._load_patterns()
        self._load_statistics()

    def _load_patterns(self):
        """从文件加载失败模式"""
        patterns_file = self.storage_dir / "failure_patterns.json"

        if not patterns_file.exists():
            logger.info("patterns_file_not_found", path=str(patterns_file))
            return

        try:
            with open(patterns_file, 'r') as f:
                data = json.load(f)

            for pattern_data in data.get("patterns", []):
                pattern = FailurePattern(**pattern_data)
                self.patterns[pattern.pattern_id] = pattern

            logger.info(
                "patterns_loaded",
                count=len(self.patterns),
                path=str(patterns_file),
            )
        except Exception as e:
            logger.error(
                "patterns_load_failed",
                path=str(patterns_file),
                error=str(e),
                exc_info=True,
            )

    def _load_statistics(self):
        """从文件加载统计信息"""
        stats_file = self.storage_dir / "pattern_statistics.json"

        if not stats_file.exists():
            logger.info("statistics_file_not_found", path=str(stats_file))
            return

        try:
            with open(stats_file, 'r') as f:
                data = json.load(f)

            for pattern_id, stats_data in data.get("statistics", {}).items():
                stats = PatternStatistics(
                    pattern_id=pattern_id,
                    total_occurrences=stats_data.get("total_occurrences", 0),
                    first_seen=datetime.fromisoformat(stats_data["first_seen"]) if stats_data.get("first_seen") else None,
                    last_seen=datetime.fromisoformat(stats_data["last_seen"]) if stats_data.get("last_seen") else None,
                    projects=set(stats_data.get("projects", [])),
                    fix_attempts=stats_data.get("fix_attempts", 0),
                    fix_successes=stats_data.get("fix_successes", 0),
                    recent_trend=stats_data.get("recent_trend", []),
                )
                self.statistics[pattern_id] = stats

            logger.info(
                "statistics_loaded",
                count=len(self.statistics),
                path=str(stats_file),
            )
        except Exception as e:
            logger.error(
                "statistics_load_failed",
                path=str(stats_file),
                error=str(e),
                exc_info=True,
            )

    def save_patterns(self):
        """保存失败模式到文件"""
        patterns_file = self.storage_dir / "failure_patterns.json"

        try:
            data = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "patterns": [asdict(p) for p in self.patterns.values()],
            }

            with open(patterns_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(
                "patterns_saved",
                count=len(self.patterns),
                path=str(patterns_file),
            )
        except Exception as e:
            logger.error(
                "patterns_save_failed",
                path=str(patterns_file),
                error=str(e),
                exc_info=True,
            )

    def save_statistics(self):
        """保存统计信息到文件"""
        stats_file = self.storage_dir / "pattern_statistics.json"

        try:
            data = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "statistics": {
                    pattern_id: {
                        "total_occurrences": stats.total_occurrences,
                        "first_seen": stats.first_seen.isoformat() if stats.first_seen else None,
                        "last_seen": stats.last_seen.isoformat() if stats.last_seen else None,
                        "projects": list(stats.projects),
                        "fix_attempts": stats.fix_attempts,
                        "fix_successes": stats.fix_successes,
                        "recent_trend": stats.recent_trend,
                    }
                    for pattern_id, stats in self.statistics.items()
                },
            }

            with open(stats_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(
                "statistics_saved",
                count=len(self.statistics),
                path=str(stats_file),
            )
        except Exception as e:
            logger.error(
                "statistics_save_failed",
                path=str(stats_file),
                error=str(e),
                exc_info=True,
            )

    def add_pattern(self, pattern: FailurePattern) -> None:
        """添加失败模式"""
        self.patterns[pattern.pattern_id] = pattern

        # 初始化统计信息
        if pattern.pattern_id not in self.statistics:
            self.statistics[pattern.pattern_id] = PatternStatistics(
                pattern_id=pattern.pattern_id,
            )

        self.save_patterns()
        logger.info("pattern_added", pattern_id=pattern.pattern_id)

    def get_pattern(self, pattern_id: str) -> Optional[FailurePattern]:
        """获取失败模式"""
        return self.patterns.get(pattern_id)

    def get_all_patterns(
        self,
        failure_type: Optional[FailureType] = None,
    ) -> List[FailurePattern]:
        """获取所有失败模式"""
        patterns = list(self.patterns.values())

        if failure_type:
            patterns = [p for p in patterns if p.failure_type == failure_type]

        return patterns

    def record_occurrence(
        self,
        occurrence: PatternOccurrence,
    ) -> None:
        """记录模式出现"""
        stats = self.statistics.get(occurrence.pattern_id)

        if not stats:
            stats = PatternStatistics(pattern_id=occurrence.pattern_id)
            self.statistics[occurrence.pattern_id] = stats

        # 更新统计信息
        stats.total_occurrences += 1
        stats.projects.add(occurrence.project_id)

        if not stats.first_seen:
            stats.first_seen = occurrence.timestamp
        stats.last_seen = occurrence.timestamp

        if occurrence.fix_attempted:
            stats.fix_attempts += 1
            if occurrence.fix_successful:
                stats.fix_successes += 1

        logger.info(
            "pattern_occurrence_recorded",
            pattern_id=occurrence.pattern_id,
            total=stats.total_occurrences,
        )

        self.save_statistics()

    def get_statistics(self, pattern_id: str) -> Optional[PatternStatistics]:
        """获取模式统计信息"""
        return self.statistics.get(pattern_id)

    def get_all_statistics(self) -> Dict[str, PatternStatistics]:
        """获取所有统计信息"""
        return self.statistics

    def get_common_patterns(
        self,
        limit: int = 10,
        min_occurrences: int = 5,
    ) -> List[tuple[str, PatternStatistics]]:
        """
        获取常见失败模式

        Args:
            limit: 返回数量限制
            min_occurrences: 最小出现次数

        Returns:
            [(pattern_id, statistics), ...] 按出现次数排序
        """
        filtered = [
            (pid, stats)
            for pid, stats in self.statistics.items()
            if stats.total_occurrences >= min_occurrences
        ]

        # 按出现次数排序
        filtered.sort(key=lambda x: x[1].total_occurrences, reverse=True)

        return filtered[:limit]

    def get_frequent_patterns(
        self,
        days: int = 30,
        limit: int = 10,
    ) -> List[tuple[str, PatternStatistics]]:
        """
        获取高频失败模式

        Args:
            days: 统计天数
            limit: 返回数量限制

        Returns:
            [(pattern_id, statistics), ...] 按频率排序
        """
        pattern_rates = [
            (pid, stats, stats.get_frequency(days))
            for pid, stats in self.statistics.items()
        ]

        # 过滤掉没有频率数据的
        pattern_rates = [(pid, stats, rate) for pid, stats, rate in pattern_rates if rate > 0]

        # 按频率排序
        pattern_rates.sort(key=lambda x: x[2], reverse=True)

        return [(pid, stats) for pid, stats, _ in pattern_rates[:limit]]

    def get_problematic_patterns(
        self,
        min_fix_attempts: int = 5,
        max_success_rate: float = 0.3,
        limit: int = 10,
    ) -> List[tuple[str, PatternStatistics]]:
        """
        获取难修复的失败模式

        Args:
            min_fix_attempts: 最小修复尝试次数
            max_success_rate: 最大成功率阈值
            limit: 返回数量限制

        Returns:
            [(pattern_id, statistics), ...] 按修复难度排序
        """
        problematic = [
            (pid, stats)
            for pid, stats in self.statistics.items()
            if stats.fix_attempts >= min_fix_attempts and
               stats.get_fix_success_rate() <= max_success_rate
        ]

        # 按成功率排序（成功率越低越靠前）
        problematic.sort(key=lambda x: x[1].get_fix_success_rate())

        return problematic[:limit]

    def learn_from_database(self, db: Session) -> None:
        """
        从数据库学习失败模式

        分析历史失败记录，提取新模式
        """
        try:
            # 查询最近的失败记录
            failures = db.query(PipelineFailure).order_by(
                PipelineFailure.created_at.desc()
            ).limit(1000).all()

            logger.info("learning_from_database", failures_count=len(failures))

            for failure in failures:
                # 检查是否已有匹配的模式
                matched = False
                for pattern in self.patterns.values():
                    for regex in pattern.regex_patterns:
                        if failure.error_message and re.search(regex, failure.error_message):
                            matched = True
                            break
                    if matched:
                        break

                if not matched and failure.error_message:
                    # 尝试从错误消息中提取新模式
                    self._extract_potential_pattern(failure)

            logger.info("pattern_learning_completed")
        except Exception as e:
            logger.error(
                "pattern_learning_failed",
                error=str(e),
                exc_info=True,
            )

    def _extract_potential_pattern(self, failure: Dict[str, Any]) -> None:
        """从失败记录中提取潜在模式"""
        # 简化版本：基于错误消息的前几个词创建模式
        error_msg = failure.get("error_message", "")
        if not error_msg:
            return

        # 提取错误类型
        words = error_msg.split()[:5]
        pattern_id = "_".join(words).lower().replace(":", "_")

        # 避免重复
        if pattern_id in self.patterns:
            return

        # 创建新模式
        pattern = FailurePattern(
            pattern_id=f"auto_{pattern_id}",
            name=f"Auto-learned: {' '.join(words)}",
            description=f"自动学习的失败模式，来自失败 #{failure.get('id', 'unknown')}",
            failure_type=FailureType.OTHER,
            severity=FailureSeverity.MEDIUM,
            regex_patterns=[re.escape(error_msg.split('\n')[0])],
        )

        self.add_pattern(pattern)
        logger.info("new_pattern_learned", pattern_id=pattern.pattern_id)

    def export_patterns(self, output_file: str) -> None:
        """导出失败模式到文件"""
        output_path = Path(output_file)

        data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "patterns": [asdict(p) for p in self.patterns.values()],
            "statistics": {
                pattern_id: {
                    "total_occurrences": stats.total_occurrences,
                    "fix_success_rate": stats.get_fix_success_rate(),
                    "frequency_per_day": stats.get_frequency(),
                }
                for pattern_id, stats in self.statistics.items()
            },
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        logger.info("patterns_exported", path=str(output_path))

    def import_patterns(self, input_file: str) -> int:
        """从文件导入失败模式"""
        input_path = Path(input_file)

        if not input_path.exists():
            logger.error("import_file_not_found", path=str(input_path))
            return 0

        try:
            with open(input_path, 'r') as f:
                data = json.load(f)

            imported_count = 0
            for pattern_data in data.get("patterns", []):
                pattern = FailurePattern(**pattern_data)
                self.add_pattern(pattern)
                imported_count += 1

            logger.info(
                "patterns_imported",
                count=imported_count,
                path=str(input_path),
            )

            return imported_count
        except Exception as e:
            logger.error(
                "patterns_import_failed",
                path=str(input_path),
                error=str(e),
                exc_info=True,
            )
            return 0


# 全局单例
pattern_database = PatternDatabase()
