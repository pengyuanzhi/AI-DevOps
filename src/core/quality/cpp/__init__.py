"""
C++ 静态分析模块
"""

from src.core.quality.cpp.cpp_models import (
    CppIssue,
    CppcheckIssue,
    CppCodeQualityScore,
    ClangTidyIssue,
    StaticAnalysisResult,
)
from src.core.quality.cpp.clang_tidy_checker import (
    ClangTidyChecker,
    ClangTidyConfig,
    get_clang_tidy_checker,
)
from src.core.quality.cpp.cppcheck_checker import (
    CppcheckChecker,
    get_cppcheck_checker,
)

__all__ = [
    # Models
    "CppIssue",
    "CppcheckIssue",
    "ClangTidyIssue",
    "StaticAnalysisResult",
    "CppCodeQualityScore",
    # Clang-tidy
    "ClangTidyChecker",
    "ClangTidyConfig",
    "get_clang_tidy_checker",
    # Cppcheck
    "CppcheckChecker",
    "get_cppcheck_checker",
]
