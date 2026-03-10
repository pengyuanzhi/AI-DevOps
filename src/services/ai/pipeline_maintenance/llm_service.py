"""
LLM Service Wrapper

Provides a unified interface for LLM interactions in the pipeline maintenance system.
Wraps the existing LLM client factory.
"""

from typing import Optional, Any
from ....core.llm.factory import get_llm_client, LLMClient
from ....utils.logger import get_logger

logger = get_logger(__name__)


class LLMService:
    """
    LLM服务包装器

    提供统一的LLM调用接口，支持多种LLM提供商
    """

    def __init__(self, provider: Optional[str] = None):
        """
        初始化LLM服务

        Args:
            provider: LLM提供商 (zhipu, claude, openai)，None则使用默认配置
        """
        self.provider = provider
        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        """初始化LLM客户端"""
        try:
            self._client = get_llm_client(self.provider)
            if self._client:
                logger.info(
                    "llm_service_initialized",
                    provider=self.provider or "default",
                )
            else:
                logger.warning(
                    "llm_client_not_available",
                    provider=self.provider,
                )
        except Exception as e:
            logger.error(
                "llm_client_init_failed",
                provider=self.provider,
                error=str(e),
                exc_info=True,
            )
            self._client = None

    def is_available(self) -> bool:
        """
        检查LLM服务是否可用

        Returns:
            True如果客户端已初始化且可用
        """
        return self._client is not None

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Optional[str]:
        """
        生成LLM响应

        Args:
            prompt: 提示文本
            max_tokens: 最大token数
            temperature: 温度参数
            **kwargs: 其他参数

        Returns:
            生成的文本，失败返回None
        """
        if not self.is_available():
            logger.warning("llm_service_not_available")
            return None

        try:
            # 调用底层客户端
            if hasattr(self._client, 'generate'):
                response = await self._client.generate(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                return response
            elif hasattr(self._client, 'chat'):
                # 某些客户端使用chat接口
                response = await self._client.chat(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                return response
            else:
                logger.error("llm_client_no_generate_method")
                return None

        except Exception as e:
            logger.error(
                "llm_generate_failed",
                error=str(e),
                exc_info=True,
            )
            return None

    async def chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Optional[str]:
        """
        对话式LLM调用

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            max_tokens: 最大token数
            temperature: 温度参数
            **kwargs: 其他参数

        Returns:
            生成的文本，失败返回None
        """
        if not self.is_available():
            logger.warning("llm_service_not_available")
            return None

        try:
            if hasattr(self._client, 'chat'):
                response = await self._client.chat(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                return response
            elif hasattr(self._client, 'generate'):
                # 回退到generate接口
                prompt = self._messages_to_prompt(messages)
                response = await self._client.generate(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                return response
            else:
                logger.error("llm_client_no_chat_method")
                return None

        except Exception as e:
            logger.error(
                "llm_chat_failed",
                error=str(e),
                exc_info=True,
            )
            return None

    def _messages_to_prompt(self, messages: list[dict[str, str]]) -> str:
        """将消息列表转换为提示文本"""
        lines = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def get_provider(self) -> Optional[str]:
        """获取当前使用的提供商"""
        return self.provider

    def reload(self, provider: Optional[str] = None):
        """
        重新加载LLM客户端

        Args:
            provider: 新的提供商，None则保持原提供商
        """
        if provider is not None:
            self.provider = provider
        self._initialize_client()
