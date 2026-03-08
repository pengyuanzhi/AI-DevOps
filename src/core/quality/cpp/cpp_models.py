"""
C++ 静态分析数据模型
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CppIssue:
    """C++ 代码问题"""
    tool: str  # clang-tidy, cppcheck
    severity: str  # critical, error, warning, info, style
    category: str  # memory, performance, modern-cpp, thread-safety, etc.
    file: str
    line: int
    column: int
    message: str
    suggestion: Optional[str] = None
    rule_id: Optional[str] = None  # e.g., modernize-avoid-c-arrays, cppcoreguidelines-pro-type-reinterpret-cast
    code_snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tool": self.tool,
            "severity": self.severity,
            "category": self.category,
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "suggestion": self.suggestion,
            "rule_id": self.rule_id,
            "code_snippet": self.code_snippet,
        }


@dataclass
class ClangTidyIssue(CppIssue):
    """Clang-tidy 问题"""
    tool: str = field(default="clang-tidy", init=False)


@dataclass
class CppcheckIssue(CppIssue):
    """Cppcheck 问题"""
    tool: str = field(default="cppcheck", init=False)


@dataclass
class StaticAnalysisResult:
    """静态分析结果"""
    file_path: str
    issues: List[CppIssue] = field(default_factory=list)

    # 统计信息
    clang_tidy_issues: List[ClangTidyIssue] = field(default_factory=list)
    cppcheck_issues: List[CppcheckIssue] = field(default_factory=list)

    # 分类统计
    memory_issues: List[CppIssue] = field(default_factory=list)
    performance_issues: List[CppIssue] = field(default_factory=list)
    modern_cpp_issues: List[CppIssue] = field(default_factory=list)
    thread_safety_issues: List[CppIssue] = field(default_factory=list)
    style_issues: List[CppIssue] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        return len(self.issues)

    @property
    def critical_count(self) -> int:
        return len([i for i in self.issues if i.severity == "critical"])

    @property
    def error_count(self) -> int:
        return len([i for i in self.issues if i.severity == "error"])

    @property
    def warning_count(self) -> int:
        return len([i for i in self.issues if i.severity == "warning"])

    @property
    def info_count(self) -> int:
        return len([i for i in self.issues if i.severity == "info"])

    @property
    def style_count(self) -> int:
        return len([i for i in self.issues if i.severity == "style"])

    def get_issues_by_category(self, category: str) -> List[CppIssue]:
        """按类别获取问题"""
        return [i for i in self.issues if i.category == category]

    def get_issues_by_severity(self, severity: str) -> List[CppIssue]:
        """按严重性获取问题"""
        return [i for i in self.issues if i.severity == severity]

    def categorize_issues(self) -> None:
        """对问题进行分类"""
        for issue in self.issues:
            # 根据规则 ID 或消息判断类别
            if issue.category:
                # 已经有类别，直接添加
                if issue.category == "memory":
                    self.memory_issues.append(issue)
                elif issue.category == "performance":
                    self.performance_issues.append(issue)
                elif issue.category == "modern-cpp":
                    self.modern_cpp_issues.append(issue)
                elif issue.category == "thread-safety":
                    self.thread_safety_issues.append(issue)
                elif issue.category == "style":
                    self.style_issues.append(issue)
                else:
                    self.style_issues.append(issue)
            else:
                # 根据规则 ID 自动分类
                self._auto_categorize(issue)

    def _auto_categorize(self, issue: CppIssue) -> None:
        """自动分类问题"""
        rule_id = issue.rule_id or ""
        message = issue.message.lower()

        # 内存相关
        memory_keywords = ["memory", "leak", "delete", "free", "pointer", "alloc", "buffer", "overflow"]
        if any(kw in rule_id.lower() or kw in message for kw in memory_keywords):
            issue.category = "memory"
            self.memory_issues.append(issue)
            return

        # 性能相关
        perf_keywords = ["performance", "inefficient", "slow", "optimize", "complexity"]
        if any(kw in rule_id.lower() or kw in message for kw in perf_keywords):
            issue.category = "performance"
            self.performance_issues.append(issue)
            return

        # 现代 C++
        modern_keywords = ["modernize", "c++11", "c++14", "c++17", "auto", "nullptr", "smart"]
        if any(kw in rule_id.lower() or kw in message for kw in modern_keywords):
            issue.category = "modern-cpp"
            self.modern_cpp_issues.append(issue)
            return

        # 线程安全
        thread_keywords = ["thread", "mutex", "lock", "race", "concurrency", "atomic"]
        if any(kw in rule_id.lower() or kw in message for kw in thread_keywords):
            issue.category = "thread-safety"
            self.thread_safety_issues.append(issue)
            return

        # 默认为风格问题
        issue.category = "style"
        self.style_issues.append(issue)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "file_path": self.file_path,
            "total_issues": self.total_issues,
            "critical_count": self.critical_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "style_count": self.style_count,
            "memory_issues_count": len(self.memory_issues),
            "performance_issues_count": len(self.performance_issues),
            "modern_cpp_issues_count": len(self.modern_cpp_issues),
            "thread_safety_issues_count": len(self.thread_safety_issues),
            "issues": [i.to_dict() for i in self.issues],
        }


@dataclass
class CppCodeQualityScore:
    """C++ 代码质量分数"""
    file_path: str
    overall_score: float = 0.0  # 0-100

    # 维度分数
    memory_safety_score: float = 0.0
    performance_score: float = 0.0
    modern_cpp_score: float = 0.0
    thread_safety_score: float = 0.0
    code_style_score: float = 0.0

    # 统计
    total_issues: int = 0
    critical_issues: int = 0
    high_priority_issues: int = 0

    def calculate_overall_score(self, weights: Optional[Dict[str, float]] = None) -> float:
        """计算总体分数"""
        if weights is None:
            weights = {
                "memory_safety": 0.35,
                "performance": 0.25,
                "modern_cpp": 0.20,
                "thread_safety": 0.10,
                "code_style": 0.10,
            }

        self.overall_score = (
            self.memory_safety_score * weights.get("memory_safety", 0.35) +
            self.performance_score * weights.get("performance", 0.25) +
            self.modern_cpp_score * weights.get("modern_cpp", 0.20) +
            self.thread_safety_score * weights.get("thread_safety", 0.10) +
            self.code_style_score * weights.get("code_style", 0.10)
        )

        return round(self.overall_score, 2)

    def get_grade(self) -> str:
        """获取等级"""
        if self.overall_score >= 90:
            return "A"
        elif self.overall_score >= 80:
            return "B"
        elif self.overall_score >= 70:
            return "C"
        elif self.overall_score >= 60:
            return "D"
        else:
            return "F"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "file_path": self.file_path,
            "overall_score": round(self.overall_score, 2),
            "grade": self.get_grade(),
            "memory_safety_score": round(self.memory_safety_score, 2),
            "performance_score": round(self.performance_score, 2),
            "modern_cpp_score": round(self.modern_cpp_score, 2),
            "thread_safety_score": round(self.thread_safety_score, 2),
            "code_style_score": round(self.code_style_score, 2),
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "high_priority_issues": self.high_priority_issues,
        }
