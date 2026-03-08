"""
LLM 客户端工厂

根据配置返回相应的 LLM 客户端
"""

from typing import Optional, Union

from src.core.llm.claude_client import ClaudeClient
from src.core.llm.zhipu_client import ZhipuClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


# LLM 客户端类型
LLMClient = Union[ClaudeClient, ZhipuClient]


def get_llm_client(provider: Optional[str] = None) -> Optional[LLMClient]:
    """
    获取 LLM 客户端

    Args:
        provider: LLM 提供商（claude, openai, zhipu）
                 如果为 None，则使用配置中的默认提供商

    Returns:
        LLM 客户端实例，如果配置无效则返回 None
    """
    from src.utils.config import settings

    # 确定使用的提供商
    if provider is None:
        provider = settings.default_llm_provider

    logger.info(
        "get_llm_client",
        provider=provider,
        configured_provider=settings.default_llm_provider,
    )

    # 根据提供商返回相应的客户端
    if provider == "zhipu":
        from src.core.llm import get_zhipu_client

        client = get_zhipu_client()
        if client is None:
            logger.error("zhipu_client_not_available")
            return None

        logger.info("using_zhipu_client", model=settings.zhipu_model)
        return client

    elif provider == "claude":
        from src.core.llm import get_claude_client

        client = get_claude_client()
        if client is None:
            logger.error("claude_client_not_available")
            return None

        logger.info("using_claude_client", model=settings.claude_model)
        return client

    elif provider == "openai":
        logger.error("openai_client_not_implemented")
        return None

    else:
        logger.error(
            "unknown_llm_provider",
            provider=provider,
        )
        return None


def get_available_providers() -> list[str]:
    """
    获取可用的 LLM 提供商列表

    Returns:
        可用的提供商名称列表
    """
    from src.utils.config import settings

    available = []

    # 检查智谱 AI
    if settings.zhipu_api_key:
        available.append("zhipu")

    # 检查 Claude
    if settings.anthropic_api_key:
        available.append("claude")

    # 检查 OpenAI
    if settings.openai_api_key:
        available.append("openai")

    logger.info(
        "available_providers",
        providers=available,
        default=settings.default_llm_provider,
    )

    return available
