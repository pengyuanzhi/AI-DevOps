"""
Pipeline Maintenance API

Endpoints for autonomous pipeline maintenance and failure diagnosis.
"""
from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session

from ...services.ai.pipeline_maintenance.service import pipeline_maintenance_service
from ...services.ai.pipeline_maintenance.failure_classifier import (
    failure_classifier,
    ClassificationResult,
)
from ...services.ai.pipeline_maintenance.root_cause_analyzer import (
    root_cause_analyzer,
    AnalysisContext,
    RootCause,
)
from ...services.ai.pipeline_maintenance.change_correlator import (
    change_correlator,
    ChangeCorrelationResult,
)
from ...services.ai.pipeline_maintenance.fix_generator import (
    fix_generator,
    FixSuggestion,
)
from ...services.ai.pipeline_maintenance.fix_executor import (
    fix_executor,
    ExecutionResult,
)
from ...services.ai.pipeline_maintenance.mr_automation import (
    get_mr_automator,
    MRAutomationResult,
)
from ...services.ai.pipeline_maintenance.feedback_learner import (
    get_feedback_learner,
    FeedbackType,
)
from ...db.session import get_db_session
from ...core.logging.logger import get_logger

logger = get_logger(__name__)


router = APIRouter(prefix="/pipeline-maintenance", tags=["Pipeline Maintenance"])


class DiagnoseBuildRequest(BaseModel):
    """Request to diagnose build failure"""
    build_log: str = Field(..., description="Build log output", min_length=10)
    stage: str = Field(..., description="Pipeline stage where failure occurred")
    job_name: str = Field(..., description="Name of the failed job")


class DiagnoseTestRequest(BaseModel):
    """Request to diagnose test failure"""
    test_name: str = Field(..., description="Name of the failed test")
    test_suite: str = Field(..., description="Test suite name")
    error_log: str = Field(..., description="Test error log", min_length=10)
    occurrence_history: Optional[List[int]] = Field(
        default=None,
        description="History of test results (0=pass, 1=fail)"
    )


class AttemptAutoFixRequest(BaseModel):
    """Request to attempt automatic fix"""
    build_log: str = Field(..., description="Build log output")
    stage: str = Field(..., description="Pipeline stage")
    job_name: str = Field(..., description="Job name")
    project_path: str = Field(default=".", description="Path to project")


class QuarantineTestsRequest(BaseModel):
    """Request to quarantine flaky tests"""
    test_failures: List[dict] = Field(..., description="List of test failures to analyze")
    config_file: str = Field(default=".gitlab-ci.yml", description="CI configuration file")


@router.post("/diagnose/build")
async def diagnose_build_failure(request: DiagnoseBuildRequest):
    """
    Diagnose a build failure and provide fix suggestions

    Analyzes build logs to:
    - Classify the failure type (dependency, configuration, environment, etc.)
    - Determine severity (critical, high, medium, low)
    - Identify root cause
    - Generate specific fix suggestions
    - Estimate fix effort
    """
    result = await pipeline_maintenance_service.diagnose_build_failure(
        build_log=request.build_log,
        stage=request.stage,
        job_name=request.job_name,
    )

    return result


@router.post("/diagnose/test")
async def diagnose_test_failure(request: DiagnoseTestRequest):
    """
    Diagnose a test failure and provide fix suggestions

    Analyzes test failures to:
    - Classify the failure type
    - Determine severity
    - Detect flaky tests
    - Identify root cause
    - Generate specific fix suggestions
    - Recommend actions (fix, quarantine, retry)
    """
    result = await pipeline_maintenance_service.diagnose_test_failure(
        test_name=request.test_name,
        test_suite=request.test_suite,
        error_log=request.error_log,
        occurrence_history=request.occurrence_history,
    )

    return result


@router.post("/auto-fix")
async def attempt_auto_fix(request: AttemptAutoFixRequest):
    """
    Attempt to automatically fix a build failure

    Tries to automatically fix certain types of build failures:
    - Missing dependencies
    - Configuration errors
    - Simple syntax issues

    Returns fix result if successful, or suggestion if manual fix is needed.
    """
    from ...services.ai.pipeline_maintenance.service import FailureClassifier

    classifier = FailureClassifier()
    failure = classifier.classify_build_failure(
        request.build_log,
        request.stage,
        request.job_name,
    )

    result = await pipeline_maintenance_service.attempt_auto_fix(
        failure=failure,
        project_path=request.project_path,
    )

    return result


