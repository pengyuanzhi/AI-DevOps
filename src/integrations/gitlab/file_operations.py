"""
GitLab 文件操作封装

提供文件相关的高级操作
"""

from typing import Any, Dict, List, Optional

import structlog

from src.integrations.gitlab.client import GitLabClient

logger = structlog.get_logger(__name__)


class FileOperations:
    """文件操作封装"""

    def __init__(self, client: GitLabClient):
        """
        初始化文件操作

        Args:
            client: GitLab 客户端实例
        """
        self.client = client

    async def batch_get_files(
        self,
        project_id: int,
        file_paths: List[str],
        ref: str,
    ) -> Dict[str, Optional[str]]:
        """
        批量获取文件内容

        Args:
            project_id: 项目 ID
            file_paths: 文件路径列表
            ref: 分支或提交 SHA

        Returns:
            Dict[str, Optional[str]]: 文件路径到内容的映射
        """
        logger.info(
            "batch_getting_files",
            project_id=project_id,
            file_count=len(file_paths),
            ref=ref,
        )

        files_content = {}

        for file_path in file_paths:
            try:
                content = await self.client.get_file_content(
                    project_id=project_id,
                    file_path=file_path,
                    ref=ref,
                )
                files_content[file_path] = content
            except Exception as e:
                logger.warning(
                    "failed_to_get_file",
                    file_path=file_path,
                    error=str(e),
                )
                files_content[file_path] = None
                continue

        logger.info(
            "batch_get_files_completed",
            project_id=project_id,
            success_count=sum(1 for v in files_content.values() if v is not None),
            total_count=len(file_paths),
        )

        return files_content

    async def create_file(
        self,
        project_id: int,
        file_path: str,
        content: str,
        branch: str,
        commit_message: str,
        author_email: Optional[str] = None,
        author_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建新文件

        Args:
            project_id: 项目 ID
            file_path: 文件路径
            content: 文件内容
            branch: 目标分支
            commit_message: 提交消息
            author_email: 作者邮箱
            author_name: 作者名称

        Returns:
            Dict: 提交信息
        """
        logger.info(
            "creating_file",
            project_id=project_id,
            file_path=file_path,
            branch=branch,
            content_length=len(content),
        )

        try:
            # 使用 python-gitlab 创建文件
            project = await self.client._run_in_executor(
                self.client._client.projects.get,
                project_id,
            )

            file_data = {
                "file_path": file_path,
                "branch": branch,
                "content": content,
                "commit_message": commit_message,
            }

            if author_email:
                file_data["author_email"] = author_email
            if author_name:
                file_data["author_name"] = author_name

            result = await self.client._run_in_executor(
                project.files.create,
                file_data,
            )

            logger.info(
                "file_created",
                project_id=project_id,
                file_path=file_path,
                branch=branch,
                file_id=result.get("file_id"),
            )

            return result

        except Exception as e:
            logger.error(
                "failed_to_create_file",
                project_id=project_id,
                file_path=file_path,
                error=str(e),
            )
            raise

    async def update_file(
        self,
        project_id: int,
        file_path: str,
        content: str,
        branch: str,
        commit_message: str,
        author_email: Optional[str] = None,
        author_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        更新现有文件

        Args:
            project_id: 项目 ID
            file_path: 文件路径
            content: 新的文件内容
            branch: 目标分支
            commit_message: 提交消息
            author_email: 作者邮箱
            author_name: 作者名称

        Returns:
            Dict: 提交信息
        """
        logger.info(
            "updating_file",
            project_id=project_id,
            file_path=file_path,
            branch=branch,
            content_length=len(content),
        )

        try:
            project = await self.client._run_in_executor(
                self.client._client.projects.get,
                project_id,
            )

            # 获取当前文件信息（需要 file_sha）
            file_obj = await self.client._run_in_executor(
                project.files.get,
                file_path,
                ref=branch,
            )

            file_data = {
                "file_path": file_path,
                "branch": branch,
                "content": content,
                "commit_message": commit_message,
            }

            if author_email:
                file_data["author_email"] = author_email
            if author_name:
                file_data["author_name"] = author_name

            result = await self.client._run_in_executor(
                file_obj.update,
                file_data,
            )

            logger.info(
                "file_updated",
                project_id=project_id,
                file_path=file_path,
                branch=branch,
            )

            return result

        except Exception as e:
            logger.error(
                "failed_to_update_file",
                project_id=project_id,
                file_path=file_path,
                error=str(e),
            )
            raise

    async def delete_file(
        self,
        project_id: int,
        file_path: str,
        branch: str,
        commit_message: str,
        author_email: Optional[str] = None,
        author_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        删除文件

        Args:
            project_id: 项目 ID
            file_path: 文件路径
            branch: 目标分支
            commit_message: 提交消息
            author_email: 作者邮箱
            author_name: 作者名称

        Returns:
            Dict: 提交信息
        """
        logger.info(
            "deleting_file",
            project_id=project_id,
            file_path=file_path,
            branch=branch,
        )

        try:
            project = await self.client._run_in_executor(
                self.client._client.projects.get,
                project_id,
            )

            # 获取文件对象
            file_obj = await self.client._run_in_executor(
                project.files.get,
                file_path,
                ref=branch,
            )

            delete_data = {
                "branch": branch,
                "commit_message": commit_message,
            }

            if author_email:
                delete_data["author_email"] = author_email
            if author_name:
                delete_data["author_name"] = author_name

            result = await self.client._run_in_executor(
                file_obj.delete,
                delete_data,
            )

            logger.info(
                "file_deleted",
                project_id=project_id,
                file_path=file_path,
                branch=branch,
            )

            return result

        except Exception as e:
            logger.error(
                "failed_to_delete_file",
                project_id=project_id,
                file_path=file_path,
                error=str(e),
            )
            raise

    async def batch_commit_changes(
        self,
        project_id: int,
        changes: Dict[str, str],
        branch: str,
        commit_message: str,
        action: str = "update",
    ) -> List[Dict[str, Any]]:
        """
        批量提交文件变更

        Args:
            project_id: 项目 ID
            changes: 文件路径到内容的映射
            branch: 目标分支
            commit_message: 提交消息
            action: 操作类型（create/update/delete）

        Returns:
            List[Dict]: 提交结果列表
        """
        logger.info(
            "batch_committing_changes",
            project_id=project_id,
            file_count=len(changes),
            branch=branch,
            action=action,
        )

        results = []

        for file_path, content in changes.items():
            try:
                if action == "create":
                    result = await self.create_file(
                        project_id=project_id,
                        file_path=file_path,
                        content=content,
                        branch=branch,
                        commit_message=commit_message,
                    )
                elif action == "update":
                    result = await self.update_file(
                        project_id=project_id,
                        file_path=file_path,
                        content=content,
                        branch=branch,
                        commit_message=commit_message,
                    )
                elif action == "delete":
                    result = await self.delete_file(
                        project_id=project_id,
                        file_path=file_path,
                        branch=branch,
                        commit_message=commit_message,
                    )
                else:
                    logger.warning(
                        "unknown_action",
                        action=action,
                        file_path=file_path,
                    )
                    continue

                results.append(result)

            except Exception as e:
                logger.error(
                    "failed_to_commit_file",
                    file_path=file_path,
                    action=action,
                    error=str(e),
                )
                continue

        logger.info(
            "batch_commit_completed",
            project_id=project_id,
            success_count=len(results),
            total_count=len(changes),
        )

        return results

    async def get_repository_tree(
        self,
        project_id: int,
        path: str = "",
        ref: str = "HEAD",
        recursive: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        获取仓库目录树

        Args:
            project_id: 项目 ID
            path: 路径
            ref: 分支或提交 SHA
            recursive: 是否递归

        Returns:
            List[Dict]: 文件/目录列表
        """
        logger.info(
            "getting_repository_tree",
            project_id=project_id,
            path=path,
            ref=ref,
            recursive=recursive,
        )

        try:
            project = await self.client._run_in_executor(
                self.client._client.projects.get,
                project_id,
            )

            tree = await self.client._run_in_executor(
                project.repository_tree,
                path=path,
                ref=ref,
                all=recursive,
                recursive=recursive,
            )

            # 转换为字典列表
            tree_list = [
                {
                    "path": item["path"],
                    "type": item["type"],
                    "mode": item["mode"],
                    "id": item["id"],
                }
                for item in tree
            ]

            logger.info(
                "repository_tree_retrieved",
                project_id=project_id,
                item_count=len(tree_list),
            )

            return tree_list

        except Exception as e:
            logger.error(
                "failed_to_get_repository_tree",
                project_id=project_id,
                error=str(e),
            )
            raise
