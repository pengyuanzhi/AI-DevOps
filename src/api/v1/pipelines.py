"""
流水线相关API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from ...db.session import get_db_session
from ...integrations.gitlab.client import gitlab_client
from ...services.gitlab_service import gitlab_service
from ...db.models import Pipeline as PipelineModel
from ...schemas.pipeline import (
    PipelineResponse,
    PipelineListResponse,
    PipelineStatsResponse,
    PipelineTriggerRequest,
)

router = APIRouter()


@router.get("", response_model=PipelineListResponse)
async def get_pipelines(
    project_id: int = Query(...),
    status: Optional[str] = None,
    branch: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db_session),
):
    """
    获取流水线列表
    """
    query = db.query(PipelineModel).filter(
        PipelineModel.gitlab_project_id == project_id
    )

    if status:
        query = query.filter(PipelineModel.status == status)
    if branch:
        query = query.filter(PipelineModel.ref == branch)

    total = query.count()
    pipelines = query.order_by(PipelineModel.created_at.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    return PipelineListResponse(
        total=total,
        page=page,
        per_page=per_page,
        items=[PipelineResponse.model_validate(p) for p in pipelines],
    )


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(
    pipeline_id: str,
    db: Session = Depends(get_db_session),
):
    """
    获取流水线详情
    """
    pipeline = db.query(PipelineModel).filter(PipelineModel.id == pipeline_id).first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="流水线不存在",
        )

    return PipelineResponse.model_validate(pipeline)


@router.get("/stats", response_model=PipelineStatsResponse)
async def get_pipeline_stats(
    project_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取流水线统计信息
    """
    # 计算统计数据
    total = (
        db.query(func.count(PipelineModel.id))
        .filter(PipelineModel.gitlab_project_id == project_id)
        .scalar()
    )

    success = (
        db.query(func.count(PipelineModel.id))
        .filter(
            PipelineModel.gitlab_project_id == project_id,
            PipelineModel.status == "success",
        )
        .scalar()
    )

    failed = (
        db.query(func.count(PipelineModel.id))
        .filter(
            PipelineModel.gitlab_project_id == project_id,
            PipelineModel.status == "failed",
        )
        .scalar()
    )

    running = (
        db.query(func.count(PipelineModel.id))
        .filter(
            PipelineModel.gitlab_project_id == project_id,
            PipelineModel.status == "running",
        )
        .scalar()
    )

    success_rate = (success / total * 100) if total > 0 else 0.0

    avg_duration = (
        db.query(func.avg(PipelineModel.duration_seconds))
        .filter(
            PipelineModel.gitlab_project_id == project_id,
            PipelineModel.duration_seconds.isnot(None),
        )
        .scalar()
    ) or 0.0

    return PipelineStatsResponse(
        total=total or 0,
        success=success or 0,
        failed=failed or 0,
        running=running or 0,
        success_rate=round(success_rate, 2),
        avg_duration=round(avg_duration, 2),
    )


@router.post("/trigger", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
async def trigger_pipeline(
    project_id: int,
    trigger_data: PipelineTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
):
    """
    触发流水线
    """
    # 调用GitLab API触发流水线
    gitlab_pipeline = await gitlab_client.trigger_pipeline(
        project_id,
        trigger_data.ref,
    )

    # 异步同步流水线数据
    background_tasks.add_task(
        _sync_triggered_pipeline,
        project_id=project_id,
        pipeline_id=gitlab_pipeline["id"],
    )

    # 临时返回一个简单的响应
    return PipelineResponse(
        id=str(gitlab_pipeline["id"]),
        gitlab_pipeline_id=gitlab_pipeline["id"],
        gitlab_project_id=project_id,
        status=gitlab_pipeline["status"],
        ref=gitlab_pipeline["ref"],
        sha=gitlab_pipeline["sha"],
        source=gitlab_pipeline["source"],
        duration_seconds=None,
        created_at=gitlab_pipeline["created_at"],
        updated_at=gitlab_pipeline["updated_at"],
        started_at=gitlab_pipeline.get("started_at"),
        finished_at=gitlab_pipeline.get("finished_at"),
    )


async def _sync_triggered_pipeline(project_id: int, pipeline_id: int):
    """异步同步触发的流水线"""
    from ...db.session import get_db_session
    with get_db_session() as db:
        await gitlab_service.sync_pipelines(db, project_id)


@router.post("/{pipeline_id}/retry", response_model=PipelineResponse)
async def retry_pipeline(
    pipeline_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
):
    """
    重试流水线
    """
    # 获取流水线
    pipeline = (
        db.query(PipelineModel)
        .filter(PipelineModel.id == pipeline_id)
        .first()
    )

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="流水线不存在",
        )

    # 调用GitLab API重试流水线
    gitlab_pipeline = await gitlab_client.retry_pipeline(
        pipeline.gitlab_project_id,
        pipeline.gitlab_pipeline_id,
    )

    # 异步同步流水线数据
    background_tasks.add_task(
        _sync_pipeline,
        pipeline.gitlab_project_id,
        pipeline.gitlab_pipeline_id,
    )

    # 临时返回响应
    return PipelineResponse.model_validate(pipeline)


@router.post("/{pipeline_id}/cancel")
async def cancel_pipeline(
    pipeline_id: str,
    db: Session = Depends(get_db_session),
):
    """
    取消流水线
    """
    # TODO: 实现取消流水线的逻辑
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="功能尚未实现",
    )


async def _sync_pipeline(project_id: int, pipeline_id: int):
    """异步同步流水线"""
    from ...db.session import get_db_session
    with get_db_session() as db:
        pipelines = await gitlab_service.sync_pipelines(db, project_id)
        for pipeline in pipelines:
            if pipeline.gitlab_pipeline_id == pipeline_id:
                await gitlab_service.sync_pipeline_jobs(db, pipeline)
