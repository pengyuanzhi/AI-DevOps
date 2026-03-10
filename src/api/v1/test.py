"""
测试相关API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from pydantic import BaseModel

from ...db.session import get_db_session
from ...db.models import Project as ProjectModel, TestCase, TestResult
from ...services.test import TestConfig, test_service
from ...services.ai.test_selection.service import test_selection_service
from ...utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class TestTriggerRequest(BaseModel):
    """测试触发请求"""
    project_id: int
    pipeline_id: int
    job_id: int
    
    # 构建目录
    build_dir: str
    source_dir: str
    
    # 测试选项
    test_type: str = "qttest"
    test_filter: Optional[str] = None
    parallel_jobs: int = 4
    timeout: int = 300
    enable_coverage: bool = True
    
    # 智能测试选择
    enable_smart_selection: bool = False
    smart_selection_conservative: bool = False
    mr_source_branch: Optional[str] = None
    mr_target_branch: Optional[str] = None
    
    # 环境变量
    env_vars: dict = None


class TestResponse(BaseModel):
    """测试响应"""
    job_id: int
    status: str
    message: str
    tests_selected: Optional[int] = None
    tests_skipped: Optional[int] = None


@router.post("/trigger", response_model=TestResponse)
async def trigger_tests(
    request: TestTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
):
    """
    触发测试运行
    
    支持智能测试选择，只运行相关的测试
    """
    logger.info(
        "test_triggered",
        project_id=request.project_id,
        pipeline_id=request.pipeline_id,
        job_id=request.job_id,
        test_type=request.test_type,
        smart_selection=request.enable_smart_selection,
    )
    
    # 创建测试配置
    config = TestConfig(
        project_id=request.project_id,
        pipeline_id=request.pipeline_id,
        job_id=request.job_id,
        build_dir=request.build_dir,
        source_dir=request.source_dir,
        test_filter=request.test_filter,
        parallel_jobs=request.parallel_jobs,
        timeout=request.timeout,
        enable_coverage=request.enable_coverage,
        env_vars=request.env_vars or {},
    )
    
    # 在后台执行测试
    background_tasks.add_task(
        _execute_tests,
        config,
        request.test_type,
        request.enable_smart_selection,
        request.smart_selection_conservative,
        request.mr_source_branch,
        request.mr_target_branch,
    )
    
    return TestResponse(
        job_id=request.job_id,
        status="pending",
        message="Tests started",
    )


async def _execute_tests(
    config: TestConfig,
    test_type: str,
    enable_smart_selection: bool,
    conservative: bool,
    source_branch: Optional[str],
    target_branch: Optional[str],
):
    """在后台执行测试"""
    try:
        # 如果启用智能测试选择
        if enable_smart_selection and source_branch and target_branch:
            logger.info(
                "smart_test_selection_enabled",
                project_id=config.project_id,
                source_branch=source_branch,
                target_branch=target_branch,
            )
            
            # TODO: 这里应该先获取所有测试，然后进行选择
            # 当前暂时运行所有测试
            result = await test_service.run_tests(config, test_type)
        else:
            # 运行所有测试
            result = await test_service.run_tests(config, test_type)
        
        logger.info(
            "tests_completed",
            project_id=config.project_id,
            pipeline_id=config.pipeline_id,
            job_id=config.job_id,
            status=result.status.value,
            total_tests=result.total_tests,
            passed_tests=result.passed_tests,
            failed_tests=result.failed_tests,
            duration=result.duration_seconds,
        )
        
    except Exception as e:
        logger.error(
            "tests_failed",
            project_id=config.project_id,
            pipeline_id=config.pipeline_id,
            job_id=config.job_id,
            error=str(e),
        )


@router.get("/{job_id}/status")
async def get_test_status(
    job_id: int,
    project_id: int,
    pipeline_id: int,
):
    """
    获取测试状态
    """
    test_status = await test_service.get_test_status(
        project_id=project_id,
        pipeline_id=pipeline_id,
        job_id=job_id,
    )
    
    if test_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found",
        )
    
    return {
        "job_id": job_id,
        "status": test_status.value,
    }


class TestSelectionRequest(BaseModel):
    """测试选择请求"""
    project_id: int
    repo_path: str
    source_branch: str
    target_branch: str
    
    # 选项
    conservative: bool = False


@router.post("/select", response_model=dict)
async def select_tests(
    request: TestSelectionRequest,
    db: Session = Depends(get_db_session),
):
    """
    智能测试选择

    分析代码变更，选择需要运行的测试
    """
    logger.info(
        "test_selection_requested",
        project_id=request.project_id,
        source_branch=request.source_branch,
        target_branch=request.target_branch,
    )

    # TODO: 这里应该从数据库或配置中获取所有测试
    # 当前返回空结果
    from ....services.ai.test_selection import TestSuite

    all_tests = []  # 应该从实际来源获取

    result = await test_selection_service.select_tests_for_mr(
        repo_path=request.repo_path,
        source_branch=request.source_branch,
        target_branch=request.target_branch,
        all_tests=all_tests,
        conservative=request.conservative,
    )

    return {
        "selected_tests": [t.name for t in result.selected_tests],
        "skipped_tests": [t.name for t in result.skipped_tests],
        "affected_files": list(result.affected_files),
        "total_tests": result.total_tests,
        "selected_count": result.selected_count,
        "skip_count": result.skip_count,
        "time_saved_percent": result.estimated_time_saved_percent,
        "confidence": result.confidence,
    }


# ========================================================================
# Dashboard相关API端点
# ========================================================================

@router.get("/stats")
async def get_test_quality_stats(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取测试质量统计

    Args:
        project_id: 项目ID

    Returns:
        测试质量统计数据
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_
    from ...db.models import Project as ProjectModel, TestResult as TestResultModel

    # 检查项目是否存在
    project = (
        db.query(ProjectModel)
        .filter(ProjectModel.gitlab_project_id == project_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在",
        )

    # 计算统计数据
    # 今日测试统计
    today = datetime.now().date()
    today_results = (
        db.query(TestResultModel)
        .join(TestCase, TestCase.id == TestResultModel.test_case_id)
        .filter(
            TestCase.project_id == project_id,
            func.date(TestResultModel.created_at) == today
        )
        .all()
    )

    total_tests = len(today_results)
    passed_tests = len([r for r in today_results if r.status == "passed"])
    failed_tests = len([r for r in today_results if r.status == "failed"])
    skipped_tests = len([r for r in today_results if r.status == "skipped"])

    # 总体通过率（基于最近30天）
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_results = (
        db.query(TestResultModel)
        .join(TestCase, TestCase.id == TestResultModel.test_case_id)
        .filter(
            TestCase.project_id == project_id,
            TestResultModel.created_at >= thirty_days_ago
        )
        .all()
    )

    if recent_results:
        pass_rate = (len([r for r in recent_results if r.status == "passed"]) / len(recent_results)) * 100
    else:
        pass_rate = 0.0

    # 平均测试执行时间
    avg_duration = (
        db.query(func.avg(TestResultModel.duration))
        .join(TestCase, TestCase.id == TestResultModel.test_case_id)
        .filter(
            TestCase.project_id == project_id,
            TestResultModel.duration.isnot(None)
        )
        .scalar()
    )

    # 覆盖率数据
    coverage = 0.0  # TODO: 从覆盖率表中获取

    return {
        "project_id": project_id,
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "skipped_tests": skipped_tests,
        "pass_rate": round(pass_rate, 2),
        "avg_duration": round(avg_duration, 2) if avg_duration else 0,
        "coverage": round(coverage, 2),
    }


@router.get("/pass-rate-trend")
async def get_pass_rate_trend(
    project_id: int,
    days: int = Query(30, ge=7, le=90, description="天数"),
    db: Session = Depends(get_db_session),
):
    """
    获取测试通过率趋势

    Args:
        project_id: 项目ID
        days: 查询天数（默认30天）

    Returns:
        通过率趋势数据
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from ...db.models import Project as ProjectModel, TestResult as TestResultModel, TestCase as TestCaseModel

    # 检查项目是否存在
    project = (
        db.query(ProjectModel)
        .filter(ProjectModel.gitlab_project_id == project_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在",
        )

    # 计算每日通过率
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days-1)

    trends = []
    for i in range(days):
        current_date = start_date + timedelta(days=i)

        # 查询当天的测试结果
        day_results = (
            db.query(TestResultModel)
            .join(TestCase, TestCase.id == TestResultModel.test_case_id)
            .filter(
                TestCase.project_id == project_id,
                func.date(TestResultModel.created_at) == current_date
            )
            .all()
        )

        if day_results:
            passed_count = len([r for r in day_results if r.status == "passed"])
            pass_rate = (passed_count / len(day_results)) * 100
        else:
            pass_rate = 0

        trends.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "pass_rate": round(pass_rate, 1)
        })

    return trends


