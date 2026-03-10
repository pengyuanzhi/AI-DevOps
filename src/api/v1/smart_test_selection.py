"""
智能测试选择API路由

提供基于代码变更和历史数据的智能测试选择功能
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from pydantic import BaseModel

from ...db.session import get_db_session
from ...services.ai.test_selection.service import test_selection_service
from ...services.ai.test_selection.test_selector import SmartTestSelector, SelectionStrategy
from ...services.ai.test_selection.historical_analyzer import historical_analyzer
from ...services.test.registry import test_registry_manager
from ...services.test.base import TestSuite, TestCase
from ...core.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class SmartTestSelectionRequest(BaseModel):
    """智能测试选择请求"""
    project_id: int
    repo_path: str
    source_branch: str
    target_branch: str

    # 测试配置
    build_dir: str
    source_dir: str

    # 选择策略
    strategy: str = "balanced"  # conservative, balanced, aggressive, fast_fail
    max_tests: Optional[int] = None

    # 测试类型
    test_type: str = "qttest"  # qttest, googletest, catch2


class TestSelectionResponse(BaseModel):
    """测试选择响应"""
    selected_tests: List[str]
    skipped_tests: List[str]
    total_tests: int
    selected_count: int
    skipped_count: int
    time_saved_percent: float
    confidence: float
    strategy: str


@router.post("/select", response_model=TestSelectionResponse)
async def select_tests_smart(
    request: SmartTestSelectionRequest,
    db: Session = Depends(get_db_session),
):
    """
    智能选择测试

    基于代码变更、依赖关系和历史数据，智能选择需要运行的测试。

    **策略说明**:
    - `conservative`: 保守策略，选择更多测试，确保不遗漏
    - `balanced`: 平衡策略，兼顾速度和准确性
    - `aggressive`: 激进策略，选择最少的测试
    - `fast_fail`: 快速失败策略，优先运行可能失败的测试

    **请求示例**:
    ```json
    {
        "project_id": 1,
        "repo_path": "/path/to/repo",
        "source_branch": "feature-branch",
        "target_branch": "main",
        "build_dir": "/path/to/build",
        "source_dir": "/path/to/source",
        "strategy": "balanced",
        "max_tests": 50
    }
    ```

    **响应示例**:
    ```json
    {
        "selected_tests": ["TestSuite.test1", "TestSuite.test2"],
        "skipped_tests": ["TestSuite.test3"],
        "total_tests": 150,
        "selected_count": 25,
        "skipped_count": 125,
        "time_saved_percent": 83.3,
        "confidence": 0.85,
        "strategy": "balanced"
    }
    ```
    """
    try:
        logger.info(
            "smart_test_selection_requested",
            project_id=request.project_id,
            repo_path=request.repo_path,
            source_branch=request.source_branch,
            target_branch=request.target_branch,
            strategy=request.strategy,
        )

        # 获取测试注册中心
        registry = test_registry_manager.get_registry(request.project_id)
        if not registry:
            # 首次使用，需要先发现测试
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test registry not found for project {request.project_id}. "
                      f"Please run test discovery first.",
            )

        # 获取所有测试（从注册中心）
        all_test_suites = []
        tests = registry.get_all_tests()
        for test in tests:
            # 创建测试套件（简化版）
            suite = TestSuite(name=test.suite, tests=[test])
            all_test_suites.append(suite)

        if not all_test_suites:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No tests found in registry",
            )

        # 转换策略
        try:
            strategy = SelectionStrategy(request.strategy)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid strategy: {request.strategy}. "
                      f"Must be one of: conservative, balanced, aggressive, fast_fail",
            )

        # 使用智能选择器
        selector = SmartTestSelector()
        selected, skipped, metadata = await selector.select_tests(
            repo_path=request.repo_path,
            source_branch=request.source_branch,
            target_branch=request.target_branch,
            all_tests=all_test_suites,
            registry=registry,
            strategy=strategy,
            max_tests=request.max_tests,
        )

        # 计算时间节省百分比
        total_tests = len(selected) + len(skipped)
        time_saved = (len(skipped) / total_tests * 100) if total_tests > 0 else 0

        logger.info(
            "smart_test_selection_completed",
            project_id=request.project_id,
            selected_count=len(selected),
            skipped_count=len(skipped),
            time_saved_percent=time_saved,
            confidence=metadata.get("confidence", 0.0),
        )

        return TestSelectionResponse(
            selected_tests=[f"{t.suite}.{t.name}" for t in selected],
            skipped_tests=[f"{t.suite}.{t.name}" for t in skipped],
            total_tests=total_tests,
            selected_count=len(selected),
            skipped_count=len(skipped),
            time_saved_percent=round(time_saved, 2),
            confidence=round(metadata.get("confidence", 0.0), 2),
            strategy=request.strategy,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "smart_test_selection_failed",
            project_id=request.project_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test selection failed: {str(e)}",
        )


@router.get("/impact/{project_id}")
async def analyze_test_impact(
    project_id: int,
    changed_files: List[str],
    db: Session = Depends(get_db_session),
):
    """
    分析测试影响

    基于变更的文件，分析每个测试的影响评分。

    **参数**:
    - project_id: 项目ID
    - changed_files: 变更的文件列表（查询参数）

    **响应示例**:
    ```json
    {
        "total_tests": 150,
        "analyzed_tests": [
            {
                "test_id": "test_abc123",
                "test_name": "TestSuite.testFunction",
                "impact_score": 85.5,
                "failure_probability": 75.0,
                "regression_risk": 60.0,
                "priority": "high",
                "reason": "直接依赖变更; 高失败风险"
            }
        ]
    }
    ```
    """
    try:
        # 获取测试注册中心
        registry = test_registry_manager.get_registry(project_id, create=False)
        if not registry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test registry not found for project {request.project_id}",
            )

        # 加载历史数据
        historical_analyzer.load_from_registry(registry)

        # 获取所有测试
        tests = registry.get_all_tests()
        changed_files_set = set(changed_files)

        # 分析影响
        impacts = historical_analyzer.analyze_test_impact(
            test_ids=[t.test_id for t in tests],
            changed_files=changed_files_set,
            registry=registry,
        )

        return {
            "total_tests": len(tests),
            "changed_files": len(changed_files),
            "analyzed_tests": [
                {
                    "test_id": impact.test_id,
                    "test_name": impact.test_name,
                    "impact_score": round(impact.impact_score, 2),
                    "failure_probability": round(impact.failure_probability, 2),
                    "execution_time": round(impact.execution_time, 2),
                    "coverage_importance": round(impact.coverage_importance, 2),
                    "regression_risk": round(impact.regression_risk, 2),
                    "priority": impact.priority,
                    "reason": impact.reason,
                }
                for impact in impacts
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "test_impact_analysis_failed",
            project_id=project_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Impact analysis failed: {str(e)}",
        )


@router.get("/flaky/{project_id}")
async def get_flaky_tests(
    project_id: int,
    min_runs: int = 10,
    db: Session = Depends(get_db_session),
):
    """
    获取不稳定测试

    返回经常在成功和失败之间波动的测试。

    **参数**:
    - project_id: 项目ID
    - min_runs: 最少运行次数（默认10）

    **响应示例**:
    ```json
    {
        "flaky_tests": [
            {
                "test_id": "test_abc123",
                "test_name": "TestSuite.flakyTest",
                "total_runs": 50,
                "flaky_runs": 15,
                "pass_rate": 70.0,
                "avg_duration_ms": 250
            }
        ]
    }
    ```
    """
    try:
        # 获取测试注册中心
        registry = test_registry_manager.get_registry(project_id, create=False)
        if not registry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test registry not found for project {request.project_id}",
            )

        # 加载历史数据
        historical_analyzer.load_from_registry(registry)

        # 查找不稳定测试
        flaky_tests = historical_analyzer.find_flaky_tests(
            registry=registry,
            min_runs=min_runs,
        )

        return {
            "project_id": project_id,
            "min_runs": min_runs,
            "flaky_tests": [
                {
                    "test_id": h.test_id,
                    "test_name": h.test_name,
                    "total_runs": h.total_runs,
                    "flaky_runs": h.flaky_runs,
                    "pass_rate": round((h.passed_runs / h.total_runs * 100) if h.total_runs > 0 else 0, 2),
                    "avg_duration_ms": round(h.avg_duration_ms, 2),
                }
                for h in flaky_tests
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "flaky_tests_retrieval_failed",
            project_id=project_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve flaky tests: {str(e)}",
        )


@router.get("/slow/{project_id}")
async def get_slow_tests(
    project_id: int,
    threshold_ms: float = 5000,
    db: Session = Depends(get_db_session),
):
    """
    获取慢速测试

    返回执行时间超过阈值的测试。

    **参数**:
    - project_id: 项目ID
    - threshold_ms: 时间阈值（毫秒，默认5000）

    **响应示例**:
    ```json
    {
        "slow_tests": [
            {
                "test_id": "test_abc123",
                "test_name": "TestSuite.slowTest",
                "avg_duration_ms": 8500,
                "total_runs": 25,
                "last_run": "2026-03-09T12:34:00"
            }
        ]
    }
    ```
    """
    try:
        # 获取测试注册中心
        registry = test_registry_manager.get_registry(project_id, create=False)
        if not registry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test registry not found for project {request.project_id}",
            )

        # 加载历史数据
        historical_analyzer.load_from_registry(registry)

        # 查找慢速测试
        slow_tests = historical_analyzer.find_slow_tests(
            registry=registry,
            threshold_ms=threshold_ms,
        )

        return {
            "project_id": project_id,
            "threshold_ms": threshold_ms,
            "slow_tests": [
                {
                    "test_id": h.test_id,
                    "test_name": h.test_name,
                    "avg_duration_ms": round(h.avg_duration_ms, 2),
                    "total_runs": h.total_runs,
                    "last_run": h.last_run.isoformat() if h.last_run else None,
                }
                for h in slow_tests
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "slow_tests_retrieval_failed",
            project_id=project_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve slow tests: {str(e)}",
        )


@router.get("/correlations/{project_id}")
async def get_test_correlations(
    project_id: int,
    test_id: str,
    db: Session = Depends(get_db_session),
):
    """
    获取测试关联度

    返回与指定测试经常一起失败或一起通过的测试。

    **参数**:
    - project_id: 项目ID
    - test_id: 测试ID

    **响应示例**:
    ```json
    {
        "test_id": "test_abc123",
        "correlations": {
            "test_def456": 0.85,
            "test_ghi789": 0.72
        }
    }
    ```
    """
    try:
        # 获取测试注册中心
        registry = test_registry_manager.get_registry(project_id, create=False)
        if not registry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test registry not found for project {request.project_id}",
            )

        # 加载历史数据
        historical_analyzer.load_from_registry(registry)

        # 获取关联度
        correlations = historical_analyzer.get_test_correlations(
            test_id=test_id,
            registry=registry,
        )

        return {
            "project_id": project_id,
            "test_id": test_id,
            "correlations": correlations,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "test_correlations_retrieval_failed",
            project_id=project_id,
            test_id=test_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve test correlations: {str(e)}",
        )


@router.get("/statistics/{project_id}")
async def get_selection_statistics(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取测试选择统计信息

    返回测试选择相关的统计数据。

    **响应示例**:
    ```json
    {
        "total_tests": 150,
        "by_priority": {
            "critical": 10,
            "high": 30,
            "medium": 80,
            "low": 30
        },
        "flaky_tests": 5,
        "slow_tests": 12,
        "avg_pass_rate": 96.5,
        "avg_duration_ms": 350
    }
    ```
    """
    try:
        # 获取测试注册中心
        registry = test_registry_manager.get_registry(project_id, create=False)
        if not registry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test registry not found for project {request.project_id}",
            )

        # 获取统计信息
        stats = registry.get_statistics()

        return {
            "project_id": project_id,
            **stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "selection_statistics_retrieval_failed",
            project_id=project_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve selection statistics: {str(e)}",
        )
