"""
Claude API 客户端

封装 Anthropic Claude API 调用
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from anthropic import Anthropic, AsyncAnthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.utils.config import settings

logger = structlog.get_logger(__name__)


class ClaudeAPIError(Exception):
    """Claude API 错误"""
    pass


class ClaudeClient:
    """Claude API 客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        timeout: int = 60,
    ):
        """
        初始化 Claude 客户端

        Args:
            api_key: Claude API 密钥
            model: 模型名称
            max_tokens: 最大 token 数
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.claude_model
        self.max_tokens = max_tokens
        self.timeout = timeout

        # 创建同步和异步客户端
        self.client = Anthropic(api_key=self.api_key, timeout=self.timeout)
        self.async_client = AsyncAnthropic(api_key=self.api_key, timeout=self.timeout)

        logger.info(
            "claude_client_initialized",
            model=self.model,
            max_tokens=max_tokens,
        )

    @retry(
        retry=retry_if_exception_type((ClaudeAPIError, OSError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        生成文本

        Args:
            prompt: 用户提示
            max_tokens: 最大 token 数
            temperature: 温度参数（0-1）
            system_prompt: 系统提示

        Returns:
            str: 生成的文本

        Raises:
            ClaudeAPIError: API 调用失败
        """
        max_tokens = max_tokens or self.max_tokens

        logger.debug(
            "claude_generation_start",
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            prompt_length=len(prompt),
        )

        try:
            start_time = datetime.now()

            response = await self.async_client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            # 提取文本内容
            content = response.content[0].text

            duration = (datetime.now() - start_time).total_seconds()

            # 记录使用情况
            logger.info(
                "claude_generation_success",
                model=self.model,
                duration_seconds=duration,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )

            return content

        except Exception as e:
            logger.error(
                "claude_generation_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ClaudeAPIError(f"Claude API 调用失败: {e}")

    @retry(
        retry=retry_if_exception_type((ClaudeAPIError, OSError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def generate_stream(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ):
        """
        流式生成文本

        Args:
            prompt: 用户提示
            max_tokens: 最大 token 数
            temperature: 温度参数（0-1）
            system_prompt: 系统提示

        Yields:
            str: 生成的文本片段
        """
        max_tokens = max_tokens or self.max_tokens

        logger.debug(
            "claude_stream_generation_start",
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        try:
            async with self.async_client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(
                "claude_stream_generation_failed",
                error=str(e),
            )
            raise ClaudeAPIError(f"Claude API 流式调用失败: {e}")

    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的 token 数

        Args:
            text: 输入文本

        Returns:
            int: 估算的 token 数（粗略估计：约 4 字符 = 1 token）
        """
        # 粗略估算：英文约 4 字符 = 1 token，中文约 2-3 字符 = 1 token
        # 这里使用简单的字符计数除以 4
        return len(text) // 4

    def count_tokens(self, text: str) -> int:
        """
        精确计算 token 数（使用 tiktoken）

        Args:
            text: 输入文本

        Returns:
            int: token 数
        """
        try:
            import tiktoken

            # 使用 claude 的编码（近似于 GPT-4）
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except ImportError:
            # 如果 tiktoken 不可用，回退到估算
            return self.estimate_tokens(text)


# 全局客户端实例
_claude_client: Optional[ClaudeClient] = None


def get_claude_client() -> ClaudeClient:
    """获取 Claude 客户端实例（单例）"""
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
    return _claude_client