@router.get("/failed")
async def get_failed_tests(
    project_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db_session),
):
    """
    获取失败的测试列表

    Args:
        project_id: 项目ID
        page: 页码
        per_page: 每页数量

    Returns:
        失败的测试列表
    """
    from datetime import datetime, timedelta
    from ...db.models import Project as ProjectModel, TestResult as TestResultModel, TestCase as TestCaseModel

    # 检查项目是否存在
    project = (
        db.query(ProjectModel)
        .filter(ProjectModel.gitlab_project_id == project_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在",
        )

    # 查询最近7天失败的测试
    seven_days_ago = datetime.now() - timedelta(days=7)

    query = (
        db.query(TestCaseModel)
        .join(TestResultModel, TestCaseModel.id == TestResultModel.test_case_id)
        .filter(
            TestCaseModel.project_id == project_id,
            TestResultModel.status == "failed",
            TestResultModel.created_at >= seven_days_ago
        )
        .distinct()
    )

    total = query.count()
    test_cases = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [
            {
                "id": tc.id,
                "name": tc.name,
                "suite_id": tc.test_suite_id,
                "file_path": tc.file_path,
                "line_number": tc.line_number,
            }
            for tc in test_cases
        ]
    }


@router.get("/coverage")
async def get_test_coverage(
    project_id: int,
    pipeline_id: Optional[int] = Query(None, description="Pipeline ID"),
    db: Session = Depends(get_db_session),
):
    """
    获取代码覆盖率

    Args:
        project_id: 项目ID
        pipeline_id: 可选的Pipeline ID

    Returns:
        代码覆盖率数据
    """
    from ...db.models import Project as ProjectModel

    # 检查项目是否存在
    project = (
        db.query(ProjectModel)
        .filter(ProjectModel.gitlab_project_id == project_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在",
        )

    # TODO: 从覆盖率表中获取实际数据
    # 当前返回模拟数据
    return {
        "project_id": project_id,
        "line_coverage": 75.5,
        "function_coverage": 82.3,
        "branch_coverage": 68.9,
        "total_lines": 10000,
        "covered_lines": 7550,
        "total_functions": 500,
        "covered_functions": 412,
        "total_branches": 1000,
        "covered_branches": 689,
    }


@router.get("/coverage-trend")
async def get_coverage_trend(
    project_id: int,
    days: int = Query(30, ge=7, le=90, description="天数"),
    db: Session = Depends(get_db_session),
):
    """
    获取覆盖率趋势

    Args:
        project_id: 项目ID
        days: 查询天数（默认30天）

    Returns:
        覆盖率趋势数据
    """
    from datetime import datetime, timedelta
    from ...db.models import Project as ProjectModel

    # 检查项目是否存在
    project = (
        db.query(ProjectModel)
        .filter(ProjectModel.gitlab_project_id == project_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在",
        )

    # TODO: 从覆盖率表中获取实际趋势数据
    # 当前返回模拟数据
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days-1)

    trends = []
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        # 模拟覆盖率变化
        base_coverage = 70.0
        variation = (i % 10) * 1.5

        trends.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "line_coverage": round(base_coverage + variation, 1),
            "function_coverage": round(base_coverage + variation + 5, 1),
            "branch_coverage": round(base_coverage + variation - 5, 1),
        })

    return trends


