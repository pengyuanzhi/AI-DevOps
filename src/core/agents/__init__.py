"""
Agent 模块初始化
"""

# C/C++/QT Agents (MVP)
from src.core.agents.cpp_reviewer import (
    CppCodeReviewResult,
    CppCodeReviewerAgent,
    get_cpp_reviewer,
)
from src.core.agents.cpp_test_generator import (
    CppTestGenerationResult,
    GeneratedCppTest,
    get_gtest_generator,
    GoogleTestGenerator,
)

# Python Agents (已弃用，仅用于兼容)
from src.core.agents.code_reviewer import (
    CodeReviewResult,
    CodeReviewerAgent,
    FileReview,
    Issue,
    IssueSeverity,
    ReviewDimension,
    RiskLevel,
    get_code_reviewer,
)
from src.core.agents.test_generator import (
    GeneratedTest,
    TestGenerationResult,
    TestGeneratorAgent,
    get_test_generator,
)

__all__ = [
    # C/C++/QT
    "GoogleTestGenerator",
    "GeneratedCppTest",
    "CppTestGenerationResult",
    "get_gtest_generator",
    "CppCodeReviewerAgent",
    "CppCodeReviewResult",
    "get_cpp_reviewer",
    # Python (legacy)
    "GeneratedTest",
    "TestGenerationResult",
    "TestGeneratorAgent",
    "get_test_generator",
    # Code Review
    "CodeReviewResult",
    "CodeReviewerAgent",
    "FileReview",
    "Issue",
    "IssueSeverity",
    "ReviewDimension",
    "RiskLevel",
    "get_code_reviewer",
]
