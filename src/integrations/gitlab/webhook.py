"""
GitLab Webhook处理

处理GitLab发送的Webhook事件。
"""

import hmac
import hashlib
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
from structlog import get_logger

from ...utils.config import settings
from ...services.gitlab_service import gitlab_service
from ...db.session import get_db_session

logger = get_logger(__name__)


class WebhookProcessor:
    """Webhook处理器"""

    async def verify_signature(self, payload: bytes, signature: str) -> bool:
        """验证Webhook签名"""
        if not settings.gitlab_webhook_secret:
            logger.warning("webhook_secret_not_configured")
            return True
        
        # 计算HMAC-SHA256签名
        expected_signature = hmac.new(
            settings.gitlab_webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        
        # GitLab发送的签名格式为: sha256=<signature>
        token = signature.split("=")[1] if "=" in signature else signature
        
        is_valid = hmac.compare_digest(expected_signature, token)
        if not is_valid:
            logger.warning("webhook_signature_invalid")
        
        return is_valid

    async def handle_push_event(self, event_data: dict, db: Session):
        """处理Push事件"""
        project_id = event_data["project"]["id"]
        ref = event_data.get("ref", "")
        branch = ref.replace("refs/heads/", "") if ref else ""
        
        logger.info(
            "push_event_received",
            project_id=project_id,
            branch=branch,
            commits_count=len(event_data.get("commits", [])),
        )
        
        # 同步项目
        await gitlab_service.sync_project(db, project_id)
        
        # TODO: 触发智能测试选择
        # TODO: 触发静态代码审查

    async def handle_merge_request_event(self, event_data: dict, db: Session):
        """处理合并请求事件"""
        mr = event_data.get("object_attributes", {})
        project = event_data.get("project", {})
        
        action = mr.get("action")
        mr_iid = mr.get("iid")
        mr_state = mr.get("state")
        
        logger.info(
            "mr_event_received",
            project_id=project.get("id"),
            mr_iid=mr_iid,
            action=action,
            state=mr_state,
        )
        
        if action == "open" or action == "reopen":
            # MR打开或重新打开
            # TODO: 触发智能测试选择
            # TODO: 触发代码审查
            pass
        elif action == "merge":
            # MR合并
            # TODO: 更新代码质量指标
            pass
        elif action == "close":
            # MR关闭
            pass
        
        # 同步项目
        await gitlab_service.sync_project(db, project["id"])

    async def handle_pipeline_event(self, event_data: dict, db: Session):
        """处理流水线事件"""
        pipeline_attrs = event_data.get("object_attributes", {})
        project = event_data.get("project", {})
        
        pipeline_id = pipeline_attrs.get("id")
        status = pipeline_attrs.get("status")
        
        logger.info(
            "pipeline_event_received",
            project_id=project.get("id"),
            pipeline_id=pipeline_id,
            status=status,
        )
        
        # TODO: 根据流水线状态更新数据库
        # TODO: 如果流水线失败，触发自主维护
        if status == "failed":
            pass
        elif status == "success":
            pass

    async def handle_job_event(self, event_data: dict, db: Session):
        """处理作业事件"""
        job_attrs = event_data.get("object_attributes", {})
        project = event_data.get("project", {})
        
        job_id = job_attrs.get("id")
        job_name = job_attrs.get("name")
        status = job_attrs.get("status")
        
        logger.info(
            "job_event_received",
            project_id=project.get("id"),
            job_id=job_id,
            job_name=job_name,
            status=status,
        )
        
        # TODO: 更新作业状态
        # TODO: 收集日志和测试结果

    async def handle_note_event(self, event_data: dict, db: Session):
        """处理评论事件"""
        note_attrs = event_data.get("object_attributes", {})
        project = event_data.get("project", {})
        
        note_type = note_attrs.get("noteable_type")
        action = note_attrs.get("action")
        
        logger.info(
            "note_event_received",
            project_id=project.get("id"),
            note_type=note_type,
            action=action,
        )
        
        # TODO: 处理评论事件，例如触发重新分析

    async def process_webhook(self, request: Request, db: Session):
        """处理Webhook请求"""
        # 读取payload
        payload = await request.body()
        
        # 验证签名
        signature = request.headers.get("X-Gitlab-Token", "")
        is_valid = await self.verify_signature(payload, signature)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # 解析事件数据
        import json
        event_data = json.loads(payload.decode())
        event_type = request.headers.get("X-Gitlab-Event", "")
        
        logger.info(
            "webhook_received",
            event_type=event_type,
            project_id=event_data.get("project", {}).get("id"),
        )
        
        # 根据事件类型分发处理
        if event_type == "Push Hook":
            await self.handle_push_event(event_data, db)
        elif event_type == "Merge Request Hook":
            await self.handle_merge_request_event(event_data, db)
        elif event_type == "Pipeline Hook":
            await self.handle_pipeline_event(event_data, db)
        elif event_type == "Job Hook":
            await self.handle_job_event(event_data, db)
        elif event_type == "Note Hook":
            await self.handle_note_event(event_data, db)
        else:
            logger.warning("unsupported_webhook_event", event_type=event_type)
        
        return {"status": "ok"}


# 全局单例
webhook_processor = WebhookProcessor()