@router.get("/duration-distribution")
async def get_test_duration_distribution(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取测试执行时间分布

    Args:
        project_id: 项目ID

    Returns:
        测试执行时间分布数据
    """
    from ...db.models import Project as ProjectModel

    # 检查项目是否存在
    project = (
        db.query(ProjectModel)
        .filter(ProjectModel.gitlab_project_id == project_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在",
        )

    # TODO: 从测试结果表中获取实际时间分布
    # 当前返回模拟数据
    return [
        {"range": "0-1s", "count": 150},
        {"range": "1-5s", "count": 80},
        {"range": "5-10s", "count": 45},
        {"range": "10-30s", "count": 20},
        {"range": "30-60s", "count": 10},
        {"range": ">60s", "count": 5},
    ]


# ============================================================================
# Celery任务集成的新API端点
# ============================================================================

class CeleryTestRequest(BaseModel):
    """基于Celery的测试请求"""
    project_id: int
    pipeline_id: str
    job_id: str
    gitlab_job_id: int
    job_name: str

    # 测试配置
    build_dir: str
    source_dir: str
    test_type: str = "qttest"  # qttest, googletest, catch2
    test_filter: Optional[str] = None
    parallel_jobs: int = 4
    timeout: int = 300
    enable_coverage: bool = True

    # 环境变量
    env_vars: Dict[str, str] = None


class CeleryTestResponse(BaseModel):
    """测试提交响应"""
    job_id: str
    celery_task_id: str
    status: str
    message: str


@router.post("/celery/submit", response_model=CeleryTestResponse)
async def submit_celery_test(
    request: CeleryTestRequest,
    db: Session = Depends(get_db_session),
):
    """
    提交测试任务到Celery队列

    这是新的测试API，使用Celery异步任务队列执行测试。
    相比旧的/trigger端点，这个端点提供更好的可扩展性和任务跟踪能力。
    使用TestScheduler统一管理测试任务提交和状态跟踪。

    **请求示例**:
    ```json
    {
        "project_id": 1,
        "pipeline_id": "pipeline-123",
        "job_id": "job-456",
        "gitlab_job_id": 789,
        "job_name": "test-linux",
        "build_dir": "/path/to/build",
        "source_dir": "/path/to/source",
        "test_type": "googletest",
        "enable_coverage": true
    }
    ```
    """
    try:
        from ...services.test.scheduler import test_scheduler

        # 准备测试配置
        test_config = {
            "build_dir": request.build_dir,
            "source_dir": request.source_dir,
            "test_type": request.test_type,
            "test_filter": request.test_filter,
            "parallel_jobs": request.parallel_jobs,
            "timeout": request.timeout,
            "enable_coverage": request.enable_coverage,
            "environment": request.env_vars or {},
        }

        # 使用TestScheduler提交任务（统一管理）
        celery_task_id = test_scheduler.submit_test(
            db=db,
            project_id=request.project_id,
            pipeline_id=request.pipeline_id,
            job_id=request.job_id,
            gitlab_job_id=request.gitlab_job_id,
            job_name=request.job_name,
            job_stage="test",
            test_config=test_config,
            project_path=request.source_dir,
        )

        logger.info(
            "celery_test_submitted",
            job_id=request.job_id,
            celery_task_id=celery_task_id,
            project_id=request.project_id,
            pipeline_id=request.pipeline_id,
        )

        return CeleryTestResponse(
            job_id=request.job_id,
            celery_task_id=celery_task_id,
            status="pending",
            message="Test task submitted to Celery queue",
        )

    except Exception as e:
        logger.error(
            "celery_test_submission_failed",
            job_id=request.job_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit test task: {str(e)}",
        )


@router.get("/celery/{job_id}/status")
async def get_celery_test_status(
    job_id: str,
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取Celery测试任务状态

    返回测试任务的详细状态信息，包括：
    - 任务状态（pending/running/success/failed等）
    - 开始/完成时间
    - 测试统计（通过/失败/跳过的数量）
    - 覆盖率信息（如果启用）

    使用TestScheduler统一查询任务状态。
    """
    from ...services.test.scheduler import test_scheduler

    status_info = test_scheduler.get_test_status(db, job_id)

    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test job {job_id} not found",
        )

    return status_info


