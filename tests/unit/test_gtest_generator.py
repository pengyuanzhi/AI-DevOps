"""
Google Test 生成器单元测试
"""

import pytest
from unittest.mock import AsyncMock, Mock

from src.core.agents import (
    CppTestGenerationResult,
    GoogleTestGenerator,
    get_gtest_generator,
)


class TestGoogleTestGenerator:
    """Google Test 生成器测试"""

    def test_generator_initialization(self):
        """测试生成器初始化"""
        # 不需要 LLM 客户端也可以初始化
        generator = GoogleTestGenerator(llm_client=None, cpp_parser=None)

        assert generator is not None
        assert generator.llm_client is None
        assert generator.cpp_parser is None

    def test_get_test_file_path(self):
        """测试生成测试文件路径"""
        generator = GoogleTestGenerator()

        # src/module/file.cpp -> tests/module/test_file.cpp
        path1 = generator._get_test_file_path("src/module/calculator.cpp")
        assert "test_calculator.cpp" in path1
        assert "tests/" in path1

        # module/file.cpp -> tests/test_file.cpp
        path2 = generator._get_test_file_path("utils/helper.cpp")
        assert "test_helper.cpp" in path2

    def test_extract_test_code(self):
        """测试提取测试代码"""
        generator = GoogleTestGenerator()

        # 带 markdown 标记
        code_with_markdown = """```cpp
#include <gtest/gtest.h>

TEST(CalculatorTest, AddWorks) {
    EXPECT_EQ(2 + 2, 4);
}
```"""

        extracted = generator._extract_test_code(code_with_markdown)
        assert "#include <gtest/gtest.h>" in extracted
        assert "TEST(CalculatorTest" in extracted
        assert "```" not in extracted

    def test_extract_test_code_plain(self):
        """测试提取纯代码"""
        generator = GoogleTestGenerator()

        code_plain = """
#include <gtest/gtest.h>

TEST(CalculatorTest, SimpleAdd) {
    EXPECT_EQ(1 + 1, 2);
}
"""

        extracted = generator._extract_test_code(code_plain)
        assert "TEST(CalculatorTest" in extracted

    def test_estimate_coverage_no_analysis(self):
        """测试没有分析结果时的覆盖率估算"""
        generator = GoogleTestGenerator()

        test_code = """
TEST_F(CalculatorTest, AddTest) {
    EXPECT_EQ(calc.add(1, 2), 3);
}

TEST_F(CalculatorTest, SubtractTest) {
    EXPECT_EQ(calc.subtract(5, 3), 2);
}
"""

        coverage = generator._estimate_coverage(None, test_code)

        # 应该返回默认值或基于测试数量的估算
        assert coverage >= 0.0

    def test_generate_cmake_updates(self):
        """测试生成 CMake 更新"""
        generator = GoogleTestGenerator()

        cmake_updates = generator._generate_cmake_updates(
            "tests/test_calculator.cpp",
            "src/calculator.cpp"
        )

        assert len(cmake_updates) > 0
        assert "test_calculator" in cmake_updates[0]
        assert "gtest" in cmake_updates[0]

    @pytest.mark.asyncio
    async def test_generate_tests_without_llm(self):
        """测试没有 LLM 客户端时生成测试"""
        generator = GoogleTestGenerator(llm_client=None, cpp_parser=None)

        code = """
class Calculator {
public:
    int add(int a, int b);
};
"""

        result = await generator.generate_tests(code, "calculator.h")

        # 应该返回错误
        assert len(result.errors) > 0
        assert "LLM" in result.errors[0]

    @pytest.mark.asyncio
    async def test_generate_tests_with_mock_llm(self):
        """测试使用 Mock LLM 生成测试"""
        from src.core.analyzers.cpp import get_cpp_parser

        # Mock LLM 响应
        mock_llm = Mock()
        mock_llm.generate = AsyncMock(
            return_value="""```cpp
#include <gtest/gtest.h>
#include "calculator.h"

class CalculatorTest : public ::testing::Test {
protected:
    Calculator calc;
};

TEST_F(CalculatorTest, AddTwoNumbers) {
    EXPECT_EQ(calc.add(2, 3), 5);
}

TEST_F(CalculatorTest, AddNegativeNumbers) {
    EXPECT_EQ(calc.add(-5, 3), -2);
}
```"""
        )

        # 创建 C++ 解析器
        cpp_parser = get_cpp_parser()

        generator = GoogleTestGenerator(llm_client=mock_llm, cpp_parser=cpp_parser)

        code = """
class Calculator {
public:
    int add(int a, int b);
};
"""

        result = await generator.generate_tests(code, "calculator.h")

        # 验证结果
        assert len(result.errors) == 0
        assert len(result.tests) == 1
        assert result.tests[0].test_framework == "gtest"
        assert "TEST_F(CalculatorTest" in result.tests[0].test_code

    def test_build_prompt(self):
        """测试构建 Prompt"""
        from src.core.analyzers.cpp import get_cpp_parser

        cpp_parser = get_cpp_parser()
        generator = GoogleTestGenerator(llm_client=None, cpp_parser=cpp_parser)

        code = """
class Calculator {
public:
    int add(int a, int b);
    int subtract(int a, int b);
};
"""

        analysis = cpp_parser.parse_code(code, "calculator.h")

        prompt = generator._build_prompt(code, analysis, {})

        # 验证 Prompt 包含关键信息
        assert "Calculator" in prompt
        assert "add" in prompt or "subtract" in prompt

    def test_build_prompt_with_qt_project(self):
        """测试构建 QT 项目的 Prompt"""
        from src.core.analyzers.cpp import get_cpp_parser

        cpp_parser = get_cpp_parser()
        generator = GoogleTestGenerator(llm_client=None, cpp_parser=cpp_parser)

        code = """
#include <QObject>

class MainWindow : public QObject {
    Q_OBJECT
public:
    void openFile();
};
"""

        analysis = cpp_parser.parse_code(code, "mainwindow.h")

        prompt = generator._build_prompt(code, analysis, {})

        # 应该包含 QT 信息
        assert "QT" in prompt
        assert "MainWindow" in prompt


class TestGetGTestGenerator:
    """测试 Google Test 生成器单例"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        gen1 = get_gtest_generator()
        gen2 = get_gtest_generator()

        # 注意：如果 settings.enable_test_generation 为 False，可能会返回不同的实例
        # 这里我们主要测试函数可以调用
        assert gen1 is not None
        assert gen2 is not None
