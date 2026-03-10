"""
Pydantic schemas

定义API的请求和响应模型。
"""

from .auth import LoginRequest, LoginResponse, UserResponse
from .project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)
from .pipeline import (
    PipelineResponse,
    PipelineListResponse,
    PipelineStatsResponse,
    PipelineTriggerRequest,
)

__all__ = [
    "LoginRequest",
    "LoginResponse",
    "UserResponse",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectListResponse",
    "PipelineResponse",
    "PipelineListResponse",
    "PipelineStatsResponse",
    "PipelineTriggerRequest",
]
