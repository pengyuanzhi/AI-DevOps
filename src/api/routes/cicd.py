"""CI/CD 配置生成 API 路由."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.core.config import CICDConfigGenerator, NaturalLanguageParser, TemplateManager
from src.core.llm.factory import get_llm_client
from src.models.cicd import (
    CICDConfigRequest,
    CICDConfigResult,
    OptimizationRequest,
    TemplateInfo,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["cicd"])


# 请求/响应模型
class GenerateConfigRequest(BaseModel):
    """生成配置请求."""

    user_input: str = Field(
        ..., description="自然语言描述，如：'我有一个C++项目，使用CMake构建，需要运行测试'"
    )
    project_id: int = Field(..., description="GitLab 项目 ID")
    branch: str = Field(default="main", description="目标分支")
    commit_config: bool = Field(default=False, description="是否提交到仓库")
    project_files: list[str] = Field(default_factory=list, description="项目文件列表（可选）")
    optimization_goals: list[str] = Field(
        default_factory=list, description="优化目标：speed, cost, reliability"
    )


class GenerateConfigResponse(BaseModel):
    """生成配置响应."""

    config: str = Field(..., description=".gitlab-ci.yml 配置内容")
    explanation: str = Field(..., description="配置说明")
    parsed_requirements: dict = Field(..., description="解析的需求")
    stages: list[str] = Field(..., description="包含的 stages")
    template_used: str | None = Field(None, description="使用的模板")
    optimization_applied: list[str] = Field(default_factory=list, description="应用的优化")
    warnings: list[str] = Field(default_factory=list, description="警告信息")
    estimated_time_saved: str | None = Field(None, description="预计节省的时间")


class ListTemplatesResponse(BaseModel):
    """模板列表响应."""

    templates: list[TemplateInfo] = Field(..., description="可用模板列表")


class OptimizeConfigRequest(BaseModel):
    """优化配置请求."""

    current_config: str = Field(..., description="当前的 .gitlab-ci.yml 内容")
    project_id: int = Field(..., description="GitLab 项目 ID")
    optimization_goals: list[str] = Field(
        default_factory=list, description="优化目标：speed, cost, reliability"
    )
    project_type: str | None = Field(None, description="项目类型（用于更精确的优化）")


# 端点实现
@router.post(
    "/api/v1/cicd/generate",
    response_model=GenerateConfigResponse,
    summary="生成 GitLab CI 配置",
    description="""
    根据自然语言描述生成 .gitlab-ci.yml 配置文件。

    ## 使用示例

    ```bash
    curl -X POST http://localhost:8000/api/v1/cicd/generate \\
      -H "Content-Type: application/json" \\
      -d '{
        "user_input": "我有一个C++项目，使用CMake构建，需要运行Google Test测试",
        "project_id": 123
      }'
    ```

    ## 支持的项目类型

    - C++ (CMake, Makefile)
    - QT (CMake)
    - Python (pytest, unittest)
    - Node.js (npm)
    - Java (Maven, Gradle)

    ## 生成内容

    - 完整的 .gitlab-ci.yml 配置
    - 自动启用 ccache（C++项目）
    - 配置 artifacts 缓存
    - 并行构建优化
    """,
)
async def generate_cicd_config(request: GenerateConfigRequest) -> GenerateConfigResponse:
    """生成 GitLab CI 配置."""
    logger.info(
        "generate_cicd_config",
        project_id=request.project_id,
        input_length=len(request.user_input),
        has_project_files=len(request.project_files) > 0,
    )

    try:
        # 获取 LLM 客户端
        llm_client = get_llm_client()
        if not llm_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM 服务不可用，请检查配置",
            )

        # 初始化组件
        parser = NaturalLanguageParser(llm_client)
        template_manager = TemplateManager()
        generator = CICDConfigGenerator(llm_client, template_manager)

        # 解析需求
        requirements = await parser.parse_requirements(request.user_input)

        # 如果提供了项目文件，进行项目检测
        project_context = None
        if request.project_files:
            from src.core.analyzers.project_detector import ProjectDetector

            detector = ProjectDetector()
            project_context = await detector.detect_project_type(request.project_files)

        # 生成配置
        result: CICDConfigResult = await generator.generate_config(
            requirements=requirements,
            project_context=project_context,
            user_input=request.user_input,
        )

        logger.info(
            "generate_cicd_config_success",
            project_id=request.project_id,
            template_used=result.template_used,
            stages=result.stages,
        )

        return GenerateConfigResponse(
            config=result.config,
            explanation=result.explanation,
            parsed_requirements=result.parsed_requirements,
            stages=result.stages,
            template_used=result.template_used,
            optimization_applied=result.optimization_applied,
            warnings=result.warnings,
            estimated_time_saved=result.estimated_time_saved,
        )

    except Exception as e:
        logger.error(
            "generate_cicd_config_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"配置生成失败: {str(e)}",
        )


@router.get(
    "/api/v1/cicd/templates",
    response_model=ListTemplatesResponse,
    summary="列出可用的配置模板",
    description="""
    列出所有可用的 CI/CD 配置模板。

    ## 使用示例

    ```bash
    curl http://localhost:8000/api/v1/cicd/templates

    # 过滤项目类型
    curl http://localhost:8000/api/v1/cicd/templates?project_type=cpp
    ```

    ## 模板分类

    - **cpp**: C++ 项目模板
    - **qt**: QT 项目模板
    - **python**: Python 项目模板
    - **nodejs**: Node.js 项目模板
    """,
)
async def list_templates(
    project_type: str | None = None,
) -> ListTemplatesResponse:
    """列出可用模板."""
    logger.info(
        "list_templates",
        project_type=project_type,
    )

    try:
        template_manager = TemplateManager()
        templates = template_manager.list_templates(project_type=project_type)

        template_infos = [
            TemplateInfo(
                name=t.id,
                display_name=t.name,
                description=t.description,
                category=t.category,
                tags=t.tags,
                estimated_build_time=t.estimated_build_time,
            )
            for t in templates
        ]

        return ListTemplatesResponse(templates=template_infos)

    except Exception as e:
        logger.error(
            "list_templates_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模板列表失败: {str(e)}",
        )


@router.post(
    "/api/v1/cicd/optimize",
    summary="优化现有配置（实验性）",
    description="""
    优化现有的 GitLab CI 配置。

    **注意**: 此功能正在开发中，目前仅提供基础的配置分析和改进建议。

    ## 使用示例

    ```bash
    curl -X POST http://localhost:8000/api/v1/cicd/optimize \\
      -H "Content-Type: application/json" \\
      -d '{
        "current_config": "stages:\\n  - build\\nbuild:\\n  script: make",
        "optimization_goals": ["speed"],
        "project_id": 123
      }'
    ```
    """,
)
async def optimize_cicd_config(request: OptimizeConfigRequest):
    """优化现有配置."""
    logger.info(
        "optimize_cicd_config",
        project_id=request.project_id,
        goals=request.optimization_goals,
    )

    # TODO: 实现配置优化逻辑
    # 这是 Phase 2 的功能
    return {
        "message": "配置优化功能正在开发中",
        "current_config": request.current_config,
        "optimization_goals": request.optimization_goals,
        "suggestions": [
            "启用 ccache 可以减少 30-50% 的构建时间",
            "使用并行构建可以充分利用 CPU 资源",
            "配置 artifacts 缓存可以减少重复下载",
        ],
    }


@router.get(
    "/api/v1/cicd/health",
    summary="健康检查",
    description="检查 CI/CD 配置服务的健康状态。",
)
async def health_check():
    """健康检查."""
    llm_client = get_llm_client()
    llm_available = llm_client is not None

    return {
        "status": "healthy" if llm_available else "degraded",
        "llm_available": llm_available,
        "version": "0.2.0",
    }
