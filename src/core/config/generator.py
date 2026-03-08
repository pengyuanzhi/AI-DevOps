"""GitLab CI 配置生成器."""

from pathlib import Path
from typing import Optional

from src.models.cicd import CICDConfigResult, ParsedRequirements, Template
from src.models.project import ProjectContext
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CICDConfigGenerator:
    """GitLab CI 配置生成器.

    根据解析的需求和项目上下文生成 .gitlab-ci.yml 配置文件。
    """

    def __init__(self, llm_client, template_manager):
        """初始化生成器.

        Args:
            llm_client: LLM 客户端实例
            template_manager: 模板管理器实例
        """
        self.llm = llm_client
        self.template_manager = template_manager
        self.generation_prompt_template = self._load_prompt_template(
            "prompts/cicd_config/generation.txt"
        )

    def _load_prompt_template(self, template_path: str) -> str:
        """加载 Prompt 模板.

        Args:
            template_path: 模板文件路径

        Returns:
            模板内容
        """
        try:
            template_file = Path(template_path)
            if template_file.exists():
                return template_file.read_text(encoding="utf-8")
            else:
                logger.warning(
                    "prompt_template_not_found",
                    template_path=template_path,
                )
                return self._get_default_generation_prompt()
        except Exception as e:
            logger.error(
                "load_prompt_template_failed",
                template_path=template_path,
                error=str(e),
            )
            return self._get_default_generation_prompt()

    def _get_default_generation_prompt(self) -> str:
        """获取默认的生成提示词."""
        return """你是一个GitLab CI/CD配置专家。

## 任务
根据用户需求生成 .gitlab-ci.yml 配置文件。

## 用户需求
{user_input}

## 项目上下文
- 项目类型: {project_type}
- 构建系统: {build_system}
- 测试框架: {test_framework}

## 生成要求
1. 使用GitLab CI语法
2. 包含合理的stages（build, test, deploy）
3. 如果是C++项目，启用ccache以加速构建
4. 配置artifacts缓存以减少重复下载
5. 添加必要的before_script和依赖安装
6. 确保配置简洁、可维护

## 输出格式
仅输出YAML配置，不要包含markdown标记（不要```yaml），直接输出YAML内容。"""

    async def generate_config(
        self,
        requirements: ParsedRequirements,
        project_context: Optional[ProjectContext] = None,
        user_input: Optional[str] = None,
    ) -> CICDConfigResult:
        """生成 GitLab CI 配置.

        Args:
            requirements: 解析后的需求
            project_context: 项目上下文
            user_input: 原始用户输入（用于 LLM 生成）

        Returns:
            配置生成结果
        """
        logger.info(
            "generate_config_start",
            project_type=requirements.project_type,
            build_system=requirements.build_system,
        )

        try:
            # 尝试使用模板生成
            template = self.template_manager.find_best_template(
                project_type=requirements.project_type,
                build_system=requirements.build_system,
                test_framework=requirements.test_framework,
            )

            if template:
                logger.info(
                    "using_template",
                    template_id=template.id,
                    template_name=template.name,
                )
                return await self._generate_from_template(
                    template, requirements, project_context
                )
            else:
                logger.info("no_template_found_using_llm")
                return await self._generate_from_llm(
                    requirements, project_context, user_input
                )

        except Exception as e:
            logger.error(
                "generate_config_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def _generate_from_template(
        self,
        template: Template,
        requirements: ParsedRequirements,
        project_context: Optional[ProjectContext] = None,
    ) -> CICDConfigResult:
        """从模板生成配置.

        Args:
            template: 模板对象
            requirements: 需求对象
            project_context: 项目上下文

        Returns:
            配置生成结果
        """
        logger.info(
            "generate_from_template",
            template_id=template.id,
        )

        # 获取模板内容
        config_content = template.content

        # 如果需要，可以添加额外的优化
        optimizations_applied = template.default_optimizations

        # 如果需要部署，添加 deploy stage
        if requirements.deployment_targets:
            config_content = self._add_deployment_stage(
                config_content, requirements.deployment_targets
            )
            optimizations_applied.append("deployment")

        # 生成说明
        explanation = self._generate_explanation(template, requirements)

        return CICDConfigResult(
            config=config_content,
            explanation=explanation,
            parsed_requirements=requirements.to_dict(),
            stages=requirements.stages,
            template_used=template.id,
            optimization_applied=optimizations_applied,
            warnings=[],
            estimated_time_saved="30-50%",
        )

    async def _generate_from_llm(
        self,
        requirements: ParsedRequirements,
        project_context: Optional[ProjectContext] = None,
        user_input: Optional[str] = None,
    ) -> CICDConfigResult:
        """使用 LLM 生成配置.

        Args:
            requirements: 需求对象
            project_context: 项目上下文
            user_input: 原始用户输入

        Returns:
            配置生成结果
        """
        logger.info("generate_from_llm")

        # 构建 Prompt
        user_input = user_input or f"为 {requirements.project_type} 项目生成 CI/CD 配置"
        prompt = self.generation_prompt_template.format(
            user_input=user_input,
            project_type=requirements.project_type,
            build_system=requirements.build_system or "未指定",
            test_framework=requirements.test_framework or "未指定",
        )

        # 调用 LLM
        system_prompt = "你是一个专业的GitLab CI/CD配置专家，精通各种编程语言和构建系统的CI/CD配置。"
        response = await self.llm.generate(
            prompt=prompt,
            temperature=0.5,
            max_tokens=2048,
            system_prompt=system_prompt,
        )

        # 清理响应
        config_content = self._clean_llm_response(response)

        return CICDConfigResult(
            config=config_content,
            explanation=f"根据您的需求为 {requirements.project_type} 项目生成的配置。"
            f"\n\n构建系统: {requirements.build_system or '自动检测'}"
            f"\n测试框架: {requirements.test_framework or '未指定'}",
            parsed_requirements=requirements.to_dict(),
            stages=requirements.stages,
            template_used=None,
            optimization_applied=[],
            warnings=[
                "此配置由 AI 生成，建议在使用前进行测试和验证"
            ],
            estimated_time_saved=None,
        )

    def _clean_llm_response(self, response: str) -> str:
        """清理 LLM 响应，提取 YAML 内容.

        Args:
            response: LLM 返回的文本

        Returns:
            清理后的 YAML 内容
        """
        response = response.strip()

        # 移除可能的 markdown 代码块标记
        if response.startswith("```yaml"):
            response = response[7:]
        elif response.startswith("```yml"):
            response = response[6:]
        elif response.startswith("```"):
            response = response[3:]

        if response.endswith("```"):
            response = response[:-3]

        return response.strip()

    def _add_deployment_stage(self, config: str, targets: list[str]) -> str:
        """添加部署 stage.

        Args:
            config: 当前配置
            targets: 部署目标列表

        Returns:
            添加了 deploy stage 的配置
        """
        # 在 stages 中添加 deploy
        if "stages:" in config:
            config = config.replace("stages:", "stages:\n  - deploy")

        # 添加 deploy job
        deploy_job = "\n\ndeploy:\n  stage: deploy\n  script:\n"
        for target in targets:
            deploy_job += f'    - echo "Deploying to {target}"\n'
        deploy_job += "  only:\n    - main\n"

        return config + deploy_job

    def _generate_explanation(
        self, template: Template, requirements: ParsedRequirements
    ) -> str:
        """生成配置说明.

        Args:
            template: 使用的模板
            requirements: 需求对象

        Returns:
            配置说明文本
        """
        explanation = f"""使用模板: {template.name}

{template.description}

**配置特点**:
"""
        if "ccache" in template.default_optimizations:
            explanation += "\n- ✅ 启用 ccache 加速编译（减少 30-50% 构建时间）"

        if "parallel_build" in template.default_optimizations:
            explanation += "\n- ✅ 并行构建（使用所有 CPU 核心）"

        if "artifacts_cache" in template.default_optimizations:
            explanation += "\n- ✅ 构建产物缓存（减少重复下载）"

        if requirements.deployment_targets:
            explanation += f"\n- ✅ 部署到: {', '.join(requirements.deployment_targets)}"

        return explanation
