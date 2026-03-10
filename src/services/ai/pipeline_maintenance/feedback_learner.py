"""
反馈学习器

从修复结果中学习，持续改进系统
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum

from sqlalchemy.orm import Session

from ....utils.logger import get_logger
from ....services.ai.pipeline_maintenance.failure_classifier import FailureType, FailurePattern
from ....services.ai.pipeline_maintenance.root_cause_analyzer import RootCauseType
from ....services.ai.pipeline_maintenance.fix_generator import FixSuggestion
from ....services.ai.pipeline_maintenance.fix_executor import ExecutionResult
from ....services.ai.pipeline_maintenance.pattern_db import PatternDatabase, PatternOccurrence

logger = get_logger(__name__)


class FeedbackType(str, Enum):
    """反馈类型"""
    FIX_SUCCESS = "fix_success"  # 修复成功
    FIX_FAILURE = "fix_failure"  # 修复失败
    FALSE_POSITIVE = "false_positive"  # 误报（不需要修复）
    IMPROVEMENT = "improvement"  # 改进建议
    VERIFICATION_FAILED = "verification_failed"  # 验证失败


@dataclass
class FeedbackRecord:
    """反馈记录"""
    record_id: str
    feedback_type: FeedbackType
    timestamp: datetime

    # 关联信息
    suggestion_id: str = ""
    pattern_id: str = ""
    failure_type: FailureType = FailureType.UNKNOWN
    root_cause_type: RootCauseType = RootCauseType.UNKNOWN

    # 执行结果
    execution_status: str = ""
    execution_time_seconds: float = 0.0

    # 用户反馈
    user_comments: str = ""
    user_rating: int = 0  # 1-5星

    # 实际修复
    actual_fix_applied: str = ""
    actual_fix_successful: bool = False


@dataclass
class LearningMetrics:
    """学习指标"""
    total_fixes: int = 0
    successful_fixes: int = 0
    failed_fixes: int = 0
    false_positives: int = 0

    # 按类型的统计
    fixes_by_type: Dict[str, int] = field(default_factory=dict)
    fixes_by_pattern: Dict[str, int] = field(default_factory=dict)

    # 成功率
    overall_success_rate: float = 0.0
    recent_success_rate: float = 0.0  # 最近7天

    # 时间统计
    avg_fix_time: float = 0.0

    def calculate_success_rate(self) -> None:
        """计算成功率"""
        if self.total_fixes > 0:
            self.overall_success_rate = self.successful_fixes / self.total_fixes


class FeedbackLearner:
    """
    反馈学习器

    从修复反馈中学习，改进系统性能
    """

    def __init__(self, pattern_db: PatternDatabase):
        self.pattern_db = pattern_db
        self.feedback_history: List[FeedbackRecord] = []

    def record_feedback(
        self,
        suggestion: FixSuggestion,
        execution_result: ExecutionResult,
        feedback_type: FeedbackType,
        user_comments: Optional[str] = None,
        user_rating: int = 0,
        actual_fix: Optional[str] = None,
    ) -> FeedbackRecord:
        """
        记录反馈

        Args:
            suggestion: 修复建议
            execution_result: 执行结果
            feedback_type: 反馈类型
            user_comments: 用户评论
            user_rating: 用户评分
            actual_fix: 实际应用的修复

        Returns:
            反馈记录
        """
        record = FeedbackRecord(
            record_id=f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{suggestion.suggestion_id}",
            feedback_type=feedback_type,
            timestamp=datetime.now(),
            suggestion_id=suggestion.suggestion_id,
            execution_status=execution_result.status.value,
            execution_time_seconds=execution_result.duration_seconds,
            user_comments=user_comments or "",
            user_rating=user_rating,
            actual_fix_applied=actual_fix or "",
            actual_fix_successful=(feedback_type == FeedbackType.FIX_SUCCESS),
        )

        self.feedback_history.append(record)

        logger.info(
            "feedback_recorded",
            record_id=record.record_id,
            feedback_type=feedback_type.value,
            suggestion_id=suggestion.suggestion_id,
            user_rating=user_rating,
        )

        # 更新模式数据库
        self._update_pattern_statistics(record)

        return record

    def _update_pattern_statistics(self, feedback: FeedbackRecord) -> None:
        """更新模式统计信息"""
        if not feedback.pattern_id:
            return

        # 更新模式数据库中的修复成功率
        stats = self.pattern_db.get_statistics(feedback.pattern_id)
        if stats:
            if feedback.execution_status in ["succeeded", "completed"]:
                stats.fix_successes += 1
            stats.fix_attempts += 1

    def get_metrics(
        self,
        time_window_days: int = 30,
    ) -> LearningMetrics:
        """
        获取学习指标

        Args:
            time_window_days: 时间窗口（天）

        Returns:
            学习指标
        """
        metrics = LearningMetrics()

        # 过滤时间窗口内的记录
        cutoff_time = datetime.now() - timedelta(days=time_window_days)
        recent_records = [
            r for r in self.feedback_history
            if r.timestamp >= cutoff_time
        ]

        metrics.total_fixes = len(recent_records)

        # 统计各类反馈
        for record in recent_records:
            if record.feedback_type == FeedbackType.FIX_SUCCESS:
                metrics.successful_fixes += 1
            elif record.feedback_type == FeedbackType.FIX_FAILURE:
                metrics.failed_fixes += 1
            elif record.feedback_type == FeedbackType.FALSE_POSITIVE:
                metrics.false_positives += 1

            # 按类型统计
            ftype = record.failure_type.value
            metrics.fixes_by_type[ftype] = metrics.fixes_by_type.get(ftype, 0) + 1

            if record.pattern_id:
                metrics.fixes_by_pattern[record.pattern_id] = \
                    metrics.fixes_by_pattern.get(record.pattern_id, 0) + 1

            # 累计修复时间
            if record.execution_time_seconds > 0:
                if metrics.avg_fix_time == 0:
                    metrics.avg_fix_time = record.execution_time_seconds
                else:
                    metrics.avg_fix_time = (
                        metrics.avg_fix_time + record.execution_time_seconds
                    ) / 2

        # 计算成功率
        metrics.calculate_success_rate()

        # 计算最近7天的成功率
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_7days = [r for r in recent_records if r.timestamp >= recent_cutoff]
        if recent_7days:
            success_count = sum(
                1 for r in recent_7days
                if r.feedback_type == FeedbackType.FIX_SUCCESS
            )
            metrics.recent_success_rate = success_count / len(recent_7days)

        return metrics

    def get_problematic_patterns(
        self,
        min_attempts: int = 5,
        max_success_rate: float = 0.5,
        limit: int = 10,
    ) -> List[Dict]:
        """
        获取有问题的模式

        Args:
            min_attempts: 最小尝试次数
            max_success_rate: 最大成功率阈值
            limit: 返回数量限制

        Returns:
            有问题的模式列表
        """
        problematic = []

        for pattern_id, stats in self.pattern_db.get_all_statistics().items():
            if stats.fix_attempts >= min_attempts:
                success_rate = stats.get_fix_success_rate()
                if success_rate <= max_success_rate:
                    problematic.append({
                        "pattern_id": pattern_id,
                        "total_attempts": stats.fix_attempts,
                        "successes": stats.fix_successes,
                        "success_rate": success_rate,
                        "total_occurrences": stats.total_occurrences,
                    })

        # 按成功率排序
        problematic.sort(key=lambda x: x["success_rate"])

        return problematic[:limit]

    def get_best_patterns(
        self,
        min_attempts: int = 5,
        limit: int = 10,
    ) -> List[Dict]:
        """
        获取表现最好的模式

        Args:
            min_attempts: 最小尝试次数
            limit: 返回数量限制

        Returns:
            表现最好的模式列表
        """
        best = []

        for pattern_id, stats in self.pattern_db.get_all_statistics().items():
            if stats.fix_attempts >= min_attempts:
                success_rate = stats.get_fix_success_rate()
                best.append({
                    "pattern_id": pattern_id,
                    "total_attempts": stats.fix_attempts,
                    "successes": stats.fix_successes,
                    "success_rate": success_rate,
                    "total_occurrences": stats.total_occurrences,
                })

        # 按成功率排序
        best.sort(key=lambda x: x["success_rate"], reverse=True)

        return best[:limit]

    def generate_improvement_suggestions(
        self,
    ) -> List[Dict]:
        """
        生成系统改进建议

        Returns:
            改进建议列表
        """
        suggestions = []

        # 1. 检查成功率低的模式
        problematic = self.get_problematic_patterns(min_attempts=3, max_success_rate=0.4)
        if problematic:
            suggestions.append({
                "type": "pattern_improvement",
                "priority": "high",
                "description": f"发现{len(problematic)}个成功率低的失败模式，需要优化",
                "details": problematic[:5],
                "action": "review_and_update_patterns",
            })

        # 2. 检查误报率
        metrics = self.get_metrics()
        false_positive_rate = (
            metrics.false_positives / metrics.total_fixes
            if metrics.total_fixes > 0 else 0
        )
        if false_positive_rate > 0.1:  # 超过10%
            suggestions.append({
                "type": "reduce_false_positives",
                "priority": "high",
                "description": f"误报率过高 ({false_positive_rate:.1%})，需要改进分类准确性",
                "action": "improve_classification_accuracy",
            })

        # 3. 检查修复时间
        if metrics.avg_fix_time > 3600:  # 超过1小时
            suggestions.append({
                "type": "reduce_fix_time",
                "priority": "medium",
                "description": f"平均修复时间过长 ({metrics.avg_fix_time/60:.1f}分钟)，建议优化修复流程",
                "action": "optimize_fix_generation",
            })

        # 4. 检查整体成功率
        if metrics.recent_success_rate < 0.6:  # 低于60%
            suggestions.append({
                "type": "improve_success_rate",
                "priority": "high",
                "description": f"最近7天成功率偏低 ({metrics.recent_success_rate:.1%})，需要系统性改进",
                "action": "review_and_improve_system",
            })

        return suggestions

    def learn_from_feedback(
        self,
    ) -> Dict[str, any]:
        """
        从反馈中学习

        分析反馈数据，提取改进建议

        Returns:
            学习报告
        """
        logger.info("learning_from_feedback", feedback_count=len(self.feedback_history))

        metrics = self.get_metrics()
        improvements = self.generate_improvement_suggestions()
        problematic = self.get_problematic_patterns()
        best = self.get_best_patterns()

        report = {
            "generated_at": datetime.now().isoformat(),
            "metrics": {
                "total_fixes": metrics.total_fixes,
                "overall_success_rate": metrics.overall_success_rate,
                "recent_success_rate": metrics.recent_success_rate,
                "avg_fix_time_minutes": metrics.avg_fix_time / 60,
                "false_positive_rate": (
                    metrics.false_positives / metrics.total_fixes
                    if metrics.total_fixes > 0 else 0
                ),
            },
            "improvement_suggestions": improvements,
            "problematic_patterns": problematic[:5],
            "best_patterns": best[:5],
            "summary": self._generate_summary(metrics, improvements),
        }

        logger.info(
            "learning_completed",
            total_fixes=metrics.total_fixes,
            success_rate=metrics.overall_success_rate,
            improvement_count=len(improvements),
        )

        return report

    def _generate_summary(
        self,
        metrics: LearningMetrics,
        improvements: List[Dict],
    ) -> str:
        """生成摘要"""
        summary_parts = []

        summary_parts.append(f"总共分析了 {metrics.total_fixes} 次修复尝试")
        summary_parts.append(
            f"整体成功率为 {metrics.overall_success_rate:.1%}"
        )
        summary_parts.append(
            f"最近7天成功率为 {metrics.recent_success_rate:.1%}"
        )

        if improvements:
            summary_parts.append(f"发现 {len(improvements)} 个改进建议")

        return "; ".join(summary_parts)


# 全局单例
_feedback_learner: Optional[FeedbackLearner] = None


def get_feedback_learner() -> Optional[FeedbackLearner]:
    """获取反馈学习器实例"""
    return _feedback_learner


def initialize_feedback_learner(pattern_db: PatternDatabase) -> None:
    """初始化反馈学习器"""
    global _feedback_learner
    _feedback_learner = FeedbackLearner(pattern_db)
    logger.info("feedback_learner_initialized")
