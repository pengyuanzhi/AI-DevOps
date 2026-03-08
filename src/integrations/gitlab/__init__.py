"""
GitLab 集成模块

提供 GitLab API 客户端和相关操作
"""

from src.integrations.gitlab.client import (
    GitLabClient,
    GitLabAPIError,
    GitLabAuthenticationError,
    GitLabError,
    get_gitlab_client,
)
from src.integrations.gitlab.mr_operations import MROperations
from src.integrations.gitlab.file_operations import FileOperations

__all__ = [
    "GitLabClient",
    "GitLabAPIError",
    "GitLabAuthenticationError",
    "GitLabError",
    "get_gitlab_client",
    "MROperations",
    "FileOperations",
]