@router.post("/quarantine")
async def quarantine_flaky_tests(request: QuarantineTestsRequest):
    """
    Quarantine flaky tests

    Identifies and isolates flaky tests that have intermittent failures.
    Quarantined tests are excluded from normal test runs and can be run separately.
    """
    # Convert dict to TestFailure objects
    from ...services.ai.pipeline_maintenance.service import FailureClassifier

    classifier = FailureClassifier()
    test_failures = []

    for failure_data in request.test_failures:
        failure = classifier.classify_test_failure(
            test_name=failure_data.get("test_name", ""),
            test_suite=failure_data.get("test_suite", ""),
            error_log=failure_data.get("error_log", ""),
            occurrence_history=failure_data.get("occurrence_history"),
        )
        test_failures.append(failure)

    result = await pipeline_maintenance_service.quarantine_flaky_tests(
        test_failures=test_failures,
        config_file=request.config_file,
    )

    return result


@router.get("/failure-types")
async def get_failure_types():
    """
    Get supported failure types

    Returns all failure types that can be detected and classified
    """
    return {
        "build_failure_types": [
            {
                "type": "dependency_error",
                "name": "Dependency Error",
                "description": "Missing or incompatible dependencies",
                "examples": ["cannot find -lssl", "package 'openssl' not found"],
            },
            {
                "type": "configuration_error",
                "name": "Configuration Error",
                "description": "Build system configuration issues",
                "examples": ["CMake Error in CMakeLists.txt", "invalid option"],
            },
            {
                "type": "environment_error",
                "name": "Environment Error",
                "description": "Build environment issues",
                "examples": ["permission denied", "no space left", "out of memory"],
            },
            {
                "type": "build_error",
                "name": "Build Error",
                "description": "General compilation errors",
                "examples": ["syntax error", "undefined reference"],
            },
        ],
        "test_failure_types": [
            {
                "type": "test_failure",
                "name": "Test Failure",
                "description": "Assertion or expectation failures",
                "examples": ["assertion failed", "expected X but got Y"],
            },
            {
                "type": "timeout",
                "name": "Timeout",
                "description": "Test exceeded time limit",
                "examples": ["test timed out after 30s"],
            },
        ],
        "severity_levels": [
            {
                "level": "critical",
                "description": "Blocks all builds/tests",
                "action": "Immediate fix required",
            },
            {
                "level": "high",
                "description": "Blocks multiple tests or major features",
                "action": "Fix urgently",
            },
            {
                "level": "medium",
                "description": "Affects single test/feature",
                "action": "Fix in next iteration",
            },
            {
                "level": "low",
                "description": "Minor issue",
                "action": "Fix when convenient",
            },
        ],
    }


@router.get("/best-practices")
async def get_best_practices():
    """
    Get pipeline maintenance best practices

    Returns recommendations for preventing common build/test failures
    """
    return {
        "build_best_practices": [
            {
                "category": "Dependency Management",
                "practices": [
                    "Use dependency manifests (CMakeLists.txt, conan.txt, etc.)",
                    "Pin dependency versions for reproducibility",
                    "Use package managers (conan, vcpkg) instead of manual installation",
                    "Document all required dependencies",
                ],
            },
            {
                "category": "Build Configuration",
                "practices": [
                    "Separate debug and release configurations",
                    "Use build caching (ccache, sccache) to speed up builds",
                    "Enable compiler warnings (-Wall -Wextra)",
                    "Use consistent build configurations across environments",
                ],
            },
            {
                "category": "Error Handling",
                "practices": [
                    "Use static analysis tools (clang-tidy, cppcheck)",
                    "Enable address sanitizer in debug builds",
                    "Add pre-commit hooks for code quality",
                    "Run tests in isolation to identify flaky tests",
                ],
            },
        ],
        "test_best_practices": [
            {
                "category": "Test Reliability",
                "practices": [
                    "Write deterministic tests (avoid timing dependencies)",
                    "Use test fixtures for setup/teardown",
                    "Mock external dependencies",
                    "Avoid shared state between tests",
                ],
            },
            {
                "category": "Test Maintenance",
                "practices": [
                    "Remove or fix flaky tests promptly",
                    "Keep test data separate from production data",
                    "Update tests when API changes",
                    "Document test requirements and setup",
                ],
            },
            {
                "category": "Test Organization",
                "practices": [
                    "Group related tests in test suites",
                    "Use descriptive test names",
                    "Follow AAA pattern (Arrange, Act, Assert)",
                    "Keep tests short and focused",
                ],
            },
        ],
    }