@router.post("/celery/{job_id}/cancel")
async def cancel_celery_test(
    job_id: str,
    db: Session = Depends(get_db_session),
):
    """
    取消Celery测试任务

    只能取消状态为pending或running的任务。
    使用TestScheduler统一取消任务。
    """
    from ...services.test.scheduler import test_scheduler

    success = test_scheduler.cancel_test(db, job_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to cancel test job {job_id}. Job may not exist or already completed.",
        )

    return {
        "job_id": job_id,
        "status": "cancelled",
        "message": "Test job cancelled successfully",
    }


@router.get("/celery/active")
async def list_active_celery_tests(
    project_id: Optional[int] = None,
    pipeline_id: Optional[str] = None,
    db: Session = Depends(get_db_session),
):
    """
    列出活跃的Celery测试任务

    返回所有pending或running状态的测试任务。
    可以通过project_id或pipeline_id进行过滤。
    使用TestScheduler统一查询活跃任务。
    """
    from ...services.test.scheduler import test_scheduler

    active_tests = test_scheduler.list_active_tests(
        db=db,
        project_id=project_id,
        pipeline_id=pipeline_id,
    )

    return {
        "count": len(active_tests),
        "tests": active_tests,
    }


@router.post("/celery/discover")
async def discover_celery_tests(
    project_id: int,
    build_dir: str,
    source_dir: Optional[str] = None,
    db: Session = Depends(get_db_session),
):
    """
    发现测试用例

    扫描构建目录并发现所有可用的测试用例。
    """
    from ...tasks.test_tasks import discover_tests

    try:
        result = discover_tests.delay(
            project_id=project_id,
            build_dir=build_dir,
            source_dir=source_dir,
        )

        return {
            "status": "submitted",
            "celery_task_id": result.id,
            "message": "Test discovery task submitted",
        }

    except Exception as e:
        logger.error("test_discovery_submission_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit discovery task: {str(e)}",
        )


