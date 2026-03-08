"""
C++ 代码审查 Agent（集成静态分析和 AI 审查）
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from src.core.analyzers.cpp import CppAnalysisResult, get_cpp_parser
from src.core.llm.factory import get_llm_client, LLMClient
from src.core.quality.cpp import (
    CppCodeQualityScore,
    ClangTidyChecker,
    CppcheckChecker,
    StaticAnalysisResult,
    get_clang_tidy_checker,
    get_cppcheck_checker,
)
from src.utils.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CppIssueSeverity(str, Enum):
    """C++ 问题严重性"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class CppRiskLevel(str, Enum):
    """C++ 风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CppCodeReviewResult:
    """C++ 代码审查结果"""
    project_id: int
    mr_iid: int
    file_path: str

    # 静态分析结果
    static_analysis: Optional[StaticAnalysisResult] = None

    # 评分
    quality_score: Optional[CppCodeQualityScore] = None
    overall_score: float = 0.0
    risk_level: CppRiskLevel = CppRiskLevel.LOW

    # AI 审查
    ai_review: str = ""

    # 问题汇总
    critical_issues: List[str] = field(default_factory=list)
    high_priority_issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # 元数据
    status: str = "pending"  # pending, in_progress, completed, failed
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)

    def calculate_risk_level(self) -> CppRiskLevel:
        """计算风险等级"""
        if not self.static_analysis:
            return CppRiskLevel.LOW

        crit = self.static_analysis.critical_count
        high = self.static_analysis.error_count
        medium = self.static_analysis.warning_count

        if crit > 0 or high >= 5:
            return CppRiskLevel.CRITICAL
        elif high >= 2 or medium >= 10:
            return CppRiskLevel.HIGH
        elif medium >= 5:
            return CppRiskLevel.MEDIUM
        else:
            return CppRiskLevel.LOW

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "project_id": self.project_id,
            "mr_iid": self.mr_iid,
            "file_path": self.file_path,
            "overall_score": round(self.overall_score, 2),
            "risk_level": self.risk_level.value,
            "static_analysis": self.static_analysis.to_dict() if self.static_analysis else None,
            "quality_score": self.quality_score.to_dict() if self.quality_score else None,
            "ai_review": self.ai_review[:1000] if self.ai_review else "",  # 限制长度
            "critical_issues_count": len(self.critical_issues),
            "high_priority_issues_count": len(self.high_priority_issues),
            "recommendations_count": len(self.recommendations),
            "status": self.status,
            "errors": self.errors,
        }


class CppCodeReviewerAgent:
    """C++ 代码审查代理"""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        clang_tidy_checker: Optional[ClangTidyChecker] = None,
        cppcheck_checker: Optional[CppcheckChecker] = None,
        cpp_parser=None,
    ):
        """
        初始化 C++ 代码审查代理

        Args:
            llm_client: LLM 客户端
            clang_tidy_checker: Clang-tidy 检查器
            cppcheck_checker: Cppcheck 检查器
            cpp_parser: C++ 解析器
        """
        self.llm_client = llm_client
        self.clang_tidy_checker = clang_tidy_checker
        self.cppcheck_checker = cppcheck_checker
        self.cpp_parser = cpp_parser

        # 加载 Prompt 模板
        self.prompt_template = self._load_prompt_template()

        logger.info(
            "cpp_code_reviewer_initialized",
            has_llm=llm_client is not None,
            has_clang_tidy=clang_tidy_checker is not None,
            has_cppcheck=cppcheck_checker is not None,
            has_parser=cpp_parser is not None,
        )

    def _load_prompt_template(self) -> str:
        """加载 Prompt 模板"""
        template_path = settings.prompts_dir / "code_review" / "cpp_review.txt"

        if template_path.exists():
            logger.debug("loading_cpp_review_prompt_template", path=str(template_path))
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()

        # 默认模板
        return """Review the following C++ code and provide feedback.

```diff
{diff}
```

Static analysis results:
{static_issues}

