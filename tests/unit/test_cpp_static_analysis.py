"""
C++ 静态分析单元测试
"""

import pytest
from unittest.mock import Mock, patch

from src.core.quality.cpp import (
    CppIssue,
    CppCodeQualityScore,
    StaticAnalysisResult,
    ClangTidyIssue,
    CppcheckIssue,
)


class TestCppModels:
    """C++ 模型测试"""

    def test_cpp_issue_creation(self):
        """测试创建 C++ 问题"""
        issue = CppIssue(
            tool="clang-tidy",
            severity="warning",
            category="memory",
            file="test.cpp",
            line=10,
            column=5,
            message="Potential memory leak",
            rule_id="clang-analyzer-cplusplus.NewDelete",
        )

        assert issue.tool == "clang-tidy"
        assert issue.severity == "warning"
        assert issue.category == "memory"

    def test_static_analysis_result_empty(self):
        """测试空的静态分析结果"""
        result = StaticAnalysisResult(file_path="test.cpp")

        assert result.file_path == "test.cpp"
        assert result.total_issues == 0
        assert result.critical_count == 0

    def test_static_analysis_result_with_issues(self):
        """测试带问题的静态分析结果"""
        result = StaticAnalysisResult(file_path="test.cpp")

        # 添加问题
        result.issues.append(
            CppIssue(
                tool="clang-tidy",
                severity="critical",  # 改为 critical
                category="memory",
                file="test.cpp",
                line=5,
                column=0,
                message="Memory leak",
                rule_id="clang-analyzer-cplusplus.NewDeleteLeaks",
            )
        )
        result.issues.append(
            CppIssue(
                tool="cppcheck",
                severity="warning",
                category="performance",
                file="test.cpp",
                line=10,
                column=0,
                message="Inefficient container operation",
                rule_id="stlContainer",
            )
        )

        assert result.total_issues == 2
        assert result.critical_count == 1
        assert result.warning_count == 1

        # 分类问题
        result.categorize_issues()
        assert len(result.memory_issues) == 1
        assert len(result.performance_issues) == 1

    def test_cpp_quality_score(self):
        """测试 C++ 代码质量分数"""
        score = CppCodeQualityScore(file_path="test.cpp")

        score.total_issues = 10
        score.critical_issues = 1
        score.high_priority_issues = 5

        score.memory_safety_score = 80.0
        score.performance_score = 75.0
        score.modern_cpp_score = 90.0
        score.thread_safety_score = 100.0
        score.code_style_score = 85.0

        overall = score.calculate_overall_score()

        assert overall > 0
        assert overall <= 100
        assert score.overall_score == overall

    def test_grade_calculation(self):
        """测试等级计算"""
        score = CppCodeQualityScore(file_path="test.cpp")

        score.overall_score = 95.0
        assert score.get_grade() == "A"

        score.overall_score = 82.0
        assert score.get_grade() == "B"

        score.overall_score = 75.0
        assert score.get_grade() == "C"

        score.overall_score = 45.0
        assert score.get_grade() == "F"


class TestClangTidyIssue:
    """Clang-tidy 问题测试"""

    def test_auto_set_tool(self):
        """测试自动设置工具名称"""
        issue = ClangTidyIssue(
            severity="warning",
            category="memory",
            file="test.cpp",
            line=10,
            column=0,
            message="Test message",
        )

        assert issue.tool == "clang-tidy"


class TestCppcheckIssue:
    """Cppcheck 问题测试"""

    def test_auto_set_tool(self):
        """测试自动设置工具名称"""
        issue = CppcheckIssue(
            severity="error",
            category="memory",
            file="test.cpp",
            line=10,
            column=0,
            message="Test message",
        )

        assert issue.tool == "cppcheck"


class TestStaticAnalysisCategorization:
    """静态分析分类测试"""

    def test_auto_categorize_memory(self):
        """测试自动分类内存问题"""
        result = StaticAnalysisResult(file_path="test.cpp")

        # 内存相关问题
        result.issues.append(
            CppIssue(
                tool="test",
                severity="warning",
                category="",  # 空类别，需要自动分类
                file="test.cpp",
                line=10,
                column=0,
                message="Memory leak detected",
                rule_id="memory-leak",
            )
        )

        result.categorize_issues()

        assert len(result.memory_issues) == 1
        assert result.issues[0].category == "memory"

    def test_auto_categorize_performance(self):
        """测试自动分类性能问题"""
        result = StaticAnalysisResult(file_path="test.cpp")

        result.issues.append(
            CppIssue(
                tool="test",
                severity="warning",
                category="",
                file="test.cpp",
                line=10,
                column=0,
                message="Performance: inefficient loop",
                rule_id="performance-inefficient",
            )
        )

        result.categorize_issues()

        assert len(result.performance_issues) == 1
        assert result.issues[0].category == "performance"

    def test_auto_categorize_modern_cpp(self):
        """测试自动分类现代 C++ 问题"""
        result = StaticAnalysisResult(file_path="test.cpp")

        result.issues.append(
            CppIssue(
                tool="test",
                severity="info",
                category="",
                file="test.cpp",
                line=10,
                column=0,
                message="Use nullptr instead of NULL",
                rule_id="modernize-use-nullptr",
            )
        )

        result.categorize_issues()

        assert len(result.modern_cpp_issues) == 1
        assert result.issues[0].category == "modern-cpp"
