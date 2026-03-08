"""
Radon 复杂度检查器单元测试
"""

import pytest
from src.core.quality import (
    ClassComplexity,
    FunctionComplexity,
    RadonChecker,
    RadonResult,
)


class TestFunctionComplexity:
    """函数复杂度测试"""

    def test_function_creation(self):
        """测试创建函数复杂度"""
        func = FunctionComplexity(
            name="foo",
            fullname="module.Class.foo",
            lineno=10,
            complexity=5,
            type="method",
        )

        assert func.name == "foo"
        assert func.fullname == "module.Class.foo"
        assert func.lineno == 10
        assert func.complexity == 5
        assert func.type == "method"

    def test_function_to_dict(self):
        """测试函数转换为字典"""
        func = FunctionComplexity(
            name="calculate",
            fullname="calculate",
            lineno=1,
            complexity=3,
            type="function",
        )

        data = func.to_dict()

        assert data["name"] == "calculate"
        assert data["complexity"] == 3
        assert data["type"] == "function"


class TestClassComplexity:
    """类复杂度测试"""

    def test_class_creation(self):
        """测试创建类复杂度"""
        cls = ClassComplexity(
            name="Calculator",
            lineno=1,
        )

        assert cls.name == "Calculator"
        assert cls.lineno == 1
        assert cls.total_complexity == 0
        assert cls.average_complexity == 0.0
        assert len(cls.methods) == 0

    def test_class_with_methods(self):
        """测试带方法的类"""
        cls = ClassComplexity(name="Calculator", lineno=1)

        cls.methods.extend([
            FunctionComplexity(
                name="add",
                fullname="Calculator.add",
                lineno=5,
                complexity=2,
                type="method",
            ),
            FunctionComplexity(
                name="subtract",
                fullname="Calculator.subtract",
                lineno=10,
                complexity=3,
                type="method",
            ),
        ])

        cls.total_complexity = 5
        cls.average_complexity = 2.5

        assert len(cls.methods) == 2
        assert cls.total_complexity == 5
        assert cls.average_complexity == 2.5


class TestRadonResult:
    """Radon 结果测试"""

    def test_empty_result(self):
        """测试空结果"""
        result = RadonResult(file_path="test.py")

        assert result.file_path == "test.py"
        assert result.average_complexity == 0.0
        assert result.max_complexity == 0
        assert result.rank == "A"

    def test_result_with_functions(self):
        """测试带函数的结果"""
        result = RadonResult(file_path="test.py")

        result.functions.extend([
            FunctionComplexity(
                name="simple_func",
                fullname="simple_func",
                lineno=1,
                complexity=2,
                type="function",
            ),
            FunctionComplexity(
                name="complex_func",
                fullname="complex_func",
                lineno=10,
                complexity=15,
                type="function",
            ),
        ])

        result.total_complexity = 17
        result.average_complexity = 8.5
        result.max_complexity = 15
        result.rank = result.get_rank_for_complexity(8)

        assert len(result.functions) == 2
        assert result.total_complexity == 17
        assert result.average_complexity == 8.5
        assert result.max_complexity == 15
        assert result.rank == "B"

    def test_simple_functions(self):
        """测试简单函数分类"""
        result = RadonResult(file_path="test.py")

        result.functions.extend([
            FunctionComplexity(
                name=f"func_{i}",
                fullname=f"func_{i}",
                lineno=i,
                complexity=i,
                type="function",
            )
            for i in range(1, 6)  # 1-5
        ])

        assert len(result.simple_functions) == 5
        assert len(result.moderate_functions) == 0

    def test_moderate_functions(self):
        """测试中等复杂度函数分类"""
        result = RadonResult(file_path="test.py")

        result.functions.extend([
            FunctionComplexity(
                name="func_6",
                fullname="func_6",
                lineno=6,
                complexity=6,
                type="function",
            ),
            FunctionComplexity(
                name="func_10",
                fullname="func_10",
                lineno=10,
                complexity=10,
                type="function",
            ),
        ])

        assert len(result.moderate_functions) == 2

    def test_complex_functions(self):
        """测试复杂函数分类"""
        result = RadonResult(file_path="test.py")

        result.functions.extend([
            FunctionComplexity(
                name="complex_func",
                fullname="complex_func",
                lineno=1,
                complexity=15,
                type="function",
            ),
        ])

        assert len(result.complex_functions) == 1

    def test_very_complex_functions(self):
        """测试非常复杂函数分类"""
        result = RadonResult(file_path="test.py")

        result.functions.extend([
            FunctionComplexity(
                name="very_complex",
                fullname="very_complex",
                lineno=1,
                complexity=25,
                type="function",
            ),
        ])

        assert len(result.very_complex_functions) == 1

    def test_rank_thresholds(self):
        """测试等级阈值"""
        result = RadonResult(file_path="test.py")

        # A 级 (1-5)
        assert result.get_rank_for_complexity(1) == "A"
        assert result.get_rank_for_complexity(5) == "A"

        # B 级 (6-10)
        assert result.get_rank_for_complexity(6) == "B"
        assert result.get_rank_for_complexity(10) == "B"

        # C 级 (11-20)
        assert result.get_rank_for_complexity(11) == "C"
        assert result.get_rank_for_complexity(20) == "C"

        # D 级 (21-30)
        assert result.get_rank_for_complexity(21) == "D"
        assert result.get_rank_for_complexity(30) == "D"

        # E 级 (31-40)
        assert result.get_rank_for_complexity(31) == "E"
        assert result.get_rank_for_complexity(40) == "E"

        # F 级 (41+)
        assert result.get_rank_for_complexity(41) == "F"
        assert result.get_rank_for_complexity(100) == "F"


