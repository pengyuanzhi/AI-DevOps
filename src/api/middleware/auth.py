"""
GitLab Webhook 签名验证中间件

验证 GitLab 发送的 webhook 请求签名
"""

from functools import lru_cache
from typing import Callable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.utils.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GitLabWebhookAuthMiddleware(BaseHTTPMiddleware):
    """
    GitLab Webhook 签名验证中间件

    验证请求是否来自合法的 GitLab webhook
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """
        处理请求

        Args:
            request: 传入的请求
            call_next: 下一个中间件或路由处理器

        Returns:
            响应对象

        Raises:
            HTTPException: 签名验证失败
        """
        # 只对 webhook 端点进行签名验证
        if request.url.path.startswith("/webhook"):
            if not await self.verify_webhook_signature(request):
                logger.warning(
                    "webhook_signature_verification_failed",
                    path=request.url.path,
                    client_host=request.client.host if request.client else None,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid webhook signature",
                )

            logger.info(
                "webhook_signature_verified",
                path=request.url.path,
            )

        # 调用下一个中间件或路由处理器
        response = await call_next(request)
        return response

    async def verify_webhook_signature(self, request: Request) -> bool:
        """
        验证 GitLab webhook 签名

        Args:
            request: FastAPI 请求对象

        Returns:
            bool: 签名是否有效
        """
        # 方法1: 验证 X-Gitlab-Token 头（推荐）
        token = request.headers.get("X-Gitlab-Token")
        if token:
            return self._verify_token(token)

        # 方法2: 验证 X-Gitlab-Token（GitLab 14.0+）
        gitlab_token = request.headers.get("X-Gitlab-Token")
        if gitlab_token:
            return self._verify_token(gitlab_token)

        logger.warning("missing_webhook_token", headers=dict(request.headers))
        return False

    def _verify_token(self, token: str) -> bool:
        """
        验证 token 是否匹配

        Args:
            token: 请求中的 token

        Returns:
            bool: token 是否有效
        """
        # 使用常量时间比较，防止时序攻击
        import hmac

        expected_token = settings.gitlab_webhook_secret.encode()
        actual_token = token.encode()

        try:
            return hmac.compare_digest(expected_token, actual_token)
        except Exception as e:
            logger.error("token_verification_error", error=str(e))
            return False


@lru_cache()
def get_webhook_auth_middleware() -> GitLabWebhookAuthMiddleware:
    """
    获取 webhook 认证中间件单例

    Returns:
        GitLabWebhookAuthMiddleware 实例
    """
    return GitLabWebhookAuthMiddleware()
