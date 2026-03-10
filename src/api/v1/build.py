"""
构建相关API路由

提供构建任务的提交、状态查询、取消等API接口。
支持Celery异步任务执行。
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from pathlib import Path

from ...db.session import get_db_session
from ...db.models import JobStatus
from ...services.build import BuildService, BuildConfig, build_service
from ...services.build.scheduler import build_scheduler
from ...services.build.status_tracker import build_status_tracker_manager
from ...services.test import TestConfig, test_service
from ...core.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class BuildTriggerRequest(BaseModel):
    """构建触发请求"""
    project_id: int
    pipeline_id: int
    job_id: int
    
    # Git信息
    git_url: str
    git_ref: str
    git_sha: str
    
    # 构建选项
    build_type: str = "RelWithDebInfo"
    parallel_jobs: int = 4
    timeout: int = 3600
    enable_ccache: bool = True
    
    # 构建配置
    cmake_options: dict = None
    qmake_options: dict = None
    make_options: dict = None
    env_vars: dict = None


class BuildResponse(BaseModel):
    """构建响应"""
    job_id: int
    status: str
    message: str


@router.post("/trigger", response_model=BuildResponse)
async def trigger_build(
    request: BuildTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
):
    """
    触发构建
    
    在后台执行构建任务
    """
    logger.info(
        "build_triggered",
        project_id=request.project_id,
        pipeline_id=request.pipeline_id,
        job_id=request.job_id,
        git_ref=request.git_ref,
    )
    
    # 准备构建环境
    config = build_service.prepare_build_environment(
        project_id=request.project_id,
        pipeline_id=request.pipeline_id,
        job_id=request.job_id,
        git_url=request.git_url,
        git_ref=request.git_ref,
        git_sha=request.git_sha,
    )
    
    # 更新配置
    config.build_type = request.build_type
    config.parallel_jobs = request.parallel_jobs
    config.timeout = request.timeout
    config.enable_ccache = request.enable_ccache
    
    if request.cmake_options:
        config.cmake_options = request.cmake_options
    if request.qmake_options:
        config.qmake_options = request.qmake_options
    if request.make_options:
        config.make_options = request.make_options
    if request.env_vars:
        config.env_vars = request.env_vars
    
    # 在后台执行构建
    background_tasks.add_task(
        _execute_build,
        config,
    )
    
    return BuildResponse(
        job_id=request.job_id,
        status="pending",
        message="Build started",
    )


async def _execute_build(config: BuildConfig):
    """在后台执行构建"""
    try:
        result = await build_service.build(config)
        
        logger.info(
            "build_completed",
            project_id=config.project_id,
            pipeline_id=config.pipeline_id,
            job_id=config.job_id,
            status=result.status.value,
            duration=result.duration_seconds,
            artifacts_count=len(result.artifacts),
        )
        
        # 清理构建环境
        build_service.cleanup_build_environment(
            config.project_id,
            config.pipeline_id,
            config.job_id,
        )
        
    except Exception as e:
        logger.error(
            "build_failed",
            project_id=config.project_id,
            pipeline_id=config.pipeline_id,
            job_id=config.job_id,
            error=str(e),
        )


@router.get("/{job_id}/status")
async def get_build_status(
    job_id: int,
    project_id: int,
    pipeline_id: int,
):
    """
    获取构建状态
    """
    build_status = await build_service.get_build_status(
        project_id=project_id,
        pipeline_id=pipeline_id,
        job_id=job_id,
    )
    
    if build_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Build not found",
        )
    
    return {
        "job_id": job_id,
        "status": build_status.value,
    }


@router.post("/{job_id}/cancel")
async def cancel_build(
    job_id: int,
    project_id: int,
    pipeline_id: int,
):
    """
    取消构建
    """
    success = await build_service.cancel_build(
        project_id=project_id,
        pipeline_id=pipeline_id,
        job_id=job_id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Build not found or already completed",
        )

    return {
        "job_id": job_id,
        "status": "cancelled",
        "message": "Build cancelled successfully",
    }


# ============================================================================
# Celery任务集成的新API端点
# ============================================================================

class CeleryBuildRequest(BaseModel):
    """基于Celery的构建请求"""
    project_id: int
    pipeline_id: str
    job_id: str
    gitlab_job_id: int
    job_name: str
    job_stage: str = "build"

    # 构建配置
    build_type: str = "Release"
    parallel_jobs: int = 4
    enable_ccache: bool = True
    cmake_generator: str = "Unix Makefiles"
    cmake_options: Dict[str, str] = None
    env_vars: Dict[str, str] = None

    # 项目路径（可选，默认使用临时目录）
    project_path: Optional[str] = None


class CeleryBuildResponse(BaseModel):
    """构建提交响应"""
    job_id: str
    celery_task_id: str
    status: str
    message: str


@router.post("/celery/submit", response_model=CeleryBuildResponse)
async def submit_celery_build(
    request: CeleryBuildRequest,
    db: Session = Depends(get_db_session),
):
    """
    提交构建任务到Celery队列

    这是新的构建API，使用Celery异步任务队列执行构建。
    相比旧的/trigger端点，这个端点提供更好的可扩展性和任务跟踪能力。

    **请求示例**:
    ```json
    {
        "project_id": 1,
        "pipeline_id": "pipeline-123",
        "job_id": "job-456",
        "gitlab_job_id": 789,
        "job_name": "build-linux",
        "job_stage": "build",
        "build_type": "Release",
        "parallel_jobs": 4,
        "enable_ccache": true,
        "cmake_generator": "Unix Makefiles"
    }
    ```
    """
    try:
        # 准备构建配置
        build_config = {
            "build_type": request.build_type,
            "parallel_jobs": request.parallel_jobs,
            "enable_ccache": request.enable_ccache,
            "cmake_generator": request.cmake_generator,
            "cmake_options": request.cmake_options or {},
            "environment": request.env_vars or {},
        }

        # 确定项目路径
        project_path = request.project_path
        if not project_path:
            # 使用默认临时构建目录
            project_path = f"/tmp/builds/{request.project_id}/{request.pipeline_id}/{request.job_id}/source"

        # 提交Celery任务
        celery_task_id = build_scheduler.submit_build(
            db=db,
            project_id=request.project_id,
            pipeline_id=request.pipeline_id,
            job_id=request.job_id,
            gitlab_job_id=request.gitlab_job_id,
            job_name=request.job_name,
            job_stage=request.job_stage,
            build_config=build_config,
            project_path=project_path,
        )

        logger.info(
            "celery_build_submitted",
            job_id=request.job_id,
            celery_task_id=celery_task_id,
            project_id=request.project_id,
            pipeline_id=request.pipeline_id,
        )

        return CeleryBuildResponse(
            job_id=request.job_id,
            celery_task_id=celery_task_id,
            status="pending",
            message="Build task submitted to Celery queue",
        )

    except Exception as e:
        logger.error(
            "celery_build_submission_failed",
            job_id=request.job_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit build task: {str(e)}",
        )


@router.get("/celery/{job_id}/status")
async def get_celery_build_status(
    job_id: str,
    db: Session = Depends(get_db_session),
):
    """
    获取Celery构建任务状态

    返回构建任务的详细状态信息，包括：
    - 任务状态（pending/running/success/failed等）
    - 开始/完成时间
    - 持续时间
    - Celery任务ID
    - 构建日志和结果（如果已完成）
    """
    status_info = build_scheduler.get_build_status(db, job_id)

    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Build job {job_id} not found",
        )

    return status_info


@router.post("/celery/{job_id}/cancel")
async def cancel_celery_build(
    job_id: str,
    db: Session = Depends(get_db_session),
):
    """
    取消Celery构建任务

    只能取消状态为pending或running的任务。
    """
    success = build_scheduler.cancel_build(db, job_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to cancel build job {job_id}. Job may not exist or already completed.",
        )

    return {
        "job_id": job_id,
        "status": "cancelled",
        "message": "Build job cancelled successfully",
    }


@router.get("/celery/active")
async def list_active_celery_builds(
    project_id: Optional[int] = None,
    pipeline_id: Optional[str] = None,
    db: Session = Depends(get_db_session),
):
    """
    列出活跃的Celery构建任务

    返回所有pending或running状态的构建任务。
    可以通过project_id或pipeline_id进行过滤。
    """
    active_builds = build_scheduler.list_active_builds(
        db=db,
        project_id=project_id,
        pipeline_id=pipeline_id,
    )

    return {
        "count": len(active_builds),
        "builds": active_builds,
    }


@router.get("/celery/{job_id}/logs")
async def get_build_logs(
    job_id: str,
    db: Session = Depends(get_db_session),
):
    """
    获取构建日志

    返回构建任务的完整日志信息。
    """
    from ...db.models import Job

    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Build job {job_id} not found",
        )

    # 解析日志
    log_details = None
    if job.log:
        try:
            import json
            log_details = json.loads(job.log)
        except (json.JSONDecodeError, TypeError):
            log_details = {"raw_log": job.log}

    return {
        "job_id": job_id,
        "status": job.status.value,
        "log": log_details,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "duration_seconds": job.duration_seconds,
    }


@router.post("/celery/cache/cleanup")
async def cleanup_build_cache(
    max_age_hours: int = 24,
    background_tasks: BackgroundTasks = None,
):
    """
    清理旧的构建缓存

    异步清理超过指定时间的构建缓存。

    **参数**:
    - max_age_hours: 缓存最大保留时间（小时），默认24小时
    """
    from ...tasks.build_tasks import cleanup_cache

    # 在后台执行缓存清理
    if background_tasks:
        background_tasks.add_task(cleanup_cache.delay, max_age_hours)
    else:
        cleanup_cache.delay(max_age_hours)

    return {
        "status": "success",
        "message": f"Cache cleanup task submitted for entries older than {max_age_hours} hours",
    }


# ============================================================================
# 构建进度和报告API端点 (Phase 4)
# ============================================================================

@router.get("/celery/{job_id}/progress")
async def get_build_progress(
    job_id: str,
    db: Session = Depends(get_db_session),
):
    """
    获取构建进度

    返回构建的实时进度信息，包括：
    - 总体进度百分比
    - 当前阶段
    - 已完成的阶段
    - 预计剩余时间

    **响应示例**:
    ```json
    {
        "job_id": "job-456",
        "status": "running",
        "overall_progress": 60.0,
        "elapsed_time": 120.5,
        "current_stage": {
            "stage": "build",
            "status": "running",
            "progress": 75.0,
            "message": "Compiling source code",
            "current_step": 3,
            "total_steps": 4
        },
        "completed_stages": 3,
        "total_stages": 5
    }
    ```
    """
    tracker = build_status_tracker_manager.get_tracker(job_id)

    if not tracker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Build tracker for job {job_id} not found"
        )

    progress_info = tracker.get_overall_progress()
    return progress_info


@router.get("/celery/{job_id}/report")
async def get_build_report(
    job_id: str,
    db: Session = Depends(get_db_session),
):
    """
    获取构建报告

    返回详细的构建报告，包括：
    - 时间统计（各阶段耗时）
    - 性能指标（CPU、内存、IO）
    - 构建统计（文件数、警告数等）
    - 阶段详情

    **响应示例**:
    ```json
    {
        "job_id": "job-456",
        "started_at": "2026-03-09T12:34:00",
        "finished_at": "2026-03-09T12:36:30",
        "total_duration": 150.0,
        "stages": {
            "prepare": {"status": "completed", "duration": 0.5},
            "configure": {"status": "completed", "duration": 2.0},
            "build": {"status": "completed", "duration": 145.0}
        },
        "performance": {
            "cpu": {"average": 75.5, "max": 95.0},
            "memory": {"average_mb": 512.0, "max_mb": 1024.0}
        },
        "statistics": {
            "source_files": 150,
            "compiled_files": 12,
            "warnings": 5,
            "errors": 0
        }
    }
    ```
    """
    tracker = build_status_tracker_manager.get_tracker(job_id)

    if not tracker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Build tracker for job {job_id} not found"
        )

    report = tracker.get_build_report()
    return report


@router.get("/celery/{job_id}/performance")
async def get_build_performance(
    job_id: str,
    db: Session = Depends(get_db_session),
):
    """
    获取构建性能指标

    返回实时的性能监控数据，包括：
    - CPU使用率（当前、平均、最大）
    - 内存使用（当前、平均、最大）
    - IO统计
    - 进程信息

    **响应示例**:
    ```json
    {
        "job_id": "job-456",
        "cpu": {
            "current": 85.0,
            "average": 70.5,
            "max": 95.0
        },
        "memory": {
            "current_mb": 750.0,
            "average_mb": 600.0,
            "max_mb": 1024.0
        },
        "io": {
            "read_mb": 1250.0,
            "write_mb": 450.0
        },
        "process": {
            "pid": 12345,
            "threads": 8,
            "open_files": 256
        },
        "samples": 150
    }
    ```
    """
    tracker = build_status_tracker_manager.get_tracker(job_id)

    if not tracker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Build tracker for job {job_id} not found"
        )

    performance = tracker.get_performance_summary()
    return performance


@router.get("/celery/reports")
async def get_all_build_reports(
    project_id: Optional[int] = None,
    limit: int = 10,
    db: Session = Depends(get_db_session),
):
    """
    获取所有构建报告

    返回多个构建任务的报告摘要。
    可以通过project_id过滤，并限制返回数量。

    **参数**:
    - project_id: 项目ID（可选）
    - limit: 返回数量限制（默认10）

    **响应示例**:
    ```json
    {
        "count": 5,
        "reports": [
            {
                "job_id": "job-456",
                "total_duration": 150.0,
                "status": "success",
                "performance": {...}
            }
        ]
    }
    ```
    """
    all_reports = build_status_tracker_manager.get_all_reports()

    # 过滤
    if project_id:
        all_reports = {
            job_id: report
            for job_id, report in all_reports.items()
            if report.get("project_id") == project_id
        }

    # 限制数量
    report_items = list(all_reports.items())[:limit]

    return {
        "count": len(report_items),
        "reports": [
            {"job_id": job_id, **report}
            for job_id, report in report_items
        ]
    }