# ==================== 新增：自主流水线维护API ====================

class ClassifyFailureRequest(BaseModel):
    """失败分类请求"""
    project_id: int
    pipeline_id: str
    job_id: str
    log_content: str
    is_build: bool = False
    is_test: bool = False


class AnalyzeRootCauseRequest(BaseModel):
    """根因分析请求"""
    project_id: int
    pipeline_id: str
    job_id: str
    log_content: str
    failure_type: str
    changed_files: List[str] = []
    changed_commits: List[str] = []
    diff_summary: str = ""
    error_location: Optional[str] = None
    use_ai: bool = True


class GenerateFixRequest(BaseModel):
    """生成修复建议请求"""
    project_id: int
    pipeline_id: str
    job_id: str
    root_cause_type: str
    title: str
    description: str
    confidence: float
    responsible_files: List[str] = []
    failure_type: Optional[str] = None
    error_location: Optional[str] = None
    error_message: Optional[str] = None
    use_ai: bool = True


class ExecuteFixRequest(BaseModel):
    """执行修复请求"""
    project_id: int
    pipeline_id: str
    job_id: str
    suggestion_id: str
    fix_type: str
    complexity: str
    title: str
    description: str
    code_changes: List[Dict] = []
    commands: List[str] = []
    verification_steps: List[str] = []
    project_path: str
    dry_run: bool = True


class SubmitFeedbackRequest(BaseModel):
    """提交反馈请求"""
    suggestion_id: str
    feedback_type: str
    execution_status: str
    execution_time: float
    user_comments: Optional[str] = None
    user_rating: int = 0
    actual_fix: Optional[str] = None


@router.post("/v2/classify")
async def classify_failure_v2(
    request: ClassifyFailureRequest,
    db: Session = Depends(get_db_session),
):
    """
    分类失败日志（v2版本）

    自动识别失败类型和严重程度
    """
    try:
        logger.info(
            "failure_classification_v2_requested",
            project_id=request.project_id,
            pipeline_id=request.pipeline_id,
            job_id=request.job_id,
        )

        context = {
            "is_build": request.is_build,
            "is_test": request.is_test,
        }
        result = failure_classifier.classify(request.log_content, context)

        logger.info(
            "failure_classification_v2_completed",
            failure_type=result.failure_type.value,
            severity=result.severity.value,
            confidence=result.confidence,
        )

        return {
            "failure_type": result.failure_type.value,
            "severity": result.severity.value,
            "confidence": result.confidence,
            "matched_patterns": result.matched_patterns,
            "error_location": result.error_location,
            "error_message": result.error_message,
            "context_lines": result.context_lines,
            "suggested_actions": result.suggested_actions,
            "auto_fix_available": result.auto_fix_available,
        }

    except Exception as e:
        logger.error("failure_classification_v2_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分类失败: {str(e)}",
        )


@router.get("/v2/statistics")
async def get_maintenance_statistics_v2(
    db: Session = Depends(get_db_session),
):
    """获取流水线维护统计信息（v2版本）"""
    try:
        learner = get_feedback_learner()
        if not learner:
            return {
                "available": False,
                "message": "反馈学习器未初始化",
            }

        report = learner.learn_from_feedback()

        return {
            "available": True,
            "generated_at": report["generated_at"],
            "metrics": report["metrics"],
            "improvement_suggestions": report["improvement_suggestions"],
            "summary": report["summary"],
        }

    except Exception as e:
        logger.error("get_statistics_v2_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}",
        )
