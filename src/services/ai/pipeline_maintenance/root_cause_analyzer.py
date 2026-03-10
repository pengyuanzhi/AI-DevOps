"""
根因分析引擎

使用AI分析流水线失败的根因
"""

import re
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ....utils.logger import get_logger
from .llm_service import LLMService
from .failure_classifier import ClassificationResult, FailureType
from .change_correlator import ChangeCorrelationResult

logger = get_logger(__name__)


class RootCauseType(str, Enum):
    """根因类型"""
    CODE_DEFECT = "code_defect"  # 代码缺陷
    CONFIGURATION_ISSUE = "configuration_issue"  # 配置问题
    ENVIRONMENT_ISSUE = "environment_issue"  # 环境问题
    DEPENDENCY_ISSUE = "dependency_issue"  # 依赖问题
    TEST_ISSUE = "test_issue"  # 测试问题
    INFRASTRUCTURE_ISSUE = "infrastructure_issue"  # 基础设施问题
    DATA_ISSUE = "data_issue"  # 数据问题
    UNKNOWN = "unknown"


@dataclass
class RootCause:
    """根因分析结果"""
    root_cause_type: RootCauseType
    confidence: float  # 0-1

    # 描述
    title: str
    description: str
    detailed_explanation: str = ""

    # 关联信息
    responsible_files: List[str] = field(default_factory=list)
    responsible_commits: List[str] = field(default_factory=list)
    responsible_components: List[str] = field(default_factory=list)

    # 证据
    evidence: List[str] = field(default_factory=list)
    error_traces: List[str] = field(default_factory=list)

    # 修复建议
    suggested_fixes: List[str] = field(default_factory=list)
    estimated_fix_time: Optional[str] = None  # "5分钟", "1小时", "1天"等

    # 元数据
    analysis_method: str = "ai"  # "ai", "rule_based", "hybrid"
    analyzed_at: datetime = field(default_factory=datetime.now)


@dataclass
class AnalysisContext:
    """分析上下文"""
    # 失败信息
    failure_log: str
    failure_type: FailureType
    error_location: Optional[str] = None

    # 代码变更
    changed_files: List[str] = field(default_factory=list)
    changed_commits: List[str] = field(default_factory=list)
    diff_summary: str = ""

    # 项目信息
    project_id: int = 0
    pipeline_id: str = ""
    job_id: str = ""

    # 历史信息
    similar_failures: List[Dict] = field(default_factory=list)
    recent_failures: List[Dict] = field(default_factory=list)


class RootCauseAnalyzer:
    """
    根因分析器

    使用LLM和规则分析失败的根因
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()
        self._initialize_rules()

    def _initialize_rules(self):
        """初始化基于规则的分析"""
        # 备用规则，当LLM不可用时使用
        self.rules = {
            # 编译错误规则
            FailureType.COMPILATION_ERROR: [
                {
                    "pattern": r"undefined reference",
                    "root_cause": RootCauseType.DEPENDENCY_ISSUE,
                    "suggestion": "链接时找不到符号，可能需要添加依赖库或检查链接配置",
                },
                {
                    "pattern": r"No such file or directory",
                    "root_cause": RootCauseType.CONFIGURATION_ISSUE,
                    "suggestion": "文件路径配置错误，检查include路径或源文件路径",
                },
            ],
            # 测试失败规则
            FailureType.TEST_FAILURE: [
                {
                    "pattern": r"Assertion.*failed",
                    "root_cause": RootCauseType.CODE_DEFECT,
                    "suggestion": "测试断言失败，代码逻辑可能存在问题",
                },
            ],
        }

    async def analyze(
        self,
        context: AnalysisContext,
        classification: Optional[ClassificationResult] = None,
        use_ai: bool = True,
    ) -> RootCause:
        """
        分析根因

        Args:
            context: 分析上下文
            classification: 失败分类结果
            use_ai: 是否使用AI分析

        Returns:
            根因分析结果
        """
        logger.info(
            "root_cause_analysis_started",
            project_id=context.project_id,
            pipeline_id=context.pipeline_id,
            job_id=context.job_id,
            use_ai=use_ai,
        )

        # 尝试AI分析
        if use_ai and self.llm_service.is_available():
            try:
                root_cause = await self._analyze_with_ai(context, classification)
                if root_cause and root_cause.confidence > 0.5:
                    logger.info(
                        "root_cause_analysis_ai_success",
                        confidence=root_cause.confidence,
                    )
                    return root_cause
            except Exception as e:
                logger.warning(
                    "ai_analysis_failed",
                    error=str(e),
                    falling_back_to_rules=True,
                )

        # 回退到基于规则的分析
        logger.info("using_rule_based_analysis")
        return self._analyze_with_rules(context, classification)

    async def _analyze_with_ai(
        self,
        context: AnalysisContext,
        classification: Optional[ClassificationResult],
    ) -> Optional[RootCause]:
        """使用AI分析根因"""
        # 构建分析提示
        prompt = self._build_analysis_prompt(context, classification)

        try:
            # 调用LLM
            response = await self.llm_service.generate(
                prompt=prompt,
                max_tokens=1500,
                temperature=0.3,  # 较低温度以获得更确定的结果
            )

            if not response:
                return None

            # 解析响应
            return self._parse_ai_response(response, context)

        except Exception as e:
            logger.error(
                "ai_analysis_error",
                error=str(e),
                exc_info=True,
            )
            return None

    def _build_analysis_prompt(
        self,
        context: AnalysisContext,
        classification: Optional[ClassificationResult],
    ) -> str:
        """构建AI分析提示"""
        prompt = """你是一个CI/CD流水线根因分析专家。请分析以下流水线失败，找出根本原因。

