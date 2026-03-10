"""
修复建议生成器

使用AI生成修复建议和代码补丁
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re

from ....utils.logger import get_logger
from .llm_service import LLMService
from .root_cause_analyzer import RootCause, RootCauseType
from .failure_classifier import FailureType, ClassificationResult

logger = get_logger(__name__)


class FixComplexity(str, Enum):
    """修复复杂度"""
    TRIVIAL = "trivial"  # 5分钟内
    SIMPLE = "simple"  # 30分钟内
    MODERATE = "moderate"  # 2小时内
    COMPLEX = "complex"  # 1天内
    VERY_COMPLEX = "very_complex"  # 需要多天或需要架构讨论


class FixType(str, Enum):
    """修复类型"""
    CODE_CHANGE = "code_change"  # 代码修改
    CONFIG_CHANGE = "config_change"  # 配置修改
    DEPENDENCY_UPDATE = "dependency_update"  # 依赖更新
    FILE_ADDITION = "file_addition"  # 添加文件
    FILE_DELETION = "file_deletion"  # 删除文件
    ENVIRONMENT_SETUP = "environment_setup"  # 环境设置
    REFACTORING = "refactoring"  # 代码重构
    DOCUMENTATION = "documentation"  # 文档更新


@dataclass
class CodeChange:
    """代码变更"""
    file_path: str
    old_code: str
    new_code: str
    line_start: int
    line_end: int
    description: str = ""


@dataclass
class FixSuggestion:
    """修复建议"""
    suggestion_id: str
    fix_type: FixType
    complexity: FixComplexity

    # 描述
    title: str
    description: str
    rationale: str  # 为什么这样修复

    # 具体操作
    code_changes: List[CodeChange] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)  # 要执行的命令
    config_changes: Dict[str, str] = field(default_factory=dict)

    # 风险评估
    risk_level: str = "low"  # low, medium, high
    side_effects: List[str] = field(default_factory=list)

    # 验证
    verification_steps: List[str] = field(default_factory=list)
    expected_outcome: str = ""

    # 元数据
    confidence: float = 0.0  # 0-1
    estimated_time: str = ""
    auto_applicable: bool = False  # 是否可以自动应用
    generated_at: datetime = field(default_factory=datetime.now)


class FixGenerator:
    """
    修复建议生成器

    使用AI生成针对性的修复建议
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()

    async def generate_fix(
        self,
        root_cause: RootCause,
        classification: Optional[ClassificationResult] = None,
        context: Optional[Dict] = None,
        use_ai: bool = True,
    ) -> List[FixSuggestion]:
        """
        生成修复建议

        Args:
            root_cause: 根因分析结果
            classification: 失败分类结果
            context: 额外上下文信息
            use_ai: 是否使用AI

        Returns:
            修复建议列表
        """
        logger.info(
            "fix_generation_started",
            root_cause_type=root_cause.root_cause_type.value,
            use_ai=use_ai,
        )

        # 尝试AI生成
        if use_ai and self.llm_service.is_available():
            try:
                suggestions = await self._generate_with_ai(
                    root_cause, classification, context
                )
                if suggestions:
                    logger.info(
                        "fix_generation_ai_success",
                        count=len(suggestions),
                    )
                    return suggestions
            except Exception as e:
                logger.warning(
                    "ai_fix_generation_failed",
                    error=str(e),
                    falling_back_to_rules=True,
                )

        # 回退到基于规则的生成
        logger.info("using_rule_based_fix_generation")
        return self._generate_with_rules(root_cause, classification, context)

    async def _generate_with_ai(
        self,
        root_cause: RootCause,
        classification: Optional[ClassificationResult],
        context: Optional[Dict],
    ) -> List[FixSuggestion]:
        """使用AI生成修复建议"""
        prompt = self._build_fix_prompt(root_cause, classification, context)

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.4,
            )

            if not response:
                return []

            return self._parse_ai_fix_response(response, root_cause)

        except Exception as e:
            logger.error(
                "ai_fix_generation_error",
                error=str(e),
                exc_info=True,
            )
            return []

    def _build_fix_prompt(
        self,
        root_cause: RootCause,
        classification: Optional[ClassificationResult],
        context: Optional[Dict],
    ) -> str:
        """构建AI修复提示"""
        prompt = """你是一个CI/CD问题修复专家。请根据根因分析，提供具体的修复建议。

# 根因分析
- 类型: {root_cause_type}
- 置信度: {confidence:.2f}
- 标题: {title}
- 描述: {description}
""".format(
            root_cause_type=root_cause.root_cause_type.value,
            confidence=root_cause.confidence,
            title=root_cause.title,
            description=root_cause.description,
        )

        if root_cause.responsible_files:
            prompt += f"- 相关文件:\n"
            for f in root_cause.responsible_files:
                prompt += f"  - {f}\n"

        if root_cause.evidence:
            prompt += f"- 证据:\n"
            for e in root_cause.evidence[:3]:
                prompt += f"  - {e}\n"

        if classification and classification.error_location:
            prompt += f"\n# 错误位置\n{classification.error_location}\n"

        if classification and classification.error_message:
            prompt += f"\n# 错误消息\n{classification.error_message}\n"

        prompt += """
# 修复要求
请提供1-3个修复建议，每个建议包含：

1. 修复类型: 从以下选择
   - code_change: 代码修改
   - config_change: 配置修改
   - dependency_update: 依赖更新
   - file_addition: 添加文件
   - file_deletion: 删除文件
   - environment_setup: 环境设置
   - refactoring: 代码重构
   - documentation: 文档更新

2. 复杂度: trivial, simple, moderate, complex, very_complex

3. 标题: 一句话描述修复

4. 描述: 详细说明修复步骤

5. 理由: 为什么这样修复

6. 代码变更: 如果需要修改代码，提供具体的修改内容
   - file_path: 文件路径
   - old_code: 原代码
   - new_code: 新代码
   - description: 修改说明

7. 命令: 如果需要执行命令，列出命令

8. 风险等级: low, medium, high

9. 副作用: 可能的影响

10. 验证步骤: 如何验证修复有效

11. 预期结果: 修复后应该看到什么

12. 预估时间: 如"5分钟"、"1小时"

13. 是否可自动应用: true/false

请用JSON格式返回，格式如下：
```json
{
  "suggestions": [
    {
      "fix_type": "...",
      "complexity": "...",
      "title": "...",
      "description": "...",
      "rationale": "...",
      "code_changes": [
        {
          "file_path": "...",
          "old_code": "...",
          "new_code": "...",
          "description": "..."
        }
      ],
      "commands": ["cmd1", "cmd2"],
      "risk_level": "...",
      "side_effects": ["..."],
      "verification_steps": ["..."],
      "expected_outcome": "...",
      "estimated_time": "...",
      "auto_applicable": false
    }
  ]
}
```
"""

        return prompt

    def _parse_ai_fix_response(
        self,
        response: str,
        root_cause: RootCause,
    ) -> List[FixSuggestion]:
        """解析AI修复响应"""
        try:
            # 提取JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response.strip()

            import json
            data = json.loads(json_str)

            suggestions = []
            for i, sug_data in enumerate(data.get("suggestions", [])):
                suggestion = FixSuggestion(
                    suggestion_id=f"fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}",
                    fix_type=FixType(sug_data.get("fix_type", "code_change")),
                    complexity=FixComplexity(sug_data.get("complexity", "moderate")),
                    title=sug_data.get("title", "修复建议"),
                    description=sug_data.get("description", ""),
                    rationale=sug_data.get("rationale", ""),
                    commands=sug_data.get("commands", []),
                    risk_level=sug_data.get("risk_level", "medium"),
                    side_effects=sug_data.get("side_effects", []),
                    verification_steps=sug_data.get("verification_steps", []),
                    expected_outcome=sug_data.get("expected_outcome", ""),
                    estimated_time=sug_data.get("estimated_time", "未知"),
                    auto_applicable=sug_data.get("auto_applicable", False),
                    confidence=0.8,
                )

                # 解析代码变更
                for change_data in sug_data.get("code_changes", []):
                    code_change = CodeChange(
                        file_path=change_data.get("file_path", ""),
                        old_code=change_data.get("old_code", ""),
                        new_code=change_data.get("new_code", ""),
                        line_start=0,
                        line_end=0,
                        description=change_data.get("description", ""),
                    )
                    suggestion.code_changes.append(code_change)

                suggestions.append(suggestion)

            return suggestions

        except Exception as e:
            logger.warning(
                "ai_fix_response_parse_failed",
                error=str(e),
                response=response[:500],
            )
            return []

    def _generate_with_rules(
        self,
        root_cause: RootCause,
        classification: Optional[ClassificationResult],
        context: Optional[Dict],
    ) -> List[FixSuggestion]:
        """使用基于规则的修复生成"""
        suggestions = []

        # 根据根因类型生成建议
        if root_cause.root_cause_type == RootCauseType.DEPENDENCY_ISSUE:
            suggestions.append(FixSuggestion(
                suggestion_id=f"dep_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                fix_type=FixType.DEPENDENCY_UPDATE,
                complexity=FixComplexity.SIMPLE,
                title="更新依赖库配置",
                description="检查并更新CMakeLists.txt或.pro文件中的依赖库链接",
                rationale="链接错误通常是由于缺少依赖或库版本不匹配",
                commands=[
                    "检查CMakeLists.txt中的target_link_libraries",
                    "确认所有依赖库都已安装",
                    "更新库路径配置",
                ],
                risk_level="low",
                verification_steps=[
                    "清理构建目录",
                    "重新配置CMake",
                    "重新构建",
                ],
                expected_outcome="链接错误消失，构建成功",
                estimated_time="30分钟",
                auto_applicable=False,
                confidence=0.6,
            ))

        elif root_cause.root_cause_type == RootCauseType.CONFIGURATION_ISSUE:
            suggestions.append(FixSuggestion(
                suggestion_id=f"config_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                fix_type=FixType.CONFIG_CHANGE,
                complexity=FixComplexity.SIMPLE,
                title="修复配置错误",
                description="检查并修正构建配置文件",
                rationale="配置错误导致构建或测试失败",
                commands=[
                    "检查构建配置文件",
                    "验证环境变量",
                    "检查路径配置",
                ],
                risk_level="low",
                verification_steps=[
                    "重新运行配置",
                    "检查配置输出",
                ],
                expected_outcome="配置成功，后续步骤正常",
                estimated_time="15分钟",
                auto_applicable=False,
                confidence=0.7,
            ))

        elif root_cause.root_cause_type == RootCauseType.CODE_DEFECT:
            suggestions.append(FixSuggestion(
                suggestion_id=f"code_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                fix_type=FixType.CODE_CHANGE,
                complexity=FixComplexity.MODERATE,
                title="修复代码缺陷",
                description=f"检查并修复 {root_cause.responsible_files[0] if root_cause.responsible_files else '相关文件'} 中的代码问题",
                rationale=root_cause.description,
                risk_level="medium",
                verification_steps=[
                    "代码审查",
                    "运行单元测试",
                    "运行集成测试",
                ],
                expected_outcome="测试通过，代码逻辑正确",
                estimated_time="2小时",
                auto_applicable=False,
                confidence=0.5,
            ))

        # 如果没有生成任何建议，提供通用建议
        if not suggestions:
            suggestions.append(FixSuggestion(
                suggestion_id=f"generic_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                fix_type=FixType.CODE_CHANGE,
                complexity=FixComplexity.MODERATE,
                title="手动分析和修复",
                description="根据错误日志和根因分析，手动修复问题",
                rationale=root_cause.description,
                commands=[
                    "查看完整错误日志",
                    "检查相关代码",
                    "咨询开发团队",
                ],
                risk_level="medium",
                verification_steps=[
                    "应用修复",
                    "重新运行流水线",
                    "验证结果",
                ],
                expected_outcome="问题解决",
                estimated_time="未知",
                auto_applicable=False,
                confidence=0.3,
            ))

        return suggestions

    def rank_suggestions(
        self,
        suggestions: List[FixSuggestion],
        prioritize_auto_applicable: bool = True,
    ) -> List[FixSuggestion]:
        """
        排序修复建议

        Args:
            suggestions: 修复建议列表
            prioritize_auto_applicable: 是否优先考虑可自动应用的

        Returns:
            排序后的建议列表
        """
        def score(suggestion: FixSuggestion) -> float:
            score = suggestion.confidence * 100

            # 复杂度惩罚
            complexity_penalty = {
                FixComplexity.TRIVIAL: 0,
                FixComplexity.SIMPLE: -10,
                FixComplexity.MODERATE: -20,
                FixComplexity.COMPLEX: -30,
                FixComplexity.VERY_COMPLEX: -40,
            }
            score += complexity_penalty.get(suggestion.complexity, -20)

            # 风险惩罚
            risk_penalty = {
                "low": 0,
                "medium": -15,
                "high": -30,
            }
            score += risk_penalty.get(suggestion.risk_level, -15)

            # 自动应用奖励
            if prioritize_auto_applicable and suggestion.auto_applicable:
                score += 25

            return score

        return sorted(suggestions, key=score, reverse=True)


# 全局单例
fix_generator = FixGenerator()
