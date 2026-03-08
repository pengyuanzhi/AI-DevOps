"""
GitLab MR 操作封装

提供 MR 相关的高级操作
"""

from typing import Any, Dict, List, Optional

import structlog

from src.integrations.gitlab.client import GitLabClient
from src.models.gitlab_events import GitLabMRDetails

logger = structlog.get_logger(__name__)


class MROperations:
    """Merge Request 操作封装"""

    def __init__(self, client: GitLabClient):
        """
        初始化 MR 操作

        Args:
            client: GitLab 客户端实例
        """
        self.client = client

    async def get_changed_files(
        self,
        project_id: int,
        mr_iid: int,
        extensions: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取 MR 中变更的文件列表

        Args:
            project_id: 项目 ID
            mr_iid: MR IID
            extensions: 文件扩展名过滤器（如 ['.py', '.js']）

        Returns:
            List[Dict]: 变更文件列表
        """
        logger.info(
            "getting_changed_files",
            project_id=project_id,
            mr_iid=mr_iid,
            extensions=extensions,
        )

        diffs = await self.client.get_mr_diff(project_id, mr_iid)

        # 提取变更文件
        changed_files = []
        for diff in diffs:
            file_info = {
                "old_path": diff["old_path"],
                "new_path": diff["new_path"],
                "new_file": diff["new_file"],
                "deleted_file": diff["deleted_file"],
                "renamed_file": diff["renamed_file"],
            }

            # 应用扩展名过滤
            if extensions:
                new_ext = any(diff["new_path"].endswith(ext) for ext in extensions)
                old_ext = any(diff["old_path"].endswith(ext) for ext in extensions)
                if not (new_ext or old_ext):
                    continue

            changed_files.append(file_info)

        logger.info(
            "changed_files_retrieved",
            project_id=project_id,
            mr_iid=mr_iid,
            count=len(changed_files),
        )

        return changed_files

    async def get_file_diff(
        self,
        project_id: int,
        mr_iid: int,
        file_path: str,
    ) -> Optional[str]:
        """
        获取特定文件的 diff

        Args:
            project_id: 项目 ID
            mr_iid: MR IID
            file_path: 文件路径

        Returns:
            Optional[str]: diff 内容，如果文件未变更则返回 None
        """
        logger.debug(
            "getting_file_diff",
            project_id=project_id,
            mr_iid=mr_iid,
            file_path=file_path,
        )

        diffs = await self.client.get_mr_diff(project_id, mr_iid)

        # 查找匹配的 diff
        for diff in diffs:
            if diff["new_path"] == file_path or diff["old_path"] == file_path:
                logger.debug(
                    "file_diff_found",
                    file_path=file_path,
                )
                return diff["diff"]

        logger.debug(
            "file_diff_not_found",
            file_path=file_path,
        )
        return None

    async def get_new_files_content(
        self,
        project_id: int,
        mr_iid: int,
        extensions: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        获取新增或修改的文件内容

        Args:
            project_id: 项目 ID
            mr_iid: MR IID
            extensions: 文件扩展名过滤器

        Returns:
            Dict[str, str]: 文件路径到内容的映射
        """
        logger.info(
            "getting_new_files_content",
            project_id=project_id,
            mr_iid=mr_iid,
            extensions=extensions,
        )

        # 获取 MR 详情
        mr_details = await self.client.get_mr_details(project_id, mr_iid)

        # 获取变更文件
        changed_files = await self.get_changed_files(
            project_id,
            mr_iid,
            extensions=extensions,
        )

        # 获取文件内容
        files_content = {}
        for file_info in changed_files:
            file_path = file_info["new_path"]

            # 跳过删除的文件
            if file_info["deleted_file"]:
                continue

            try:
                content = await self.client.get_file_content(
                    project_id,
                    file_path,
                    mr_details.source_branch,
                )
                files_content[file_path] = content
            except Exception as e:
                logger.warning(
                    "failed_to_get_file_content",
                    file_path=file_path,
                    error=str(e),
                )
                continue

        logger.info(
            "new_files_content_retrieved",
            project_id=project_id,
            mr_iid=mr_iid,
            count=len(files_content),
        )

        return files_content

    async def post_review_comment(
        self,
        project_id: int,
        mr_iid: int,
        comment: str,
        position: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        发布代码审查评论

        Args:
            project_id: 项目 ID
            mr_iid: MR IID
            comment: 评论内容
            position: 位置信息（用于行内评论）
        """
        logger.info(
            "posting_review_comment",
            project_id=project_id,
            mr_iid=mr_iid,
            has_position=position is not None,
        )

        # TODO: 实现行内评论（需要更复杂的 position 结构）
        # 目前先使用整体评论
        await self.client.create_mr_note(
            project_id=project_id,
            mr_iid=mr_iid,
            note=comment,
        )

        logger.info(
            "review_comment_posted",
            project_id=project_id,
            mr_iid=mr_iid,
        )

    async def batch_post_comments(
        self,
        project_id: int,
        mr_iid: int,
        comments: List[str],
        batch_size: int = 10,
    ) -> int:
        """
        批量发布评论

        Args:
            project_id: 项目 ID
            mr_iid: MR IID
            comments: 评论列表
            batch_size: 每批发布的评论数

        Returns:
            int: 成功发布的评论数
        """
        logger.info(
            "batch_posting_comments",
            project_id=project_id,
            mr_iid=mr_iid,
            total_comments=len(comments),
            batch_size=batch_size,
        )

        posted_count = 0

        # 分批发布
        for i in range(0, len(comments), batch_size):
            batch = comments[i : i + batch_size]

            for comment in batch:
                try:
                    await self.client.create_mr_note(
                        project_id=project_id,
                        mr_iid=mr_iid,
                        note=comment,
                    )
                    posted_count += 1
                except Exception as e:
                    logger.error(
                        "failed_to_post_comment",
                        comment_index=i + posted_count,
                        error=str(e),
                    )

            logger.debug(
                "batch_completed",
                batch_index=i // batch_size,
                posted_in_batch=posted_count,
            )

        logger.info(
            "batch_posting_completed",
            project_id=project_id,
            mr_iid=mr_iid,
            posted_count=posted_count,
            total_count=len(comments),
        )

        return posted_count

    async def is_mr_approved(
        self,
        project_id: int,
        mr_iid: int,
        required_approvals: int = 1,
    ) -> bool:
        """
        检查 MR 是否已获得足够的批准

        Args:
            project_id: 项目 ID
            mr_iid: MR IID
            required_approvals: 需要的批准数量

        Returns:
            bool: 是否已批准
        """
        logger.debug(
            "checking_mr_approval",
            project_id=project_id,
            mr_iid=mr_iid,
            required_approvals=required_approvals,
        )

        # 获取 MR 详情
        mr_details = await self.client.get_mr_details(project_id, mr_iid)

        # 检查批准数量（通过 approvals API）
        # TODO: 实现完整的批准检查逻辑
        # 目前简化检查：检查是否有审核者
        has_reviewers = len(mr_details.reviewers) >= required_approvals

        logger.debug(
            "mr_approval_checked",
            has_reviewers=has_reviewers,
            reviewer_count=len(mr_details.reviewers),
        )

        return has_reviewers