class TestRadonChecker:
    """Radon 检查器测试"""

    def test_checker_initialization(self):
        """测试检查器初始化"""
        checker = RadonChecker()

        assert checker is not None
        assert checker.max_complexity == 10

    def test_checker_with_custom_max_complexity(self):
        """测试自定义最大复杂度"""
        checker = RadonChecker(max_complexity=5)

        assert checker.max_complexity == 5

    def test_check_code_simple_function(self):
        """测试检查简单函数"""
        checker = RadonChecker()

        code = """
def add(a, b):
    return a + b
"""

        result = checker.check_code(code, "test.py")

        assert isinstance(result, RadonResult)
        assert len(result.functions) == 1
        assert result.functions[0].name == "add"
        assert result.functions[0].complexity <= 5

    def test_check_code_with_class(self):
        """测试检查带类的代码"""
        checker = RadonChecker()

        code = """
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
"""

        result = checker.check_code(code, "test.py")

        assert isinstance(result, RadonResult)
        assert len(result.classes) == 1
        assert result.classes[0].name == "Calculator"
        assert len(result.classes[0].methods) == 2

    def test_check_code_complex_function(self):
        """测试检查复杂函数"""
        checker = RadonChecker()

        # 创建一个复杂函数（多个分支）
        code = """
def complex_function(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                return 1
            else:
                return 2
        else:
            if z > 0:
                return 3
            else:
                return 4
    else:
        if y > 0:
            return 5
        else:
            return 6
"""

        result = checker.check_code(code, "test.py")

        assert isinstance(result, RadonResult)
        assert len(result.functions) == 1
        # 复杂度应该大于 5（因为有很多 if 分支）
        assert result.functions[0].complexity > 5

    def test_check_code_with_multiple_functions(self):
        """测试检查多个函数"""
        checker = RadonChecker()

        code = """
def func1():
    return 1

def func2():
    return 2

def func3():
    return 3
"""

        result = checker.check_code(code, "test.py")

        assert len(result.functions) == 3
        assert result.total_complexity == sum(f.complexity for f in result.functions)

    def test_get_summary(self):
        """测试获取汇总"""
        checker = RadonChecker()

        results = [
            RadonResult(file_path="file1.py", average_complexity=5.0, rank="A"),
            RadonResult(file_path="file2.py", average_complexity=8.0, rank="B"),
            RadonResult(file_path="file3.py", average_complexity=15.0, rank="C"),
        ]

        # 添加函数
        for i, result in enumerate(results):
            result.functions.append(
                FunctionComplexity(
                    name=f"func_{i}",
                    fullname=f"func_{i}",
                    lineno=1,
                    complexity=int(result.average_complexity),
                    type="function",
                )
            )

        summary = checker.get_summary(results)

        assert summary["total_files"] == 3
        assert summary["average_complexity"] > 0
        assert "rank_distribution" in summary
        assert summary["rank_distribution"]["A"] >= 1
        assert "complexity_distribution" in summary

    def test_get_recommendations(self):
        """测试获取建议"""
        checker = RadonChecker()

        # 高复杂度结果
        result = RadonResult(file_path="test.py", average_complexity=15.0, rank="C")

        result.functions.extend([
            FunctionComplexity(
                name="very_complex",
                fullname="very_complex",
                lineno=1,
                complexity=25,
                type="function",
            ),
        ])

        recommendations = checker.get_recommendations(result)

        assert len(recommendations) > 0
        assert any("复杂度" in r for r in recommendations)

    def test_get_recommendations_good_code(self):
        """测试获取建议（代码良好）"""
        checker = RadonChecker()

        # 低复杂度结果
        result = RadonResult(file_path="test.py", average_complexity=3.0, rank="A")

        result.functions.extend([
            FunctionComplexity(
                name=f"simple_{i}",
                fullname=f"simple_{i}",
                lineno=i,
                complexity=2,
                type="function",
            )
            for i in range(1, 4)
        ])

        recommendations = checker.get_recommendations(result)

        # 应该有正面反馈
        assert len(recommendations) > 0
        assert any("保持" in r or "良好" in r for r in recommendations)
