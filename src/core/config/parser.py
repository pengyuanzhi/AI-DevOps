"""自然语言需求解析器."""

import json
from pathlib import Path
from typing import Optional

from src.models.cicd import ParsedRequirements
from src.utils.logger import get_logger

logger = get_logger(__name__)


class NaturalLanguageParser:
    """自然语言需求解析器.

    使用 LLM 解析用户的自然语言输入，提取结构化的 CI/CD 需求信息。
    """

    def __init__(self, llm_client):
        """初始化解析器.

        Args:
            llm_client: LLM 客户端实例
        """
        self.llm = llm_client
        self.analysis_prompt_template = self._load_prompt_template(
            "prompts/cicd_config/analysis.txt"
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
                # 返回默认模板
                return self._get_default_analysis_prompt()
        except Exception as e:
            logger.error(
                "load_prompt_template_failed",
                template_path=template_path,
                error=str(e),
            )
            return self._get_default_analysis_prompt()

    def _get_default_analysis_prompt(self) -> str:
        """获取默认的分析提示词."""
        return """你是一个CI/CD需求分析专家。

## 任务
分析用户的自然语言描述，提取CI/CD配置需求信息。

## 用户输入
{user_input}

## 分析要求
请识别并提取以下信息：
1. 项目类型 (project_type): cpp, qt, python, nodejs, go, rust, java, etc.
2. 构建系统 (build_system): cmake, make, qmake, npm, maven, gradle, cargo, etc.
3. 测试框架 (test_framework): gtest, catch2, pytest, jest, junit, etc.
4. 需要的stages: build, test, deploy, package, etc.
5. 特殊需求（ccache、并行构建、Docker等）

## 输出格式
请以JSON格式输出分析结果，只输出JSON，不要包含其他解释文字。

```json
{{
  "project_type": "cpp",
  "build_system": "cmake",
  "test_framework": "gtest",
  "stages": ["build", "test"],
  "needs_ccache": true,
  "needs_parallel": true,
  "deployment_targets": [],
  "special_requirements": []
}}
```"""

    async def parse_requirements(
        self,
        user_input: str,
        project_context: Optional[dict] = None,
    ) -> ParsedRequirements:
        """解析用户输入，提取 CI/CD 需求.

        Args:
            user_input: 用户的自然语言描述
            project_context: 可选的项目上下文信息

        Returns:
            解析后的需求对象

        示例:
            >>> parser = NaturalLanguageParser(llm_client)
            >>> result = await parser.parse_requirements(
            ...     "我有一个C++项目，使用CMake构建，需要运行Google Test测试"
            ... )
            >>> print(result.project_type)
            'cpp'
            >>> print(result.build_system)
            'cmake'
        """
        logger.info(
            "parse_requirements_start",
            input_length=len(user_input),
        )

        try:
            # 构建 Prompt
            prompt = self.analysis_prompt_template.format(user_input=user_input)

            # 调用 LLM
            system_prompt = "你是一个专业的CI/CD配置专家，擅长分析需求并生成JSON格式的分析结果。"
            response = await self.llm.generate(
                prompt=prompt,
                temperature=0.3,  # 使用较低温度以获得更稳定的结构化输出
                max_tokens=1024,
                system_prompt=system_prompt,
            )

            # 解析 JSON 响应
            parsed_data = self._extract_json(response)

            # 如果项目上下文可用，合并信息
            if project_context:
                parsed_data = self._merge_with_context(parsed_data, project_context)

            # 创建 ParsedRequirements 对象
            requirements = ParsedRequirements(
                project_type=parsed_data.get("project_type", "cpp"),
                build_system=parsed_data.get("build_system"),
                test_framework=parsed_data.get("test_framework"),
                stages=parsed_data.get("stages", ["build", "test"]),
                needs_ccache=parsed_data.get("needs_ccache", False),
                needs_parallel=parsed_data.get("needs_parallel", False),
                deployment_targets=parsed_data.get("deployment_targets", []),
                special_requirements=parsed_data.get("special_requirements", []),
            )

            logger.info(
                "parse_requirements_success",
                project_type=requirements.project_type,
                build_system=requirements.build_system,
                stages=requirements.stages,
            )

            return requirements

        except Exception as e:
            logger.error(
                "parse_requirements_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            # 返回默认配置
            return self._get_default_requirements(user_input)

    def _extract_json(self, response: str) -> dict:
        """从 LLM 响应中提取 JSON.

        Args:
            response: LLM 返回的文本

        Returns:
            解析后的字典
        """
        # 清理响应文本
        response = response.strip()

        # 移除可能的 markdown 代码块标记
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]

        if response.endswith("```"):
            response = response[:-3]

        response = response.strip()

        # 解析 JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取 JSON 对象
            start_idx = response.find("{")
            end_idx = response.rfind("}")

            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx : end_idx + 1]
                return json.loads(json_str)
            else:
                logger.error("json_parse_failed", response=response[:200])
                raise ValueError(f"无法从响应中提取有效的JSON: {response[:200]}")

    def _merge_with_context(self, parsed_data: dict, context: dict) -> dict:
        """将解析结果与项目上下文合并.

        Args:
            parsed_data: LLM 解析的数据
            context: 项目上下文信息

        Returns:
            合并后的数据
        """
        # 如果项目上下文提供了更准确的信息，使用上下文数据
        if context.get("project_type") and not parsed_data.get("project_type"):
            parsed_data["project_type"] = context["project_type"]

        if context.get("build_system") and not parsed_data.get("build_system"):
            parsed_data["build_system"] = context["build_system"]

        if context.get("test_framework") and not parsed_data.get("test_framework"):
            parsed_data["test_framework"] = context["test_framework"]

        return parsed_data

    def _get_default_requirements(self, user_input: str) -> ParsedRequirements:
        """获取默认需求配置.

        Args:
            user_input: 用户输入（用于简单推断）

        Returns:
            默认需求对象
        """
        # 简单的关键词匹配作为后备方案
        user_input_lower = user_input.lower()

        project_type = "cpp"
        if "python" in user_input_lower or "py" in user_input_lower:
            project_type = "python"
        elif "node" in user_input_lower or "npm" in user_input_lower:
            project_type = "nodejs"
        elif "java" in user_input_lower or "maven" in user_input_lower:
            project_type = "java"
        elif "qt" in user_input_lower:
            project_type = "qt"

        build_system = "cmake" if project_type in ["cpp", "qt"] else None
        test_framework = "gtest" if project_type == "cpp" else None

        return ParsedRequirements(
            project_type=project_type,
            build_system=build_system,
            test_framework=test_framework,
            stages=["build", "test"],
            needs_ccache=project_type in ["cpp", "qt"],
            needs_parallel=True,
        )
