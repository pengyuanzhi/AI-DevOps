"""
流水线相关的Pydantic模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PipelineStatus:
    """流水线状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"
    SKIPPED = "skipped"


class JobResponse(BaseModel):
    """作业响应"""
    id: str
    gitlab_job_id: int
    pipeline_id: str
    name: str
    stage: str
    status: str
    duration_seconds: Optional[int] = None
    retry_count: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PipelineResponse(BaseModel):
    """流水线响应"""
    id: str
    gitlab_pipeline_id: int
    gitlab_project_id: int
    gitlab_mr_iid: Optional[int] = None
    status: str
    ref: str
    sha: str
    source: str
    duration_seconds: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    jobs: List[JobResponse] = []

    class Config:
        from_attributes = True


class PipelineListResponse(BaseModel):
    """流水线列表响应"""
    total: int
    page: int
    per_page: int
    items: List[PipelineResponse]


class PipelineStatsResponse(BaseModel):
    """流水线统计响应"""
    total: int
    success: int
    failed: int
    running: int
    success_rate: float
    avg_duration: float


class PipelineTriggerRequest(BaseModel):
    """触发流水线请求"""
    ref: str = Field(..., description="分支或标签")