# 失败信息
"""

        # 添加失败日志
        if context.failure_log:
            # 限制日志长度
            log_snippet = context.failure_log[:2000]
            if len(context.failure_log) > 2000:
                log_snippet += "\n... (日志已截断)"
            prompt += f"```\n{log_snippet}\n```\n\n"

        # 添加分类信息
        if classification:
            prompt += f"""# 失败分类
- 类型: {classification.failure_type.value}
- 严重程度: {classification.severity.value}
- 置信度: {classification.confidence:.2f}
"""
            if classification.error_location:
                prompt += f"- 错误位置: {classification.error_location}\n"
            if classification.error_message:
                prompt += f"- 错误消息: {classification.error_message}\n"
            prompt += "\n"

        # 添加代码变更
        if context.changed_files:
            prompt += "# 代码变更\n"
            prompt += f"- 变更文件 ({len(context.changed_files)}个):\n"
            for file in context.changed_files[:20]:  # 限制文件数量
                prompt += f"  - {file}\n"
            if len(context.changed_files) > 20:
                prompt += f"  ... 还有{len(context.changed_files) - 20}个文件\n"
            prompt += "\n"

        if context.diff_summary:
            prompt += f"- 变更摘要:\n{context.diff_summary[:1000]}\n\n"

        # 添加历史信息
        if context.similar_failures:
            prompt += f"# 历史相似失败 ({len(context.similar_failures)}次)\n"
            for failure in context.similar_failures[:5]:
                prompt += f"- {failure.get('timestamp', 'N/A')}: {failure.get('error_message', 'N/A')[:100]}\n"
            prompt += "\n"

        prompt += """# 分析要求
请提供以下格式的分析结果：

1. 根因类型: 从以下选项选择一个
   - code_defect: 代码缺陷
   - configuration_issue: 配置问题
   - environment_issue: 环境问题
   - dependency_issue: 依赖问题
   - test_issue: 测试问题
   - infrastructure_issue: 基础设施问题
   - data_issue: 数据问题
   - unknown: 未知

2. 置信度: 0.0-1.0之间的数字

3. 标题: 一句话总结根因

4. 描述: 详细说明为什么这是根因

5. 负责的文件/组件: 列出导致问题的文件或组件

6. 证据: 从日志中找出支持你分析的证据

7. 修复建议: 提供2-3条具体的修复建议

8. 预估修复时间: 如"5分钟"、"1小时"、"1天"

请用JSON格式返回：
```json
{
  "root_cause_type": "...",
  "confidence": 0.0-1.0,
  "title": "...",
  "description": "...",
  "responsible_files": ["file1", "file2"],
  "evidence": ["evidence1", "evidence2"],
  "suggested_fixes": ["fix1", "fix2"],
  "estimated_fix_time": "..."
}
```
"""

        return prompt

    def _parse_ai_response(
        self,
        response: str,
        context: AnalysisContext,
    ) -> Optional[RootCause]:
        """解析AI响应"""
        try:
            # 尝试提取JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 如果没有代码块，尝试直接解析
                json_str = response.strip()

            import json
            data = json.loads(json_str)

            # 映射类型
            root_cause_type = RootCauseType.CODE_DEFECT
            if "root_cause_type" in data:
                try:
                    root_cause_type = RootCauseType(data["root_cause_type"])
                except ValueError:
                    root_cause_type = RootCauseType.UNKNOWN

            return RootCause(
                root_cause_type=root_cause_type,
                confidence=float(data.get("confidence", 0.5)),
                title=data.get("title", "未知根因"),
                description=data.get("description", ""),
                detailed_explanation=response,
                responsible_files=data.get("responsible_files", []),
                responsible_commits=context.changed_commits,
                evidence=data.get("evidence", []),
                suggested_fixes=data.get("suggested_fixes", []),
                estimated_fix_time=data.get("estimated_fix_time"),
                analysis_method="ai",
            )

        except Exception as e:
            logger.warning(
                "ai_response_parse_failed",
                error=str(e),
                response=response[:500],
            )
            return None

    def _analyze_with_rules(
        self,
        context: AnalysisContext,
        classification: Optional[ClassificationResult],
    ) -> RootCause:
        """使用基于规则的分析"""
        if classification:
            failure_type = classification.failure_type
        else:
            failure_type = FailureType.UNKNOWN

        # 查找匹配的规则
        rules = self.rules.get(failure_type, [])

        for rule in rules:
            pattern = rule["pattern"]
            if re.search(pattern, context.failure_log, re.IGNORECASE):
                return RootCause(
                    root_cause_type=rule["root_cause"],
                    confidence=0.7,
                    title=rule["root_cause"].value.replace("_", " ").title(),
                    description=rule["suggestion"],
                    responsible_files=context.changed_files[:5],
                    evidence=[classification.error_message] if classification and classification.error_message else [],
                    suggested_fixes=[rule["suggestion"]],
                    analysis_method="rule_based",
                )

        # 默认分析
        return RootCause(
            root_cause_type=RootCauseType.UNKNOWN,
            confidence=0.3,
            title="无法确定根因",
            description="基于规则的分析无法确定明确的根因",
            responsible_files=context.changed_files[:5],
            suggested_fixes=["检查完整日志", "联系开发团队", "手动分析"],
            analysis_method="rule_based",
        )

    def batch_analyze(
        self,
        contexts: List[AnalysisContext],
        classifications: Optional[List[ClassificationResult]] = None,
    ) -> List[RootCause]:
        """批量分析根因"""
        results = []

        for i, context in enumerate(contexts):
            classification = classifications[i] if classifications else None
            # 注意：这里使用同步方式，批量处理时应该用异步
            # 为简化，这里使用规则分析
            result = self._analyze_with_rules(context, classification)
            results.append(result)

        return results


# 全局单例
root_cause_analyzer = RootCauseAnalyzer()
