"""
AST 解析器单元测试
"""

import pytest
from src.core.analyzers import (
    ASTParser,
    CodeAnalysisResult,
    FunctionInfo,
    ClassInfo,
    get_ast_parser,
)


class TestASTParser:
    """AST 解析器测试"""

    def test_parser_initialization(self):
        """测试解析器初始化"""
        parser = ASTParser()
        assert parser is not None

    def test_parse_simple_function(self):
        """测试解析简单函数"""
        parser = ASTParser()
        code = """
def add(a, b):
    return a + b
"""
        result = parser.parse_code(code, "test.py")

        assert len(result.functions) == 1
        assert result.functions[0].name == "add"
        assert result.functions[0].args == ["a", "b"]
        assert result.functions[0].lineno == 2

    def test_parse_function_with_docstring(self):
        """测试解析带文档字符串的函数"""
        parser = ASTParser()
        code = '''
def calculate_sum(numbers):
    """Calculate the sum of numbers.

    Args:
        numbers: List of numbers

    Returns:
        Sum of numbers
    """
    return sum(numbers)
'''
        result = parser.parse_code(code, "test.py")

        assert len(result.functions) == 1
        func = result.functions[0]
        assert func.name == "calculate_sum"
        assert func.docstring is not None
        assert "Calculate the sum" in func.docstring

    def test_parse_async_function(self):
        """测试解析异步函数"""
        parser = ASTParser()
        code = """
async def fetch_data(url):
    return await http_get(url)
"""
        result = parser.parse_code(code, "test.py")

        assert len(result.functions) == 1
        assert result.functions[0].is_async is True
        assert result.functions[0].name == "fetch_data"

    def test_parse_class(self):
        """测试解析类"""
        parser = ASTParser()
        code = """
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
"""
        result = parser.parse_code(code, "test.py")

        assert len(result.classes) == 1
        cls = result.classes[0]
        assert cls.name == "Calculator"
        assert len(cls.methods) == 2
        assert cls.methods[0].name == "add"
        assert cls.methods[1].name == "subtract"
        assert cls.methods[0].is_method is True

    def test_parse_class_with_inheritance(self):
        """测试解析继承的类"""
        parser = ASTParser()
        code = """
class Animal:
    pass

class Dog(Animal):
    def bark(self):
        return "Woof!"
"""
        result = parser.parse_code(code, "test.py")

        assert len(result.classes) == 2
        animal = result.classes[0]
        dog = result.classes[1]

        assert animal.name == "Animal"
        assert dog.name == "Dog"
        assert len(dog.bases) == 1
        assert dog.bases[0] == "Animal"

    def test_parse_imports(self):
        """测试解析导入语句"""
        parser = ASTParser()
        code = """
import os
import sys as system
from typing import List, Dict
from collections import defaultdict
"""
        result = parser.parse_code(code, "test.py")

        # from typing import List, Dict 会生成 2 个 ImportInfo
        assert len(result.imports) == 5
        assert result.imports[0].module == "os"
        assert result.imports[1].module == "sys"
        assert result.imports[1].alias == "system"
        assert result.imports[2].module == "typing"
        assert result.imports[2].name == "List"
        assert result.imports[3].module == "typing"
        assert result.imports[3].name == "Dict"

        # 检查依赖
        assert "os" in result.dependencies
        assert "sys" in result.dependencies
        assert "typing.List" in result.dependencies
        assert "typing.Dict" in result.dependencies

    def test_extract_function_with_decorators(self):
        """测试解析带装饰器的函数"""
        parser = ASTParser()
        code = """
@property
def name(self):
    return self._name
"""
        result = parser.parse_code(code, "test.py")

        assert len(result.functions) == 1
        func = result.functions[0]
        assert func.name == "name"
        assert "property" in func.decorators

    def test_parse_complex_code(self):
        """测试解析复杂代码"""
        parser = ASTParser()
        code = '''
"""
Utility functions for data processing.
"""

import os
from typing import List, Dict, Optional


def load_data(file_path: str) -> List[Dict]:
    """Load data from a file."""
    pass


class DataProcessor:
    """Process data from various sources."""

    def __init__(self, config: Dict):
        self.config = config

    async def process_async(self, data: List[Dict]) -> Optional[Dict]:
        """Process data asynchronously."""
        pass
'''
        result = parser.parse_code(code, "test.py")

        # 检查导入
        # from typing import List, Dict, Optional 会生成 3 个 ImportInfo
        assert len(result.imports) == 4

        # 检查函数
        assert len(result.functions) == 1
        assert result.functions[0].name == "load_data"

        # 检查类
        assert len(result.classes) == 1
        cls = result.classes[0]
        assert cls.name == "DataProcessor"
        assert len(cls.methods) == 2
        assert cls.methods[0].name == "__init__"
        assert cls.methods[1].name == "process_async"
        assert cls.methods[1].is_async is True

    def test_get_functions_includes_methods(self):
        """测试获取所有函数（包括类方法）"""
        parser = ASTParser()
        code = """
def standalone_function():
    pass

class MyClass:
    def method_one(self):
        pass

    def method_two(self):
        pass
"""
        result = parser.parse_code(code, "test.py")

        all_functions = result.get_functions()
        assert len(all_functions) == 3

        # 检查包含独立函数和类方法
        function_names = [f.name for f in all_functions]
        assert "standalone_function" in function_names
        assert "method_one" in function_names
        assert "method_two" in function_names

    def test_format_for_prompt(self):
        """测试格式化为 Prompt"""
        parser = ASTParser()
        code = """
def add(a, b):
    return a + b

class Calculator:
    def multiply(self, a, b):
        return a * b
"""
        result = parser.parse_code(code, "test.py")
        formatted = parser.format_for_prompt(result)

        assert "# Functions:" in formatted
        assert "def add" in formatted
        assert "# Classes:" in formatted
        assert "class Calculator" in formatted
        assert "def multiply" in formatted


class TestGetASTParser:
    """测试 AST 解析器单例"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        parser1 = get_ast_parser()
        parser2 = get_ast_parser()

        assert parser1 is parser2
