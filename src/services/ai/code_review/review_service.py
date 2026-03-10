"""
AI增强代码审查服务

使用LLM分析代码问题，过滤误报，提供修复建议
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

from .static_analyzers import CodeIssue, Severity, ClangTidyAnalyzer, CppcheckAnalyzer
from ....core.llm.factory import get_llm_client
from ....utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CodeQualityScore:
    """代码质量评分"""
    overall_score: float  # 0.0 - 100.0
    
    # 维度评分
    memory_safety: float  # 内存安全
    performance: float  # 性能
    modern_cpp: float  # 现代C++使用
    thread_safety: float  # 线程安全
    code_style: float  # 代码风格
    
    # 问题统计
    total_issues: int
    error_count: int
    warning_count: int
    info_count: int


@dataclass
class ReviewResult:
    """代码审查结果"""
    issues: List[CodeIssue]
    score: CodeQualityScore
    
    # 摘要
    total_issues: int
    filtered_issues: int  # AI过滤掉的误报数
    confidence: float  # 整体置信度
    
    # 按严重程度分组
    critical_issues: List[CodeIssue]
    warning_issues: List[CodeIssue]
    info_issues: List[CodeIssue]
    
    # 建议
    suggestions: List[str]
    
    # 元数据
    analyzed_at: datetime = None
    analysis_duration_seconds: float = 0


class AIEnhancedCodeReview:
    """AI增强代码审查"""
    
    def __init__(self):
        self.clang_tidy = ClangTidyAnalyzer()
        self.cppcheck = CppcheckAnalyzer()
        self.llm_client = get_llm_client()
    
    async def review_code(
        self,
        source_dir: str,
        build_dir: str,
        enable_clang_tidy: bool = True,
        enable_cppcheck: bool = True,
        use_ai_filtering: bool = True,
    ) -> ReviewResult:
        """
        执行AI增强代码审查
        
        Args:
            source_dir: 源代码目录
            build_dir: 构建目录
            enable_clang_tidy: 是否启用Clang-Tidy
            enable_cppcheck: 是否启用Cppcheck
            use_ai_filtering: 是否使用AI过滤误报
            
        Returns:
            审查结果
        """
        started_at = datetime.now()
        all_issues = []
        
        logger.info(
            "code_review_started",
            source_dir=source_dir,
            build_dir=build_dir,
            clang_tidy=enable_clang_tidy,
            cppcheck=enable_cppcheck,
            ai_filtering=use_ai_filtering,
        )
        
        # 运行静态分析
        if enable_clang_tidy:
            logger.info("running_clang_tidy")
            clang_tidy_issues = await self._run_clang_tidy(source_dir, build_dir)
            all_issues.extend(clang_tidy_issues)
        
        if enable_cppcheck:
            logger.info("running_cppcheck")
            cppcheck_issues = await self._run_cppcheck(source_dir)
            all_issues.extend(cppcheck_issues)
        
        # AI过滤和分析
        if use_ai_filtering and all_issues:
            logger.info(
                "ai_filtering_started",
                total_issues=len(all_issues),
            )
            
            filtered_issues = await self._filter_with_ai(all_issues)
        else:
            filtered_issues = all_issues
        
        # 按严重程度分组
        critical_issues = [i for i in filtered_issues if i.severity == Severity.ERROR]
        warning_issues = [i for i in filtered_issues if i.severity == Severity.WARNING]
        info_issues = [i for i in filtered_issues if i.severity in [Severity.INFO, Severity.STYLE]]
        
        # 计算代码质量评分
        score = self._calculate_quality_score(filtered_issues)
        
        # 生成建议
        suggestions = await self._generate_suggestions(filtered_issues)
        
        duration = (datetime.now() - started_at).total_seconds()
        
        result = ReviewResult(
            issues=filtered_issues,
            score=score,
            total_issues=len(all_issues),
            filtered_issues=len(all_issues) - len(filtered_issues),
            confidence=sum(i.confidence for i in filtered_issues) / max(len(filtered_issues), 1),
            critical_issues=critical_issues,
            warning_issues=warning_issues,
            info_issues=info_issues,
            suggestions=suggestions,
            analyzed_at=started_at,
            analysis_duration_seconds=duration,
        )
        
        logger.info(
            "code_review_completed",
            total_issues=len(all_issues),
            filtered_count=len(all_issues) - len(filtered_issues),
            final_count=len(filtered_issues),
            duration=duration,
            score=score.overall_score,
        )
        
        return result
    
    async def _run_clang_tidy(self, source_dir: str, build_dir: str) -> List[CodeIssue]:
        """运行Clang-Tidy"""
        issues = []
        source_path = Path(source_dir)
        
        # 查找所有C++源文件
        cpp_extensions = ['.cpp', '.cc', '.cxx', '.c']
        source_files = [
            str(f) for f in source_path.rglob('*')
            if f.is_file() and f.suffix in cpp_extensions
        ]
        
        # 启用关键检查
        checks = ",".join([
            "clang-analyzer-*",
            "bugprone-*",
            "modernize-*",
            "performance-*",
            "readability-*",
        ])
        
        for source_file in source_files[:20]:  # 限制文件数量避免超时
            try:
                file_issues = await self.clang_tidy.analyze(
                    source_file,
                    build_dir,
                    checks=checks,
                )
                issues.extend(file_issues)
            except Exception as e:
                logger.warning(
                    "clang_tidy_file_failed",
                    file=source_file,
                    error=str(e),
                )
        
        return issues
    
    async def _run_cppcheck(self, source_dir: str) -> List[CodeIssue]:
        """运行Cppcheck"""
        try:
            return await self.cppcheck.analyze(source_dir)
        except Exception as e:
            logger.error(
                "cppcheck_failed",
                source_dir=source_dir,
                error=str(e),
            )
            return []
    
    async def _filter_with_ai(self, issues: List[CodeIssue]) -> List[CodeIssue]:
        """
        使用AI过滤误报
        
        分析代码上下文，判断问题是否真实
        """
        filtered = []
        
        # 分批处理，每次最多10个问题
        batch_size = 10
        for i in range(0, len(issues), batch_size):
            batch = issues[i:i + batch_size]
            
            # 构建prompt
            prompt = self._build_filtering_prompt(batch)
            
            try:
                # 调用LLM
                response = await self.llm_client.complete(
                    prompt=prompt,
                    max_tokens=1000,
                    temperature=0.1,
                )
                
                # 解析响应
                decisions = self._parse_filtering_response(response, batch)
                
                for issue, decision in zip(batch, decisions):
                    if decision["is_valid"]:
                        issue.is_false_positive = False
                        issue.confidence = decision["confidence"]
                        filtered.append(issue)
                    else:
                        issue.is_false_positive = True
                        issue.confidence = decision["confidence"]
                
            except Exception as e:
                logger.error(
                    "ai_filtering_failed",
                    batch_start=i,
                    error=str(e),
                )
                # 如果AI分析失败，保留所有问题
                filtered.extend(batch)
        
        return filtered
    
    def _build_filtering_prompt(self, issues: List[CodeIssue]) -> str:
        """构建AI过滤prompt"""
        issues_desc = []
        
        for i, issue in enumerate(issues):
            issues_desc.append(f"""
{i + 1}. File: {issue.file_path}:{issue.line}
   Tool: {issue.tool}
   Rule: {issue.rule_id}
   Severity: {issue.severity}
   Message: {issue.message}
