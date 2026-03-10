"""
AI 功能测试 API

用于测试 LLM 集成和 AI 功能
"""

from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.core.llm.factory import get_llm_client, get_available_providers
from src.utils.logger import get_logger
from src.utils.config import settings

logger = get_logger(__name__)
router = APIRouter(prefix="/ai", tags=["AI测试"])


class TestModelRequest(BaseModel):
    """测试模型请求"""
    provider: Optional[str] = None
    prompt: str = "你好，请用一句话介绍你自己。"
    temperature: float = 0.7
    max_tokens: int = 500


class CodeReviewRequest(BaseModel):
    """代码审查请求"""
    code: str
    language: str = "cpp"
    provider: Optional[str] = None


class TestSelectionRequest(BaseModel):
    """测试选择请求"""
    changed_files: List[str]
    provider: Optional[str] = None


@router.get("/status")
async def get_ai_status() -> Dict[str, any]:
    """
    获取 AI 服务状态

    返回可用的 LLM 提供商和配置信息
    """
    available_providers = get_available_providers()

    return {
        "status": "ok",
        "available_providers": available_providers,
        "default_provider": settings.default_llm_provider,
        "config": {
            "claude": {
                "configured": bool(settings.anthropic_api_key),
                "model": settings.claude_model,
            },
            "zhipu": {
                "configured": bool(settings.zhipu_api_key),
                "model": settings.zhipu_model,
                "api_key_preview": settings.zhipu_api_key[:10] + "..." if settings.zhipu_api_key else None,
            },
            "openai": {
                "configured": bool(settings.openai_api_key),
                "model": settings.openai_model,
            },
        },
        "features": {
            "code_review": settings.ENABLE_CODE_REVIEW,
            "test_generation": settings.ENABLE_TEST_GENERATION,
            "pipeline_generation": settings.ENABLE_PIPELINE_GENERATION,
        },
    }


@router.post("/test-model")
async def test_model(request: TestModelRequest) -> Dict[str, any]:
    """
    测试 LLM 模型

    发送测试请求到指定的 LLM 提供商
    """
    try:
        # 获取 LLM 客户端
        client = get_llm_client(provider=request.provider)

        if client is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LLM 客户端未配置或不可用",
            )

        # 生成文本
        logger.info(
            "testing_llm_model",
            provider=request.provider or settings.default_llm_provider,
            prompt_length=len(request.prompt),
        )

        response = await client.generate(
            prompt=request.prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        logger.info(
            "llm_test_success",
            response_length=len(response),
        )

        return {
            "status": "success",
            "provider": request.provider or settings.default_llm_provider,
            "model": client.model if hasattr(client, 'model') else "unknown",
            "prompt": request.prompt,
            "response": response,
            "response_length": len(response),
        }

    except Exception as e:
        logger.error(
            "llm_test_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM 测试失败: {str(e)}",
        )


@router.post("/code-review")
async def test_code_review(request: CodeReviewRequest) -> Dict[str, any]:
    """
    测试 AI 代码审查功能

    使用 AI 分析代码并提供改进建议
    """
    try:
        # 获取 LLM 客户端
        client = get_llm_client(provider=request.provider)

        if client is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LLM 客户端未配置或不可用",
            )

        # 构建代码审查提示词
        system_prompt = f"""你是一个经验丰富的{request.language}代码审查专家。
你的任务是：
1. 识别代码中的潜在bug和安全问题
2. 指出代码质量问题
3. 提供改进建议
4. 遵循{request.language}最佳实践

请以JSON格式返回结果，包含以下字段：
- issues: 问题列表
- suggestions: 改进建议
- score: 代码质量评分（0-100）
"""

        user_prompt = f"""请审查以下{request.language}代码：

```{request.language}
{request.code}
```

请提供详细的审查结果。"""

        # 生成审查结果
        response = await client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=2000,
        )

        logger.info(
            "code_review_test_success",
            code_length=len(request.code),
            response_length=len(response),
        )

        return {
            "status": "success",
            "provider": request.provider or settings.default_llm_provider,
            "code_review": response,
            "code_length": len(request.code),
        }

    except Exception as e:
        logger.error(
            "code_review_test_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"代码审查失败: {str(e)}",
        )


@router.post("/test-selection")
async def test_test_selection(request: TestSelectionRequest) -> Dict[str, any]:
    """
    测试智能测试选择功能

    基于变更的文件，AI分析影响域并建议需要运行的测试
    """
    try:
        # 获取 LLM 客户端
        client = get_llm_client(provider=request.provider)

        if client is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LLM 客户端未配置或不可用",
            )

        # 构建测试选择提示词
        system_prompt = """你是一个测试策略专家。
基于代码变更，你需要：
1. 分析变更影响的功能模块
2. 识别需要测试的场景
3. 推荐需要运行的测试用例
4. 评估测试优先级

请返回JSON格式，包含：
- affected_modules: 受影响的模块列表
- recommended_tests: 推荐的测试列表
- priority: 测试优先级（high/medium/low）
- estimated_time: 预计测试时间（分钟）
"""

        user_prompt = f"""以下文件发生了变更：

{chr(10).join(f'- {f}' for f in request.changed_files)}

请分析这些变更的影响域，并推荐需要运行的测试。"""

        # 生成测试选择建议
        response = await client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=1500,
        )

        logger.info(
            "test_selection_test_success",
            files_count=len(request.changed_files),
            response_length=len(response),
        )

        return {
            "status": "success",
            "provider": request.provider or settings.default_llm_provider,
            "changed_files": request.changed_files,
            "test_selection": response,
        }

    except Exception as e:
        logger.error(
            "test_selection_test_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"测试选择失败: {str(e)}",
        )


@router.get("/providers")
async def get_providers() -> Dict[str, any]:
    """
    获取可用的 LLM 提供商信息
    """
    available = get_available_providers()

    providers_info = {
        "zhipu": {
            "name": "智谱AI",
            "models": ["glm-5", "glm-4-flash", "glm-4-plus", "glm-4-0520", "glm-4-air", "glm-3-turbo"],
            "available": "zhipu" in available,
            "current_model": settings.zhipu_model,
        },
        "claude": {
            "name": "Claude (Anthropic)",
            "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
            "available": "claude" in available,
            "current_model": settings.claude_model,
        },
        "openai": {
            "name": "OpenAI",
            "models": ["gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo"],
            "available": "openai" in available,
            "current_model": settings.openai_model,
            "note": "未实现",
        },
    }

    return {
        "available_providers": available,
        "default_provider": settings.default_llm_provider,
        "providers": providers_info,
    }
