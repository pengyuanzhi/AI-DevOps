"""
作业相关API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...db.session import get_db_session
from ...db.models import Job as JobModel
from ...schemas.pipeline import JobResponse

router = APIRouter()


@router.get("", response_model=list[JobResponse])
async def get_jobs(
    pipeline_id: str,
    db: Session = Depends(get_db_session),
):
    """
    获取作业列表
    """
    jobs = (
        db.query(JobModel)
        .filter(JobModel.pipeline_id == pipeline_id)
        .order_by(JobModel.created_at)
        .all()
    )

    return [JobResponse.model_validate(job) for job in jobs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db: Session = Depends(get_db_session),
):
    """
    获取作业详情
    """
    job = db.query(JobModel).filter(JobModel.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="作业不存在",
        )

    return JobResponse.model_validate(job)


@router.get("/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    db: Session = Depends(get_db_session),
):
    """
    获取作业日志
    """
    job = db.query(JobModel).filter(JobModel.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="作业不存在",
        )

    return {"logs": job.logs or "暂无日志"}
