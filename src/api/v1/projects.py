"""
项目相关API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional

from ...db.session import get_db_session
from ...db.models import Project as ProjectModel
from ...schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)
from ...integrations.gitlab.client import gitlab_client
from ...services.gitlab_service import gitlab_service

router = APIRouter()


@router.get("", response_model=ProjectListResponse)
async def get_projects(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db_session),
):
    """
    获取项目列表
    """
    query = db.query(ProjectModel)

    total = query.count()
    projects = query.offset((page - 1) * per_page).limit(per_page).all()

    return ProjectListResponse(
        total=total,
        page=page,
        per_page=per_page,
        items=[ProjectResponse.model_validate(p) for p in projects],
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取项目详情
    """
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

    return ProjectResponse.model_validate(project)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db_session),
):
    """
    创建项目
    """
    # 检查项目是否已存在
    existing = (
        db.query(ProjectModel)
        .filter(ProjectModel.gitlab_project_id == project_data.gitlab_project_id)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="项目已存在",
        )

    project = ProjectModel(**project_data.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)

    return ProjectResponse.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db_session),
):
    """
    更新项目
    """
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

    update_data = project_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)

    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    删除项目
    """
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

    db.delete(project)
    db.commit()


@router.post("/sync", response_model=ProjectResponse)
async def sync_from_gitlab(
    gitlab_project_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
):
    """
    从GitLab同步项目
    """
    # 检查GitLab项目是否存在
    gitlab_project = await gitlab_client.get_project(gitlab_project_id)
    if not gitlab_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitLab项目不存在",
        )

    # 同步项目
    project = await gitlab_service.sync_project(db, gitlab_project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="同步项目失败",
        )

    # 异步同步流水线
    background_tasks.add_task(
        _sync_project_pipelines,
        project_id=project.gitlab_project_id,
    )

    return ProjectResponse.model_validate(project)


async def _sync_project_pipelines(project_id: int):
    """异步同步项目流水线（后台任务）"""
    from ...db.session import get_db_session
    with get_db_session() as db:
        await gitlab_service.sync_pipelines(db, project_id)


@router.get("/{project_id}/dashboard/stats")
async def get_dashboard_stats(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取项目Dashboard统计数据

    Args:
        project_id: 项目GitLab ID

    Returns:
        Dashboard统计数据
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_

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
    from ...db.models import Pipeline as PipelineModel

    # 今日构建统计
    today = datetime.now().date()
    today_pipelines = (
        db.query(PipelineModel)
        .filter(
            PipelineModel.gitlab_project_id == project_id,
            func.date(PipelineModel.created_at) == today
        )
        .all()
    )

    today_builds = len(today_pipelines)
    success_count = len([p for p in today_pipelines if p.status == "success"])
    failed_count = len([p for p in today_pipelines if p.status == "failed"])

    # 平均构建时间（秒）
    avg_duration = (
        db.query(func.avg(PipelineModel.duration_seconds))
        .filter(
            PipelineModel.gitlab_project_id == project_id,
            PipelineModel.duration_seconds.isnot(None)
        )
        .scalar()
    )

    # 失败率
    total_pipelines = (
        db.query(PipelineModel)
        .filter(PipelineModel.gitlab_project_id == project_id)
        .count()
    )

    failure_rate = (failed_count / today_builds * 100) if today_builds > 0 else 0

    # 项目健康度（基于最近30天的成功率）
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_pipelines = (
        db.query(PipelineModel)
        .filter(
            PipelineModel.gitlab_project_id == project_id,
            PipelineModel.created_at >= thirty_days_ago
        )
        .all()
    )

    recent_success = len([p for p in recent_pipelines if p.status == "success"])
    health_score = (recent_success / len(recent_pipelines) * 100) if recent_pipelines else 0

    return {
        "project_id": project_id,
        "project_name": project.name,
        "today_builds": today_builds,
        "today_success": success_count,
        "today_failed": failed_count,
        "avg_duration": int(avg_duration) if avg_duration else 0,
        "failure_rate": round(failure_rate, 2),
        "health_score": round(health_score, 1),
        "total_pipelines": total_pipelines
    }


@router.get("/{project_id}/dashboard/health-trend")
async def get_health_trend(
    project_id: int,
    days: int = Query(30, ge=7, le=90, description="天数"),
    db: Session = Depends(get_db_session),
):
    """
    获取项目健康度历史趋势

    Args:
        project_id: 项目GitLab ID
        days: 查询天数（默认30天）

    Returns:
        健康度趋势数据
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_, cast, Date
    from ...db.models import Pipeline as PipelineModel

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

    # 计算每日健康度
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days-1)

    trends = []
    for i in range(days):
        current_date = start_date + timedelta(days=i)

        # 查询当天的Pipeline
        day_pipelines = (
            db.query(PipelineModel)
            .filter(
                PipelineModel.gitlab_project_id == project_id,
                func.date(PipelineModel.created_at) == current_date
            )
            .all()
        )

        if day_pipelines:
            success_count = len([p for p in day_pipelines if p.status == "success"])
            health = (success_count / len(day_pipelines)) * 100
        else:
            health = 0  # 没有数据时使用0或上一个值

        trends.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "health": round(health, 1)
        })

    return trends


