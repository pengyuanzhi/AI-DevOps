"""
集成模块

提供与外部系统的集成。
"""

from .gitlab.client import gitlab_client, get_gitlab_client, GitLabClient

__all__ = ["gitlab_client", "get_gitlab_client", "GitLabClient"]