""")
        
        prompt = f"""你是C/C++代码审查专家。以下是通过静态分析工具发现的潜在问题。请分析每个问题是否为误报。

考虑以下因素判断是否为误报：
1. 代码上下文是否合理
2. 是否是常见的误报模式
3. 问题的严重程度是否合理
4. 是否有明显的误报特征（例如：测试代码、已知安全的模式）

{chr(10).join(issues_desc)}

请对每个问题返回：
- 问题编号（1-{len(issues)}）
- 是否为真实问题（true/false）
- 置信度（0.0-1.0）
- 简短理由

格式：
1. true|false 0.9 reason
2. true|false 0.7 reason
...
"""
        
        return prompt
    
    def _parse_filtering_response(self, response: str, issues: List[CodeIssue]) -> List[dict]:
        """解析AI过滤响应"""
        decisions = []
        
        for line in response.strip().splitlines():
            line = line.strip()
            if not line or not line[0].isdigit():
                continue
            
            parts = line.split(None, 2)
            if len(parts) >= 2:
                is_valid_str = parts[1].split('|')[0].lower()
                is_valid = is_valid_str == 'true'
                
                # 提取置信度
                confidence = 0.5
                if '|' in parts[1]:
                    confidence_str = parts[1].split('|')[1]
                    try:
                        confidence = float(confidence_str)
                    except ValueError:
                        pass
                
                decisions.append({
                    "is_valid": is_valid,
                    "confidence": confidence,
                })
        
        # 如果解析失败，返回默认值
        while len(decisions) < len(issues):
            decisions.append({"is_valid": True, "confidence": 0.5})
        
        return decisions
    
    def _calculate_quality_score(self, issues: List[CodeIssue]) -> CodeQualityScore:
        """计算代码质量评分"""
        # 统计各类问题
        error_count = sum(1 for i in issues if i.severity == Severity.ERROR)
        warning_count = sum(1 for i in issues if i.severity == Severity.WARNING)
        info_count = sum(1 for i in issues if i.severity in [Severity.INFO, Severity.STYLE])
        
        # 按类别统计
        memory_issues = sum(1 for i in issues if i.category == "memory" or "memory" in i.category.lower())
        performance_issues = sum(1 for i in issues if i.category == "performance")
        modern_cpp_issues = sum(1 for i in issues if i.category == "modernization")
        thread_issues = sum(1 for i in issues if "thread" in i.category.lower())
        style_issues = sum(1 for i in issues if i.category == "style" or "readability" in i.category.lower())
        
        # 计算各维度评分（简化版）
        total_issues = len(issues)
        if total_issues == 0:
            return CodeQualityScore(
                overall_score=100.0,
                memory_safety=100.0,
                performance=100.0,
                modern_cpp=100.0,
                thread_safety=100.0,
                code_style=100.0,
                total_issues=0,
                error_count=0,
                warning_count=0,
                info_count=0,
            )
        
        # 基础评分：每个严重问题扣10分，警告扣5分，信息扣1分
        base_score = 100 - (error_count * 10) - (warning_count * 5) - (info_count * 1)
        overall_score = max(base_score, 0)
        
        # 维度评分
        memory_safety = max(100 - memory_issues * 15, 0)
        performance = max(100 - performance_issues * 8, 0)
        modern_cpp = max(100 - modern_cpp_issues * 5, 0)
        thread_safety = max(100 - thread_issues * 12, 0)
        code_style = max(100 - style_issues * 3, 0)
        
        return CodeQualityScore(
            overall_score=overall_score,
            memory_safety=memory_safety,
            performance=performance,
            modern_cpp=modern_cpp,
            thread_safety=thread_safety,
            code_style=code_style,
            total_issues=total_issues,
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
        )
    
    async def _generate_suggestions(self, issues: List[CodeIssue]) -> List[str]:
        """生成修复建议"""
        if not issues:
            return []
        
        # 按类别分组
        categories = {}
        for issue in issues:
            if issue.category not in categories:
                categories[issue.category] = []
            categories[issue.category].append(issue)
        
        suggestions = []
        
        # 为每个类别生成建议
        for category, cat_issues in categories.items():
            if len(cat_issues) >= 5:
                suggestions.append(
                    f"发现{len(cat_issues)}个{category}类问题，建议优先处理"
                )
        
        # 针对高严重性问题
        critical = [i for i in issues if i.severity == Severity.ERROR]
        if critical:
            suggestions.append(
                f"有{len(critical)}个严重错误需要立即修复"
            )
        
        return suggestions


# 全局单例
ai_code_review = AIEnhancedCodeReview()
