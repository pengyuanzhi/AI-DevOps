"""
GitLab Webhook API路由
"""

from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from ...db.session import get_db_session
from ...integrations.gitlab.webhook import webhook_processor

router = APIRouter()


@router.post("/gitlab")
async def handle_gitlab_webhook(
    request: Request,
    db: Session = Depends(get_db_session),
):
    """
    接收并处理GitLab Webhook事件

    支持的事件类型:
    - Push Hook: 代码推送事件
    - Merge Request Hook: 合并请求事件
    - Pipeline Hook: 流水线事件
    - Job Hook: 作业事件
    - Note Hook: 评论事件
    """
    return await webhook_processor.process_webhook(request, db)