@router.post("/celery/coverage")
async def collect_celery_coverage(
    project_id: int,
    build_dir: str,
    source_dirs: List[str],
    output_dir: Optional[str] = None,
    db: Session = Depends(get_db_session),
):
    """
    收集代码覆盖率

    使用gcov/lcov收集代码覆盖率数据。
    """
    from ...tasks.test_tasks import collect_coverage

    try:
        result = collect_coverage.delay(
            project_id=project_id,
            build_dir=build_dir,
            source_dirs=source_dirs,
            output_dir=output_dir,
        )

        return {
            "status": "submitted",
            "celery_task_id": result.id,
            "message": "Coverage collection task submitted",
        }

    except Exception as e:
        logger.error("coverage_collection_submission_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit coverage task: {str(e)}",
        )


@router.get("/celery/statistics")
async def get_celery_test_statistics(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取测试统计信息

    返回项目中所有测试的统计信息，包括：
    - 总测试数
    - 按优先级分类
    - 按状态分类
    - 不稳定测试数量
    - 平均通过率
    """
    from ...tasks.test_tasks import get_test_statistics

    result = get_test_statistics.delay(project_id)

    # 等待结果
    try:
        statistics = result.get(timeout=10)
        return statistics
    except Exception as e:
        logger.error("test_statistics_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get test statistics: {str(e)}",
        )
