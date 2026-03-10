"""
GitLab客户端封装

提供GitLab API调用的封装。
"""

from functools import lru_cache
from typing import Optional, List
from datetime import datetime
import httpx
from structlog import get_logger

from ...utils.config import settings

logger = get_logger(__name__)


class GitLabClient:
    """GitLab客户端"""

    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None

    async def get_http_client(self) -> httpx.AsyncClient:
        """获取异步HTTP客户端"""
        if self._http_client is None:
            headers = {
                "PRIVATE-TOKEN": settings.gitlab_token,
                "Content-Type": "application/json",
            }
            self._http_client = httpx.AsyncClient(
                base_url=settings.gitlab_url.rstrip('/') + "/api/v4",
                headers=headers,
                timeout=30.0,
            )
        return self._http_client

    async def close(self):
        """关闭连接"""
        if self._http_client:
            await self._http_client.close()

    # 项目相关方法
    async def get_projects(self, owned: bool = False, per_page: int = 100) -> List[dict]:
        """获取项目列表"""
        client = await self.get_http_client()
        params = {"owned": owned, "per_page": per_page, "membership": True}

        try:
            response = await client.get("/projects", params=params)
            response.raise_for_status()
            projects = response.json()
            logger.info("gitlab_projects_fetched", count=len(projects))
            return projects
        except httpx.HTTPError as e:
            logger.error("gitlab_get_projects_failed", error=str(e))
            raise

    async def get_project(self, project_id: int) -> dict:
        """获取项目详情"""
        client = await self.get_http_client()

        try:
            response = await client.get(f"/projects/{project_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("gitlab_get_project_failed", project_id=project_id, error=str(e))
            raise

    async def get_project_by_id(self, project_id: int) -> Optional[dict]:
        """通过GitLab项目ID获取项目"""
        try:
            return await self.get_project(project_id)
        except Exception:
            return None

    # 流水线相关方法
    async def get_pipelines(
        self,
        project_id: int,
        ref: Optional[str] = None,
        status: Optional[str] = None,
        per_page: int = 20,
    ) -> List[dict]:
        """获取流水线列表"""
        client = await self.get_http_client()
        params = {"per_page": per_page}

        if ref:
            params["ref"] = ref
        if status:
            params["status"] = status

        try:
            response = await client.get(f"/projects/{project_id}/pipelines", params=params)
            response.raise_for_status()
            pipelines = response.json()
            logger.info("gitlab_pipelines_fetched", project_id=project_id, count=len(pipelines))
            return pipelines
        except httpx.HTTPError as e:
            logger.error("gitlab_get_pipelines_failed", project_id=project_id, error=str(e))
            raise

    async def get_pipeline(self, project_id: int, pipeline_id: int) -> dict:
        """获取流水线详情"""
        client = await self.get_http_client()

        try:
            response = await client.get(f"/projects/{project_id}/pipelines/{pipeline_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("gitlab_get_pipeline_failed", project_id=project_id, pipeline_id=pipeline_id, error=str(e))
            raise

    async def get_pipeline_jobs(self, project_id: int, pipeline_id: int) -> List[dict]:
        """获取流水线的作业列表"""
        client = await self.get_http_client()

        try:
            response = await client.get(f"/projects/{project_id}/pipelines/{pipeline_id}/jobs")
            response.raise_for_status()
            jobs = response.json()
            logger.info("gitlab_pipeline_jobs_fetched", project_id=project_id, pipeline_id=pipeline_id, count=len(jobs))
            return jobs
        except httpx.HTTPError as e:
            logger.error("gitlab_get_pipeline_jobs_failed", project_id=project_id, pipeline_id=pipeline_id, error=str(e))
            raise

    async def trigger_pipeline(self, project_id: int, ref: str, variables: Optional[dict] = None) -> dict:
        """触发流水线"""
        client = await self.get_http_client()
        data = {"ref": ref}

        if variables:
            data["variables"] = [{"key": k, "value": v} for k, v in variables.items()]

        try:
            response = await client.post(f"/projects/{project_id}/pipeline", json=data)
            response.raise_for_status()
            pipeline = response.json()
            logger.info("gitlab_pipeline_triggered", project_id=project_id, ref=ref, pipeline_id=pipeline.get("id"))
            return pipeline
        except httpx.HTTPError as e:
            logger.error("gitlab_trigger_pipeline_failed", project_id=project_id, ref=ref, error=str(e))
            raise

    # MR相关方法
    async def get_merge_requests(self, project_id: int, state: str = "opened", per_page: int = 20) -> List[dict]:
        """获取合并请求列表"""
        client = await self.get_http_client()
        params = {"state": state, "per_page": per_page}

        try:
            response = await client.get(f"/projects/{project_id}/merge_requests", params=params)
            response.raise_for_status()
            mrs = response.json()
            logger.info("gitlab_mrs_fetched", project_id=project_id, state=state, count=len(mrs))
            return mrs
        except httpx.HTTPError as e:
            logger.error("gitlab_get_mrs_failed", project_id=project_id, error=str(e))
            raise

    async def get_merge_request(self, project_id: int, mr_iid: int) -> dict:
        """获取合并请求详情"""
        client = await self.get_http_client()

        try:
            response = await client.get(f"/projects/{project_id}/merge_requests/{mr_iid}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("gitlab_get_mr_failed", project_id=project_id, mr_iid=mr_iid, error=str(e))
            raise

    async def create_merge_request_note(self, project_id: int, mr_iid: int, body: str) -> dict:
        """为合并请求创建评论"""
        client = await self.get_http_client()

        try:
            response = await client.post(
                f"/projects/{project_id}/merge_requests/{mr_iid}/notes",
                json={"body": body}
            )
            response.raise_for_status()
            logger.info("gitlab_mr_note_created", project_id=project_id, mr_iid=mr_iid)
            return response.json()
        except httpx.HTTPError as e:
            logger.error("gitlab_create_mr_note_failed", project_id=project_id, mr_iid=mr_iid, error=str(e))
            raise

    # 用户相关方法
    async def get_current_user(self) -> dict:
        """获取当前用户信息"""
        client = await self.get_http_client()

        try:
            response = await client.get("/user")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("gitlab_get_current_user_failed", error=str(e))
            raise


# 全局单例
@lru_cache()
def get_gitlab_client() -> GitLabClient:
    """获取GitLab客户端单例"""
    return GitLabClient()


# 导出
gitlab_client = GitLabClient()