@router.get("/{project_id}/dashboard/build-trend")
async def get_build_success_trend(
    project_id: int,
    days: int = Query(30, ge=7, le=90, description="天数"),
    db: Session = Depends(get_db_session),
):
    """
    获取构建成功率趋势

    Args:
        project_id: 项目GitLab ID
        days: 查询天数（默认30天）

    Returns:
        构建成功率趋势数据
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from ...db.models import Pipeline as PipelineModel

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

    # 计算每日成功率
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days-1)

    trends = []
    for i in range(days):
        current_date = start_date + timedelta(days=i)

        # 查询当天的Pipeline
        day_pipelines = (
            db.query(PipelineModel)
            .filter(
                PipelineModel.gitlab_project_id == project_id,
                func.date(PipelineModel.created_at) == current_date
            )
            .all()
        )

        if day_pipelines:
            success_count = len([p for p in day_pipelines if p.status == "success"])
            success_rate = (success_count / len(day_pipelines)) * 100
        else:
            success_rate = 100  # 没有Pipeline时使用100%

        trends.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "success_rate": round(success_rate, 1)
        })

    return trends


@router.get("/{project_id}/dashboard/failed-pipelines")
async def get_recent_failed_pipelines(
    project_id: int,
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    db: Session = Depends(get_db_session),
):
    """
    获取最近失败的Pipeline列表

    Args:
        project_id: 项目GitLab ID
        limit: 返回数量（默认10）

    Returns:
        最近失败的Pipeline列表
    """
    from datetime import datetime
    from ...db.models import Pipeline as PipelineModel

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

    # 查询最近失败的Pipeline
    failed_pipelines = (
        db.query(PipelineModel)
        .filter(
            PipelineModel.gitlab_project_id == project_id,
            PipelineModel.status == "failed"
        )
        .order_by(PipelineModel.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": p.id,
            "pipeline_id": p.gitlab_pipeline_id,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "project": project.name,
            "ref": p.ref,
            "source": p.source
        }
        for p in failed_pipelines
    ]


# ========================================================================
# Test相关API端点（前端期望的路径）
# ========================================================================

@router.get("/{project_id}/tests/stats")
async def get_project_test_stats(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取项目测试质量统计

    Args:
        project_id: 项目GitLab ID

    Returns:
        测试质量统计数据
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from ...db.models import TestCase, TestResult

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
        db.query(TestResult)
        .join(TestCase, TestCase.id == TestResult.test_case_id)
        .filter(
            TestCase.project_id == project_id,
            func.date(TestResult.created_at) == today
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
        db.query(TestResult)
        .join(TestCase, TestCase.id == TestResult.test_case_id)
        .filter(
            TestCase.project_id == project_id,
            TestResult.created_at >= thirty_days_ago
        )
        .all()
    )

    if recent_results:
        pass_rate = (len([r for r in recent_results if r.status == "passed"]) / len(recent_results)) * 100
    else:
        pass_rate = 0.0

    # 平均测试执行时间
    avg_duration = (
        db.query(func.avg(TestResult.duration))
        .join(TestCase, TestCase.id == TestResult.test_case_id)
        .filter(
            TestCase.project_id == project_id,
            TestResult.duration.isnot(None)
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


@router.get("/{project_id}/tests/pass-rate-trend")
async def get_project_test_pass_rate_trend(
    project_id: int,
    days: int = Query(7, ge=7, le=90, description="天数"),
    db: Session = Depends(get_db_session),
):
    """
    获取项目测试通过率趋势

    Args:
        project_id: 项目GitLab ID
        days: 查询天数（默认7天）

    Returns:
        通过率趋势数据
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from ...db.models import TestCase, TestResult

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
            db.query(TestResult)
            .join(TestCase, TestCase.id == TestResult.test_case_id)
            .filter(
                TestCase.project_id == project_id,
                func.date(TestResult.created_at) == current_date
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


@router.get("/{project_id}/tests/failed")
async def get_project_failed_tests(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取项目失败的测试列表

    Args:
        project_id: 项目GitLab ID

    Returns:
        失败的测试列表
    """
    from datetime import datetime, timedelta
    from ...db.models import TestCase, TestResult

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

    failed_tests = (
        db.query(TestCase)
        .join(TestResult, TestCase.id == TestResult.test_case_id)
        .filter(
            TestCase.project_id == project_id,
            TestResult.status == "failed",
            TestResult.created_at >= seven_days_ago
        )
        .distinct()
        .limit(20)
        .all()
    )

    return [
        {
            "id": tc.id,
            "name": tc.name,
            "suite_id": tc.test_suite_id,
            "file_path": tc.file_path,
            "line_number": tc.line_number,
        }
        for tc in failed_tests
    ]


@router.get("/{project_id}/tests/coverage")
async def get_project_test_coverage(
    project_id: int,
    pipeline_id: Optional[int] = Query(None, description="Pipeline ID"),
    db: Session = Depends(get_db_session),
):
    """
    获取项目代码覆盖率

    Args:
        project_id: 项目GitLab ID
        pipeline_id: 可选的Pipeline ID

    Returns:
        代码覆盖率数据
    """
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


@router.get("/{project_id}/tests/coverage-trend")
async def get_project_coverage_trend(
    project_id: int,
    days: int = Query(30, ge=7, le=90, description="天数"),
    db: Session = Depends(get_db_session),
):
    """
    获取项目覆盖率趋势

    Args:
        project_id: 项目GitLab ID
        days: 查询天数（默认30天）

    Returns:
        覆盖率趋势数据
    """
    from datetime import datetime, timedelta

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


@router.get("/{project_id}/tests/flaky")
async def get_project_flaky_tests(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取项目不稳定的测试（flaky tests）

    Args:
        project_id: 项目GitLab ID

    Returns:
        不稳定的测试列表
    """
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

    # TODO: 从数据库中查询不稳定的测试
    # 当前返回空列表
    return []


@router.get("/{project_id}/tests/duration-distribution")
async def get_project_test_duration_distribution(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取项目测试执行时间分布

    Args:
        project_id: 项目GitLab ID

    Returns:
        测试执行时间分布数据
    """
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


# ========================================================================
# CodeReview相关API端点（前端期望的路径）
# ========================================================================

@router.get("/{project_id}/code-quality/score")
async def get_code_quality_score(
    project_id: int,
    mr_id: Optional[int] = Query(None, description="MR ID"),
    db: Session = Depends(get_db_session),
):
    """
    获取代码质量评分

    Args:
        project_id: 项目GitLab ID
        mr_id: 可选的MR ID

    Returns:
        质量评分数据
    """
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

    # TODO: 从数据库获取实际评分数据
    # 当前返回模拟数据
    return {
        "overall": 85.5,
        "memory_safety": 90.0,
        "performance": 82.0,
        "modern_cpp": 88.0,
        "thread_safety": 85.0,
        "code_style": 82.0,
    }


@router.get("/{project_id}/code-quality/trend")
async def get_code_quality_trend(
    project_id: int,
    days: int = Query(30, ge=7, le=90, description="天数"),
    db: Session = Depends(get_db_session),
):
    """
    获取质量评分历史趋势

    Args:
        project_id: 项目GitLab ID
        days: 查询天数（默认30天）

    Returns:
        质量评分趋势数据
    """
    from datetime import datetime, timedelta

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

    # TODO: 从数据库获取实际趋势数据
    # 当前返回模拟数据
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days-1)

    trends = []
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        # 模拟评分变化
        base_score = 80.0
        variation = (i % 10) * 2.0

        trends.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "overall": round(base_score + variation, 1),
            "memory_safety": round(base_score + variation + 5, 1),
            "performance": round(base_score + variation - 3, 1),
            "modern_cpp": round(base_score + variation + 2, 1),
            "thread_safety": round(base_score + variation, 1),
            "code_style": round(base_score + variation - 2, 1),
        })

    return trends


@router.get("/{project_id}/code-reviews/stats")
async def get_code_review_stats(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取代码审查统计

    Args:
        project_id: 项目GitLab ID

    Returns:
        代码审查统计数据
    """
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

    # TODO: 从数据库获取实际统计数据
    # 当前返回模拟数据
    return {
        "total_issues": 150,
        "critical": 5,
        "high": 25,
        "medium": 60,
        "low": 60,
        "new_this_week": 12,
        "fixed_this_week": 8,
        "false_positives": 15,
    }


@router.get("/{project_id}/code-quality/tech-debt-trend")
async def get_technical_debt_trend(
    project_id: int,
    days: int = Query(30, ge=7, le=90, description="天数"),
    db: Session = Depends(get_db_session),
):
    """
    获取技术债务趋势

    Args:
        project_id: 项目GitLab ID
        days: 查询天数（默认30天）

    Returns:
        技术债务趋势数据
    """
    from datetime import datetime, timedelta

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

    # TODO: 从数据库获取实际趋势数据
    # 当前返回模拟数据
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days-1)

    trends = []
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        # 模拟技术债务变化
        base_debt = 150

        trends.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "total": base_debt + (i % 5),
            "critical": 5 + (i % 3),
            "high": 25 + (i % 4),
            "medium": 60 + (i % 6),
            "low": 60 + (i % 8),
        })

    return trends


