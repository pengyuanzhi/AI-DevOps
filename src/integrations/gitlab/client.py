"""
GitLab API 客户端

封装 GitLab API 调用，提供异步接口
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from gitlab import Gitlab as SyncGitlab
from gitlab.exceptions import GitlabAuthenticationError, GitlabError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.models.gitlab_events import (
    GitLabMRComment,
    GitLabMRDetails,
    GitLabProject,
    GitLabUser,
)

logger = structlog.get_logger(__name__)


class GitLabError(Exception):
    """GitLab 操作基础异常"""
    pass


class GitLabAuthenticationError(GitLabError):
    """GitLab 认证失败"""
    pass


class GitLabAPIError(GitLabError):
    """GitLab API 调用失败"""
    pass


class GitLabClient:
    """
    GitLab API 客户端（异步封装）

    使用线程池同步库提供异步接口
    """

    def __init__(
        self,
        url: str,
        token: str,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        初始化 GitLab 客户端

        Args:
            url: GitLab 实例 URL（如 https://gitlab.com）
            token: GitLab 个人访问令牌
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.max_retries = max_retries

        # 创建同步客户端
        try:
            self._client = SyncGitlab(
                self.url,
                private_token=self.token,
                timeout=self.timeout,
            )
            # 验证认证
            self._client.auth()
            logger.info(
                "gitlab_client_initialized",
                url=self.url,
                user=self._client.user.username if self._client.user else "unknown",
            )
        except GitlabAuthenticationError as e:
            logger.error("gitlab_authentication_failed", error=str(e))
            raise GitLabAuthenticationError(f"GitLab 认证失败: {e}")
        except GitlabError as e:
            logger.error("gitlab_client_init_failed", error=str(e))
            raise GitLabError(f"GitLab 客户端初始化失败: {e}")

        # 线程池用于异步操作
        self._executor = None

    async def _run_in_executor(self, func, *args, **kwargs):
        """在线程池中运行同步函数"""
        import functools

        if self._executor is None:
            loop = asyncio.get_event_loop()
            self._executor = loop

        # 如果有关键字参数，使用 partial
        if kwargs:
            func = functools.partial(func, *args, **kwargs)
            args = ()

        return await self._executor.run_in_executor(None, func, *args)

    @retry(
        retry=retry_if_exception_type((GitlabError, OSError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_mr_details(
        self,
        project_id: int,
        mr_iid: int,
    ) -> GitLabMRDetails:
        """
        获取 MR 详情

        Args:
            project_id: 项目 ID
            mr_iid: MR IID（不是全局 ID）

        Returns:
            GitLabMRDetails: MR 详情

        Raises:
            GitLabAPIError: API 调用失败
        """
        logger.info(
            "fetching_mr_details",
            project_id=project_id,
            mr_iid=mr_iid,
        )

        try:
            project = await self._run_in_executor(
                self._client.projects.get,
                project_id,
            )
            mr = await self._run_in_executor(
                project.mergerequests.get,
                mr_iid,
            )

            # 转换为我们的模型
            mr_details = GitLabMRDetails(
                id=mr.id,
                iid=mr.iid,
                project_id=project_id,
                title=mr.title,
                description=mr.description,
                source_branch=mr.source_branch,
                target_branch=mr.target_branch,
                author=GitLabUser(
                    id=mr.author["id"],
                    name=mr.author["name"],
                    username=mr.author["username"],
                    email=mr.author.get("email"),
                )
                if mr.author
                else None,
                assignees=[
                    GitLabUser(
                        id=a["id"],
                        name=a["name"],
                        username=a["username"],
                        email=a.get("email"),
                    )
                    for a in (mr.assignees or [])
                ],
                reviewers=[
                    GitLabUser(
                        id=r["id"],
                        name=r["name"],
                        username=r["username"],
                        email=r.get("email"),
                    )
                    for r in (mr.reviewers or [])
                ],
                state=mr.state,
                draft=mr.draft or mr.work_in_progress,
                work_in_progress=mr.work_in_progress,
                created_at=datetime.fromisoformat(mr.created_at.replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(mr.updated_at.replace("Z", "+00:00")),
                merged_at=(
                    datetime.fromisoformat(mr.merged_at.replace("Z", "+00:00"))
                    if mr.merged_at
                    else None
                ),
                web_url=mr.web_url,
                additions=mr.additions or 0,
                deletions=mr.deletions or 0,
                changed_files_count=mr.changed_files_count or 0,
            )

            logger.info(
                "mr_details_fetched",
                project_id=project_id,
                mr_iid=mr_iid,
                title=mr_details.title,
                state=mr_details.state,
            )

            return mr_details

        except GitlabError as e:
            logger.error(
                "fetch_mr_failed",
                project_id=project_id,
                mr_iid=mr_iid,
                error=str(e),
            )
            raise GitLabAPIError(f"获取 MR 详情失败: {e}")

    @retry(
        retry=retry_if_exception_type((GitlabError, OSError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_mr_diff(
        self,
        project_id: int,
        mr_iid: int,
    ) -> List[Dict[str, Any]]:
        """
        获取 MR 的 diff

        Args:
            project_id: 项目 ID
            mr_iid: MR IID

        Returns:
            List[Dict]: diff 列表

        Raises:
            GitLabAPIError: API 调用失败
        """
        logger.info(
            "fetching_mr_diff",
            project_id=project_id,
            mr_iid=mr_iid,
        )

        try:
            project = await self._run_in_executor(
                self._client.projects.get,
                project_id,
            )
            mr = await self._run_in_executor(
                project.mergerequests.get,
                mr_iid,
            )

            # 获取 diff
            diffs = await self._run_in_executor(mr.diffs.list, all=True)

            # 转换为字典列表
            diff_list = [
                {
                    "old_path": diff.old_path,
                    "new_path": diff.new_path,
                    "diff": diff.diff,
                    "new_file": diff.new_file,
                    "renamed_file": diff.renamed_file,
                    "deleted_file": diff.deleted_file,
                }
                for diff in diffs
            ]

            logger.info(
                "mr_diff_fetched",
                project_id=project_id,
                mr_iid=mr_iid,
                diff_count=len(diff_list),
            )

            return diff_list

        except GitlabError as e:
            logger.error(
                "fetch_mr_diff_failed",
                project_id=project_id,
                mr_iid=mr_iid,
                error=str(e),
            )
            raise GitLabAPIError(f"获取 MR diff 失败: {e}")

    @retry(
        retry=retry_if_exception_type((GitlabError, OSError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_file_content(
        self,
        project_id: int,
        file_path: str,
        ref: str,
    ) -> str:
        """
        获取文件内容

        Args:
            project_id: 项目 ID
            file_path: 文件路径
            ref: 分支或提交 SHA

        Returns:
            str: 文件内容

        Raises:
            GitLabAPIError: API 调用失败
        """
        logger.debug(
            "fetching_file_content",
            project_id=project_id,
            file_path=file_path,
            ref=ref,
        )

        try:
            project = await self._run_in_executor(
                self._client.projects.get,
                project_id,
            )

            file = await self._run_in_executor(
                project.files.get,
                file_path,
                ref=ref,
            )

            # 解码内容
            content = file.decode()

            logger.debug(
                "file_content_fetched",
                project_id=project_id,
                file_path=file_path,
                ref=ref,
                size=len(content),
            )

            return content

        except GitlabError as e:
            logger.error(
                "fetch_file_content_failed",
                project_id=project_id,
                file_path=file_path,
                ref=ref,
                error=str(e),
            )
            raise GitLabAPIError(f"获取文件内容失败: {e}")

    async def create_mr_note(
        self,
        project_id: int,
        mr_iid: int,
        note: str,
    ) -> GitLabMRComment:
        """
        创建 MR 评论（整体评论）

        Args:
            project_id: 项目 ID
            mr_iid: MR IID
            note: 评论内容

        Returns:
            GitLabMRComment: 创建的评论

        Raises:
            GitLabAPIError: API 调用失败
        """
        logger.info(
            "creating_mr_note",
            project_id=project_id,
            mr_iid=mr_iid,
            note_length=len(note),
        )

        try:
            project = await self._run_in_executor(
                self._client.projects.get,
                project_id,
            )
            mr = await self._run_in_executor(
                project.mergerequests.get,
                mr_iid,
            )

            # 创建评论
            note_obj = await self._run_in_executor(
                mr.notes.create,
                {"body": note},
            )

            comment = GitLabMRComment(
                id=note_obj.id,
                type="note",
                author=GitLabUser(
                    id=note_obj.author["id"],
                    name=note_obj.author["name"],
                    username=note_obj.author["username"],
                    email=note_obj.author.get("email"),
                ),
                note=note_obj.note,
                created_at=datetime.fromisoformat(
                    note_obj.created_at.replace("Z", "+00:00")
                ),
                updated_at=datetime.fromisoformat(
                    note_obj.updated_at.replace("Z", "+00:00")
                ),
                system=note_obj.system,
                resolvable=note_obj.resolvable if hasattr(note_obj, "resolvable") else False,
                resolved=note_obj.resolved if hasattr(note_obj, "resolved") else False,
            )

            logger.info(
                "mr_note_created",
                project_id=project_id,
                mr_iid=mr_iid,
                note_id=comment.id,
            )

            return comment

        except GitlabError as e:
            logger.error(
                "create_mr_note_failed",
                project_id=project_id,
                mr_iid=mr_iid,
                error=str(e),
            )
            raise GitLabAPIError(f"创建 MR 评论失败: {e}")

    async def close(self):
        """关闭客户端"""
        logger.info("closing_gitlab_client")
        # python-gitlab 不需要显式关闭
        self._client = None


# 全局客户端实例
_gitlab_client: Optional[GitLabClient] = None


def get_gitlab_client(url: str, token: str) -> GitLabClient:
    """
    获取 GitLab 客户端实例（单例）

    Args:
        url: GitLab URL
        token: GitLab token

    Returns:
        GitLabClient: 客户端实例
    """
    global _gitlab_client

    if _gitlab_client is None:
        _gitlab_client = GitLabClient(url=url, token=token)

    return _gitlab_client
