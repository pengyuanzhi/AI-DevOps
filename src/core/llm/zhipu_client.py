"""
智谱 AI (Zhipu AI / GLM) 客户端
"""

from typing import Any, Dict, List, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ZhipuClient:
    """智谱 AI 客户端"""

    def __init__(
        self,
        api_key: str,
        model: str = "glm-4-flash",
        base_url: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        timeout: int = 120,
    ):
        """
        初始化智谱 AI 客户端

        Args:
            api_key: 智谱 API Key
            model: 模型名称（glm-4-flash, glm-4-plus, glm-4-0520 等）
            base_url: API 端点
            timeout: 超时时间（秒）
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

        # 解析 API Key 获取 JWT ID
        # 智谱 API Key 格式: id.secret
        if "." in api_key:
            self.jwt_id = api_key.split(".")[0]
        else:
            self.jwt_id = api_key

        logger.info(
            "zhipu_client_initialized",
            model=model,
            jwt_id=self.jwt_id[:8] + "...",  # 只显示前 8 位
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        top_p: float = 0.9,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        生成文本

        Args:
            prompt: 用户提示词
            temperature: 温度参数（0-1）
            max_tokens: 最大 token 数
            top_p: top-p 采样参数
            system_prompt: 系统提示词
            messages: 对话历史（可选）

        Returns:
            生成的文本
        """
        try:
            # 构建消息列表
            if messages is None:
                messages = []

            # 添加系统提示词
            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})

            # 添加用户提示词
            messages.append({"role": "user", "content": prompt})

            # 请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # 请求体
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
                "stream": False,
            }

            logger.debug(
                "zhipu_api_request",
                model=self.model,
                messages_count=len(messages),
                prompt_length=len(prompt),
            )

            # 发送请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                )

                # 检查响应状态
                if response.status_code != 200:
                    error_msg = f"智谱 API 请求失败: {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail.get('error', {}).get('message', '未知错误')}"
                    except Exception:
                        error_msg += f" - {response.text[:200]}"

                    logger.error(
                        "zhipu_api_error",
                        status_code=response.status_code,
                        error=error_msg,
                    )
                    raise Exception(error_msg)

                # 解析响应
                result = response.json()

                if "choices" not in result or not result["choices"]:
                    logger.error("zhipu_api_no_choices", response=result)
                    raise Exception("智谱 API 返回了空响应")

                generated_text = result["choices"][0]["message"]["content"]

                logger.info(
                    "zhipu_api_success",
                    model=self.model,
                    output_length=len(generated_text),
                    usage=result.get("usage", {}),
                )

                return generated_text

        except httpx.TimeoutException:
            logger.error("zhipu_api_timeout")
            raise Exception("智谱 API 请求超时")

        except httpx.NetworkError as e:
            logger.error("zhipu_api_network_error", error=str(e))
            raise Exception(f"智谱 API 网络错误: {str(e)}")

        except Exception as e:
            logger.error(
                "zhipu_api_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def generate_with_history(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        top_p: float = 0.9,
    ) -> str:
        """
        基于对话历史生成文本

        Args:
            messages: 对话历史列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            top_p: top-p 采样参数

        Returns:
            生成的文本
        """
        try:
            # 请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # 请求体
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
                "stream": False,
            }

            logger.debug(
                "zhipu_api_request_with_history",
                model=self.model,
                messages_count=len(messages),
            )

            # 发送请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                )

                if response.status_code != 200:
                    error_msg = f"智谱 API 请求失败: {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail.get('error', {}).get('message', '未知错误')}"
                    except Exception:
                        error_msg += f" - {response.text[:200]}"
                    raise Exception(error_msg)

                # 解析响应
                result = response.json()

                if "choices" not in result or not result["choices"]:
                    raise Exception("智谱 API 返回了空响应")

                generated_text = result["choices"][0]["message"]["content"]

                logger.info(
                    "zhipu_api_success_with_history",
                    model=self.model,
                    output_length=len(generated_text),
                )

                return generated_text

        except Exception as e:
            logger.error("zhipu_generate_with_history_failed", error=str(e))
            raise

    def validate_api_key(self) -> bool:
        """
        验证 API Key 格式

        Returns:
            是否有效
        """
        if not self.api_key:
            return False

        # 智谱 API Key 格式: id.secret
        if "." not in self.api_key:
            logger.warning("zhipu_api_key_invalid_format", api_key=self.api_key[:10] + "...")
            return False

        parts = self.api_key.split(".")
        if len(parts) != 2:
            return False

        return True

    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息

        Returns:
            模型信息字典
        """
        return {
            "provider": "zhipu",
            "model": self.model,
            "base_url": self.base_url,
            "available_models": [
                "glm-5",            # 最新一代模型
                "glm-4-flash",     # 快速推理模型
                "glm-4-plus",      # 增强版模型
                "glm-4-0520",      # GLM-4 最新版
                "glm-4-air",       # 轻量级模型
                "glm-3-turbo",     # 上一代模型
            ],
        }


# 全局实例
_zhipu_client: Optional[ZhipuClient] = None


def get_zhipu_client() -> Optional[ZhipuClient]:
    """
    获取智谱 AI 客户端实例（单例）

    Returns:
        ZhipuClient 实例，如果未配置则返回 None
    """
    global _zhipu_client
    if _zhipu_client is None:
        from src.utils.config import settings

        if not settings.zhipu_api_key:
            logger.warning("zhipu_api_key_not_set")
            return None

        _zhipu_client = ZhipuClient(
            api_key=settings.zhipu_api_key,
            model=getattr(settings, "zhipu_model", "glm-4-flash"),
        )

        # 验证 API Key
        if not _zhipu_client.validate_api_key():
            logger.error("zhipu_api_key_invalid")
            return None

    return _zhipu_client
