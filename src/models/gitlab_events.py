"""
GitLab Webhook 事件数据模型

定义 GitLab Webhook 事件的数据结构
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GitLabUser(BaseModel):
    """GitLab 用户信息"""
    id: int
    name: str
    username: str
    email: Optional[str] = None


class GitLabProject(BaseModel):
    """GitLab 项目信息"""
    id: int
    name: str
    path_with_namespace: str
    default_branch: str
    url: str
    web_url: str


class GitLabObjectAttributes(BaseModel):
    """GitLab 对象属性（MR/Issue 等）"""
    id: int
    iid: int
    title: str
    description: Optional[str] = None
    state: str
    created_at: datetime
    updated_at: datetime
    action: Optional[str] = None
    source_branch: Optional[str] = None
    target_branch: Optional[str] = None


class GitLabMergeRequest(BaseModel):
    """GitLab Merge Request 事件"""
    object_kind: str = Field(default="merge_request")
    event_type: str = Field(default="merge_request")

    user: GitLabUser
    project: GitLabProject
    object_attributes: GitLabObjectAttributes

    # MR 特有属性
    assignees: List[GitLabUser] = Field(default_factory=list)
    reviewers: List[GitLabUser] = Field(default_factory=list)
    labels: List[str] = Field(default_factory=list)

    # 变更信息
    changes: Optional[Dict[str, Any]] = None

    # 源和目标提交
    last_commit: Optional[Dict[str, Any]] = None


class GitLabPipeline(BaseModel):
    """GitLab Pipeline 事件"""
    object_kind: str = Field(default="pipeline")
    event_type: str = Field(default="pipeline")

    user: GitLabUser
    project: GitLabProject

    object_attributes: Dict[str, Any]

    # Pipeline 特有属性
    merge_request: Optional[Dict[str, Any]] = None
    source: str
    status: str
    ref: str
    sha: str


class GitLabPush(BaseModel):
    """GitLab Push 事件"""
    object_kind: str = Field(default="push")
    event_type: str = Field(default="push")

    user: GitLabUser
    project: GitLabProject

    ref: str
    before: str
    after: str
    checkout_sha: Optional[str] = None

    # 提交列表
    commits: List[Dict[str, Any]] = Field(default_factory=list)
    total_commits_count: int = 0


# 文件相关模型
class GitLabFile(BaseModel):
    """GitLab 文件信息"""
    file_path: str
    branch: str
    content: Optional[str] = None
    content_sha: Optional[str] = None


class GitLabDiff(BaseModel):
    """GitLab Diff 信息"""
    old_path: str
    new_path: str
    diff: str
    new_file: bool = False
    renamed_file: bool = False
    deleted_file: bool = False


class GitLabMRDetails(BaseModel):
    """GitLab MR 详情（从 API 获取）"""
    id: int
    iid: int
    project_id: int
    title: str
    description: Optional[str] = None
    source_branch: str
    target_branch: str
    author: GitLabUser
    assignees: List[GitLabUser] = Field(default_factory=list)
    reviewers: List[GitLabUser] = Field(default_factory=list)
    state: str
    draft: bool = False
    work_in_progress: bool = False
    created_at: datetime
    updated_at: datetime
    merged_at: Optional[datetime] = None
    web_url: str

    # 统计信息
    additions: int = 0
    deletions: int = 0
    changed_files_count: int = 0


class GitLabMRComment(BaseModel):
    """GitLab MR 评论"""
    id: int
    type: str = Field(..., description="评论类型: note, diff_note")
    author: GitLabUser
    note: str
    created_at: datetime
    updated_at: datetime
    system: bool = False
    position: Optional[Dict[str, Any]] = None  # 用于行内评论
    resolvable: bool = False
    resolved: bool = False
