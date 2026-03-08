"""
测试生成 Agent 单元测试
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.core.agents import (
    GeneratedTest,
    TestGenerationResult,
    TestGeneratorAgent,
    get_test_generator,
)


class TestGeneratedTest:
    """生成测试数据模型测试"""

    def test_generated_test_creation(self):
        """测试创建 GeneratedTest"""
        test = GeneratedTest(
            file_path="tests/test_main.py",
            test_code="def test_add():\n    assert add(1, 1) == 2",
            target_function="add",
            test_type="NORMAL",
            coverage_estimate=0.8,
        )

        assert test.file_path == "tests/test_main.py"
        assert test.target_function == "add"
        assert test.test_type == "NORMAL"
        assert test.coverage_estimate == 0.8


class TestTestGenerationResult:
    """测试生成结果数据模型测试"""

    def test_empty_result(self):
        """测试空结果"""
        result = TestGenerationResult(target_file="main.py")

        assert len(result.tests) == 0
        assert result.total_coverage_estimate == 0.0
        assert result.target_file == "main.py"

    def test_add_test(self):
        """测试添加测试"""
        result = TestGenerationResult(target_file="main.py")

        test = GeneratedTest(
            file_path="tests/test_main.py",
            test_code="def test_func(): pass",
            target_function="func",
            test_type="NORMAL",
        )

        result.tests.append(test)
        result.total_coverage_estimate = 0.5

        assert len(result.tests) == 1
        assert result.total_coverage_estimate == 0.5


class TestTestGeneratorAgent:
    """测试生成代理测试"""

    def test_agent_initialization(self):
        """测试代理初始化"""
        # 不需要 LLM 客户端也可以初始化（用于代码分析）
        agent = TestGeneratorAgent(llm_client=None, ast_parser=None)

        assert agent is not None
        assert agent.llm_client is None
        assert agent.ast_parser is None

    @pytest.mark.asyncio
    async def test_generate_tests_without_llm(self):
        """测试没有 LLM 客户端时生成测试"""
        agent = TestGeneratorAgent(llm_client=None, ast_parser=None)

        code = """
def add(a, b):
    return a + b
"""

        result = await agent.generate_tests(code, "main.py")

        # 应该返回错误
        assert len(result.errors) > 0
        assert "LLM 客户端未配置" in result.errors[0]

    def test_extract_test_code(self):
        """测试提取测试代码"""
        agent = TestGeneratorAgent(llm_client=None, ast_parser=None)

        # 带 markdown 标记
        code_with_markdown = """```python
def test_add():
    assert add(1, 1) == 2
```"""

        extracted = agent._extract_test_code(code_with_markdown)
        assert "def test_add" in extracted
        assert "```" not in extracted

        # 不带 markdown 标记
        code_plain = "def test_add():\n    assert add(1, 1) == 2"
        extracted = agent._extract_test_code(code_plain)
        assert "def test_add" in extracted

    def test_get_test_file_path(self):
        """测试生成测试文件路径"""
        agent = TestGeneratorAgent(llm_client=None, ast_parser=None)

        # src/module/file.py -> tests/module/test_file.py
        path1 = agent._get_test_file_path("src/module/file.py")
        # 路径转换保留了模块目录
        assert "test_file.py" in path1
        assert "tests/" in path1
        assert "module/" in path1 or path1 == "tests/module/test_file.py"

        # module/file.py -> tests/test_file.py
        path2 = agent._get_test_file_path("module/file.py")
        # 不包含 src/ 时，会添加 tests/ 前缀但保留子目录
        assert "test_file.py" in path2
        assert "tests/" in path2

    @patch('src.core.agents.test_generator.get_ast_parser')
    def test_estimate_coverage(self, mock_get_parser):
        """测试覆盖率估算"""
        from src.core.analyzers import CodeAnalysisResult, FunctionInfo

        # Mock 分析结果
        mock_analysis = CodeAnalysisResult(file_path="main.py")
        mock_analysis.functions = [
            FunctionInfo(name="func1", lineno=1, args=[]),
            FunctionInfo(name="func2", lineno=5, args=[]),
        ]

        agent = TestGeneratorAgent(llm_client=None, ast_parser=None)

        # 测试代码包含 2 个测试函数
        test_code = """
def test_func1():
    assert func1() == "result"

def test_func2():
    assert func2() == "result"
"""

        coverage = agent._estimate_coverage(mock_analysis, test_code)

        # 应该接近 1.0（2 个函数都有测试）
        assert coverage > 0.5

    def test_estimate_coverage_no_analysis(self):
        """测试没有分析结果时的覆盖率估算"""
        agent = TestGeneratorAgent(llm_client=None, ast_parser=None)

        test_code = "def test_func(): pass"

        coverage = agent._estimate_coverage(None, test_code)

        # 应该返回默认值
        assert coverage == 0.5

    @pytest.mark.asyncio
    async def test_generate_tests_with_mock_llm(self):
        """测试使用 Mock LLM 生成测试"""
        from src.core.analyzers import ASTParser

        # Mock LLM 响应
        mock_llm = Mock()
        mock_llm.generate = AsyncMock(return_value="def test_add():\n    assert add(1, 1) == 2")

        # 创建 AST 解析器
        ast_parser = ASTParser()

        agent = TestGeneratorAgent(llm_client=mock_llm, ast_parser=ast_parser)

        code = """
def add(a, b):
    return a + b
"""

        result = await agent.generate_tests(code, "main.py")

        # 验证结果
        assert len(result.errors) == 0
        assert len(result.tests) == 1
        assert result.tests[0].test_code == "def test_add():\n    assert add(1, 1) == 2"
        assert result.target_file == "main.py"

    def test_build_prompt(self):
        """测试构建 Prompt"""
        from src.core.analyzers import ASTParser

        ast_parser = ASTParser()
        agent = TestGeneratorAgent(llm_client=None, ast_parser=ast_parser)

        code = """
def add(a, b):
    return a + b
"""

        # 解析代码
        analysis = ast_parser.parse_code(code, "test.py")

        # 构建 Prompt
        prompt = agent._build_prompt(code, analysis, {})

        # 验证 Prompt 包含关键信息
        assert "def add" in prompt
        assert "return a + b" in prompt


class TestGetTestGenerator:
    """测试测试生成代理单例"""

    @patch('src.core.agents.test_generator.get_claude_client')
    @patch('src.core.agents.test_generator.get_ast_parser')
    def test_singleton_pattern(self, mock_get_ast, mock_get_claude):
        """测试单例模式"""
        # Mock 返回值
        mock_get_claude.return_value = Mock()
        mock_get_ast.return_value = Mock()

        generator1 = get_test_generator()
        generator2 = get_test_generator()

        assert generator1 is generator2