@router.get("/{project_id}/code-quality/custom-rules")
async def get_custom_rules(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取自定义规则列表

    Args:
        project_id: 项目GitLab ID

    Returns:
        自定义规则列表
    """
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

    # TODO: 从数据库获取实际规则数据
    # 当前返回空列表
    return []


# ========================================================================
# MemorySafety相关API端点（前端期望的路径）
# ========================================================================

@router.get("/{project_id}/memory-safety/score")
async def get_memory_safety_score(
    project_id: int,
    mr_id: Optional[int] = Query(None, description="MR ID"),
    db: Session = Depends(get_db_session),
):
    """
    获取内存安全评分

    Args:
        project_id: 项目GitLab ID
        mr_id: 可选的MR ID

    Returns:
        内存安全评分数据
    """
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

    # TODO: 从数据库获取实际评分数据
    # 当前返回模拟数据
    return {
        "overall": 88.5,
        "leaks": 90.0,
        "illegal_access": 85.0,
        "corruption": 88.0,
        "use_after_free": 92.0,
        "double_free": 87.0,
    }


@router.get("/{project_id}/memory-safety/trend")
async def get_memory_safety_trend(
    project_id: int,
    days: int = Query(30, ge=7, le=90, description="天数"),
    db: Session = Depends(get_db_session),
):
    """
    获取内存安全评分趋势

    Args:
        project_id: 项目GitLab ID
        days: 查询天数（默认30天）

    Returns:
        内存安全评分趋势数据
    """
    from datetime import datetime, timedelta

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

    # TODO: 从数据库获取实际趋势数据
    # 当前返回模拟数据
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days-1)

    trends = []
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        # 模拟评分变化
        base_score = 85.0
        variation = (i % 10) * 1.5

        trends.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "overall": round(base_score + variation, 1),
            "issue_count": max(0, 20 - (i % 10)),
        })

    return trends


@router.get("/{project_id}/memory-issues/distribution")
async def get_memory_issue_distribution(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取内存问题类型分布

    Args:
        project_id: 项目GitLab ID

    Returns:
        问题类型分布数据
    """
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

    # TODO: 从数据库获取实际分布数据
    # 当前返回模拟数据
    return [
        {"type": "内存泄漏", "count": 45, "percentage": 30.0},
        {"type": "非法访问", "count": 35, "percentage": 23.3},
        {"type": "缓冲区溢出", "count": 25, "percentage": 16.7},
        {"type": "Use After Free", "count": 20, "percentage": 13.3},
        {"type": "Double Free", "count": 15, "percentage": 10.0},
        {"type": "未初始化内存", "count": 10, "percentage": 6.7},
    ]


@router.get("/{project_id}/memory-issues/severity-distribution")
async def get_memory_issue_severity_distribution(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取严重程度分布

    Args:
        project_id: 项目GitLab ID

    Returns:
        严重程度分布数据
    """
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

    # TODO: 从数据库获取实际分布数据
    # 当前返回模拟数据
    return {
        "critical": 10,
        "high": 35,
        "medium": 65,
        "low": 40,
    }


@router.get("/{project_id}/memory-issues/module-density")
async def get_memory_issue_module_density(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取模块内存问题密度

    Args:
        project_id: 项目GitLab ID

    Returns:
        模块密度数据
    """
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

    # TODO: 从数据库获取实际密度数据
    # 当前返回模拟数据
    return [
        {"module": "core/memory", "issue_count": 25, "lines_of_code": 5000, "density": 5.0},
        {"module": "utils/buffer", "issue_count": 18, "lines_of_code": 3000, "density": 6.0},
        {"module": "network/socket", "issue_count": 15, "lines_of_code": 4000, "density": 3.75},
        {"module": "ui/widget", "issue_count": 12, "lines_of_code": 6000, "density": 2.0},
        {"module": "data/parser", "issue_count": 10, "lines_of_code": 3500, "density": 2.86},
    ]


@router.get("/{project_id}/memory-safety/benchmark")
async def get_memory_safety_benchmark(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取与行业基准对比

    Args:
        project_id: 项目GitLab ID

    Returns:
        基准对比数据
    """
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

    # TODO: 从数据库获取实际基准对比数据
    # 当前返回模拟数据
    return {
        "current_score": 88.5,
        "industry_average": 75.0,
        "top_10_percent": 95.0,
        "percentile": 75,
    }


@router.get("/{project_id}/memory-issues")
async def get_memory_issues(
    project_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    severity: Optional[str] = Query(None, description="严重程度"),
    type: Optional[str] = Query(None, description="问题类型"),
    db: Session = Depends(get_db_session),
):
    """
    获取内存安全问题列表

    Args:
        project_id: 项目GitLab ID
        page: 页码
        per_page: 每页数量
        severity: 严重程度过滤
        type: 问题类型过滤

    Returns:
        内存安全问题列表
    """
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

    # TODO: 从数据库获取实际问题数据
    # 当前返回空列表
    return {
        "total": 0,
        "page": page,
        "per_page": per_page,
        "items": []
    }


@router.get("/{project_id}/memory-issues/stats")
async def get_memory_issue_stats(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取内存安全问题统计

    Args:
        project_id: 项目GitLab ID

    Returns:
        内存安全问题统计数据
    """
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

    # TODO: 从数据库获取实际统计数据
    # 当前返回模拟数据
    return {
        "total": 150,
        "by_type": {
            "内存泄漏": 45,
            "非法访问": 35,
            "缓冲区溢出": 25,
            "Use After Free": 20,
            "Double Free": 15,
            "未初始化内存": 10,
        },
        "by_severity": {
            "critical": 10,
            "high": 35,
            "medium": 65,
            "low": 40,
        },
        "by_detector": {
            "Valgrind": 100,
            "AddressSanitizer": 50,
        },
        "trend": [
            {"date": "2026-03-01", "count": 160},
            {"date": "2026-03-02", "count": 155},
            {"date": "2026-03-03", "count": 150},
        ]
    }
