"""
项目相关的Pydantic模型
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ProjectBase(BaseModel):
    """项目基础模型"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    gitlab_project_id: int
    default_branch: str = "main"
    config: Dict[str, Any] = {}


class ProjectCreate(ProjectBase):
    """创建项目请求"""
    pass


class ProjectUpdate(BaseModel):
    """更新项目请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    default_branch: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class ProjectResponse(ProjectBase):
    """项目响应"""
    id: str
    gitlab_url: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """项目列表响应"""
    total: int
    items: list[ProjectResponse]