Provide professional feedback on code quality, memory safety, performance, and modern C++ practices."""

    async def review_cpp_file(
        self,
        project_id: int,
        mr_iid: int,
        file_path: str,
        diff: str,
        source_code: Optional[str] = None,
        compile_commands_dir: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> CppCodeReviewResult:
        """
        审查 C++ 文件

        Args:
            project_id: 项目 ID
            mr_iid: MR IID
            file_path: 文件路径
            diff: Git diff
            source_code: 源代码（可选）
            compile_commands_dir: compile_commands.json 目录
            options: 审查选项

        Returns:
            CppCodeReviewResult: 审查结果
        """
        start_time = datetime.now()
        options = options or {}

        logger.info(
            "cpp_code_review_started",
            project_id=project_id,
            mr_iid=mr_iid,
            file_path=file_path,
        )

        result = CppCodeReviewResult(
            project_id=project_id,
            mr_iid=mr_iid,
            file_path=file_path,
            status="in_progress",
        )

        try:
            # 1. 解析 C++ 代码
            if self.cpp_parser:
                analysis = self.cpp_parser.parse_file(file_path)
                logger.info(
                    "cpp_code_parsed",
                    file_path=file_path,
                    classes_count=len(analysis.classes),
                )
            else:
                analysis = None

            # 2. 运行静态分析
            static_analysis = await self._run_static_analysis(
                file_path,
                source_code,
                compile_commands_dir,
            )
            result.static_analysis = static_analysis

            # 3. 计算质量分数
            if static_analysis:
                result.quality_score = self._calculate_quality_score(static_analysis)
                result.overall_score = result.quality_score.overall_score

            # 4. 运行 AI 审查（如果配置了 LLM）
            if self.llm_client:
                ai_review = await self._run_ai_review(diff, static_analysis)
                result.ai_review = ai_review

            # 5. 计算风险等级
            result.risk_level = result.calculate_risk_level()

            # 6. 生成问题汇总和建议
            if static_analysis:
                result.critical_issues = self._extract_critical_issues(static_analysis)
                result.high_priority_issues = self._extract_high_priority_issues(static_analysis)
                result.recommendations = self._generate_recommendations(static_analysis)

            result.status = "completed"
            result.completed_at = datetime.now()

            logger.info(
                "cpp_code_review_completed",
                project_id=project_id,
                mr_iid=mr_iid,
                file_path=file_path,
                overall_score=result.overall_score,
                risk_level=result.risk_level.value,
                duration_seconds=(result.completed_at - start_time).total_seconds(),
            )

            return result

        except Exception as e:
            logger.error(
                "cpp_code_review_failed",
                project_id=project_id,
                mr_iid=mr_iid,
                file_path=file_path,
                error=str(e),
                exc_info=True,
            )
            result.status = "failed"
            result.errors.append(str(e))
            return result

    async def _run_static_analysis(
        self,
        file_path: str,
        source_code: Optional[str],
        compile_commands_dir: Optional[str],
    ) -> Optional[StaticAnalysisResult]:
        """运行静态分析"""
        result = StaticAnalysisResult(file_path=file_path)

        # 运行 Clang-tidy
        if self.clang_tidy_checker and self.clang_tidy_checker.available:
            try:
                tidy_result = self.clang_tidy_checker.check_file(
                    file_path=file_path,
                    compile_commands_dir=compile_commands_dir,
                    source_code=source_code,
                )
                result.issues.extend(tidy_result.issues)
                result.clang_tidy_issues = tidy_result.clang_tidy_issues
            except Exception as e:
                logger.warning("clang_tidy_failed", error=str(e))

        # 运行 Cppcheck
        if self.cppcheck_checker and self.cppcheck_checker.available:
            try:
                cppcheck_result = self.cppcheck_checker.check_file(
                    file_path=file_path,
                    source_code=source_code,
                )
                result.issues.extend(cppcheck_result.issues)
                result.cppcheck_issues = cppcheck_result.cppcheck_issues
            except Exception as e:
                logger.warning("cppcheck_failed", error=str(e))

        # 对问题进行分类
        result.categorize_issues()

        logger.info(
            "static_analysis_completed",
            file_path=file_path,
            total_issues=len(result.issues),
        )

        return result if result.issues else None

    async def _run_ai_review(
        self,
        diff: str,
        static_analysis: Optional[StaticAnalysisResult],
    ) -> str:
        """运行 AI 审查"""
        try:
            # 准备静态分析信息
            clang_issues = ""
            cppcheck_issues = ""

            if static_analysis:
                # Clang-tidy 问题
                if static_analysis.clang_tidy_issues:
                    clang_issues = "### Clang-tidy 检查结果\n"
                    for issue in static_analysis.clang_tidy_issues[:10]:  # 限制显示数量
                        clang_issues += f"- **{issue.severity}** [{issue.rule_id or 'N/A'}] {issue.file}:{issue.line} - {issue.message}\n"

                # Cppcheck 问题
                if static_analysis.cppcheck_issues:
                    cppcheck_issues = "### Cppcheck 检查结果\n"
                    for issue in static_analysis.cppcheck_issues[:10]:
                        cppcheck_issues += f"- **{issue.severity}** [{issue.rule_id or 'N/A'}] {issue.file}:{issue.line} - {issue.message}\n"

            # 构建 Prompt
            prompt = self.prompt_template.format(
                diff=diff[:5000],  # 限制 diff 长度
                clang_tidy_issues=clang_issues,
                cppcheck_issues=cppcheck_issues,
                static_issues=clang_issues + "\n" + cppcheck_issues,
            )

            # 调用 LLM
            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.3,
                system_prompt="你是一个资深的 C++ 代码审查专家，精通现代 C++、软件架构和安全最佳实践。",
            )

            return response

        except Exception as e:
            logger.error("ai_review_failed", error=str(e))
            return ""

    def _calculate_quality_score(self, analysis: StaticAnalysisResult) -> CppCodeQualityScore:
        """计算质量分数"""
        score = CppCodeQualityScore(file_path=analysis.file_path)

        score.total_issues = analysis.total_issues
        score.critical_issues = analysis.critical_count
        score.high_priority_issues = analysis.error_count + analysis.warning_count

        # 计算各维度分数（基于问题数量）
        # 内存安全：每个 critical 扣 10 分
        score.memory_safety_score = max(0, 100 - len(analysis.memory_issues) * 10)
        # 性能：每个 warning 扣 5 分
        score.performance_score = max(0, 100 - len(analysis.performance_issues) * 5)
        # 现代 C++：每个问题扣 2 分
        score.modern_cpp_score = max(0, 100 - len(analysis.modern_cpp_issues) * 2)
        # 线程安全：每个问题扣 8 分
        score.thread_safety_score = max(0, 100 - len(analysis.thread_safety_issues) * 8)
        # 代码风格：每个问题扣 1 分
        score.code_style_score = max(0, 100 - len(analysis.style_issues))

        # 计算总体分数
        score.calculate_overall_score()

        return score

    def _extract_critical_issues(self, analysis: StaticAnalysisResult) -> List[str]:
        """提取严重问题"""
        issues = []

        for issue in analysis.issues:
            if issue.severity in ["critical", "error"]:
                issues.append(f"[{issue.severity}] {issue.file}:{issue.line} - {issue.message}")

        return issues[:10]  # 最多返回 10 个

    def _extract_high_priority_issues(self, analysis: StaticAnalysisResult) -> List[str]:
        """提取高优先级问题"""
        issues = []

        for issue in analysis.issues:
            if issue.severity == "warning":
                issues.append(f"[{issue.category}] {issue.file}:{issue.line} - {issue.message}")

        return issues[:10]

    def _generate_recommendations(self, analysis: StaticAnalysisResult) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于问题类型生成建议
        if analysis.memory_issues:
            recommendations.append("发现内存安全问题，建议使用智能指针（std::unique_ptr, std::shared_ptr）管理动态内存")

        if analysis.modern_cpp_issues:
            recommendations.append("建议使用现代 C++ 特性（auto、nullptr、智能指针、移动语义）提高代码质量")

        if analysis.performance_issues:
            recommendations.append("发现性能问题，建议避免不必要的对象拷贝，使用 const 引用传递大对象")

        if analysis.thread_safety_issues:
            recommendations.append("发现线程安全问题，建议使用互斥锁或原子操作保护共享数据")

        if analysis.critical_count > 0:
            recommendations.append(f"发现 {analysis.critical_count} 个严重问题，需要立即处理")

        if not recommendations:
            recommendations.append("代码质量良好，继续保持！")

        return recommendations


# 全局实例
_cpp_reviewer: Optional[CppCodeReviewerAgent] = None


def get_cpp_reviewer() -> CppCodeReviewerAgent:
    """获取 C++ 代码审查代理实例（单例）"""
    global _cpp_reviewer
    if _cpp_reviewer is None:
        llm_client = get_llm_client() if settings.enable_code_review else None
        clang_tidy = get_clang_tidy_checker()
        cppcheck = get_cppcheck_checker()
        cpp_parser = get_cpp_parser()

        _cpp_reviewer = CppCodeReviewerAgent(
            llm_client=llm_client,
            clang_tidy_checker=clang_tidy,
            cppcheck_checker=cppcheck,
            cpp_parser=cpp_parser,
        )
    return _cpp_reviewer
