"""
Autonomous Pipeline Maintenance Package

Automatically detects, diagnoses, and fixes failed tests and build issues.
"""

# 新版本：自主流水线维护
from .llm_service import LLMService
from .failure_classifier import (
    FailureClassifier,
    FailureType,
    FailureSeverity,
    ClassificationResult,
    failure_classifier,
)
from .pattern_db import (
    PatternDatabase,
    PatternOccurrence,
    PatternStatistics,
    pattern_database,
)
from .root_cause_analyzer import (
    RootCauseAnalyzer,
    RootCause,
    RootCauseType,
    AnalysisContext,
    root_cause_analyzer,
)
from .change_correlator import (
    ChangeCorrelator,
    ChangeCorrelationResult,
    change_correlator,
)
from .fix_generator import (
    FixGenerator,
    FixSuggestion,
    FixComplexity,
    FixType,
    fix_generator,
)
from .fix_executor import (
    SafeFixExecutor,
    ExecutionResult,
    ExecutionStatus,
    fix_executor,
)
from .mr_automation import (
    GitLabMRAutomator,
    MRAutomationResult,
    get_mr_automator,
    initialize_mr_automator,
)
from .feedback_learner import (
    FeedbackLearner,
    FeedbackRecord,
    LearningMetrics,
    get_feedback_learner,
    initialize_feedback_learner,
)

# 旧版本（向后兼容）
from .service import PipelineMaintenanceService, pipeline_maintenance_service

__all__ = [
    # 新版本
    "LLMService",
    "FailureClassifier",
    "FailureType",
    "FailureSeverity",
    "ClassificationResult",
    "failure_classifier",
    "PatternDatabase",
    "PatternOccurrence",
    "PatternStatistics",
    "pattern_database",
    "RootCauseAnalyzer",
    "RootCause",
    "RootCauseType",
    "AnalysisContext",
    "root_cause_analyzer",
    "ChangeCorrelator",
    "ChangeCorrelationResult",
    "change_correlator",
    "FixGenerator",
    "FixSuggestion",
    "FixComplexity",
    "FixType",
    "fix_generator",
    "SafeFixExecutor",
    "ExecutionResult",
    "ExecutionStatus",
    "fix_executor",
    "GitLabMRAutomator",
    "MRAutomationResult",
    "get_mr_automator",
    "initialize_mr_automator",
    "FeedbackLearner",
    "FeedbackRecord",
    "LearningMetrics",
    "get_feedback_learner",
    "initialize_feedback_learner",
    # 旧版本
    "PipelineMaintenanceService",
    "pipeline_maintenance_service",
]
