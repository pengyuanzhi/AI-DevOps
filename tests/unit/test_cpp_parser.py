"""
C++ 解析器单元测试
"""

import pytest
from src.core.analyzers.cpp import (
    CppAnalysisResult,
    CppClassInfo,
    CppFunctionInfo,
    get_cpp_parser,
)


class TestSimpleCppParser:
    """C++ 解析器测试"""

    def test_parser_initialization(self):
        """测试解析器初始化"""
        parser = get_cpp_parser()
        assert parser is not None

    def test_parse_simple_class(self):
        """测试解析简单类"""
        parser = get_cpp_parser()

        code = """
class Calculator {
public:
    double add(double a, double b);
    double subtract(double a, double b);
};
"""

        result = parser.parse_code(code, "calculator.h")

        assert isinstance(result, CppAnalysisResult)
        assert len(result.classes) == 1
        assert result.classes[0].name == "Calculator"

    def test_parse_class_with_methods(self):
        """测试解析带方法的类"""
        parser = get_cpp_parser()

        code = """
class Calculator {
public:
    double add(double a, double b) {
        return a + b;
    }

    double divide(double a, double b) {
        if (b == 0.0) {
            throw std::invalid_argument("Division by zero");
        }
        return a / b;
    }

private:
    double lastResult;
};
"""

        result = parser.parse_code(code, "calculator.cpp")

        assert len(result.classes) == 1
        cls = result.classes[0]
        assert cls.name == "Calculator"
        assert len(cls.methods) >= 2  # 至少有 add 和 divide

    def test_parse_free_function(self):
        """测试解析自由函数"""
        parser = get_cpp_parser()

        code = """
double calculateCircleArea(double radius) {
    return 3.14159 * radius * radius;
}

int factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}
"""

        result = parser.parse_code(code, "math.cpp")

        assert len(result.functions) > 0

    def test_detect_qt_project(self):
        """测试检测 QT 项目"""
        parser = get_cpp_parser()

        qt_code = """
#include <QObject>
#include <QWidget>

class MainWindow : public QWidget {
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);
};
"""

        result = parser.parse_code(qt_code, "mainwindow.h")

        assert result.is_qt_project is True
        assert "QtWidgets" in result.qt_modules or "QtCore" in result.qt_modules

    def test_parse_includes(self):
        """测试解析 include 语句"""
        parser = get_cpp_parser()

        code = """
#include <iostream>
#include <vector>
#include <string>
#include "calculator.h"
#include <gtest/gtest.h>
"""

        result = parser.parse_code(code, "test.cpp")

        assert len(result.includes) >= 5

        # 检查系统头文件
        system_includes = [i for i in result.includes if i.is_system]
        assert len(system_includes) >= 3

        # 检查本地头文件
        local_includes = [i for i in result.includes if not i.is_system]
        assert len(local_includes) >= 1

    def test_parse_calculator_example(self):
        """测试解析实际的计算器示例"""
        parser = get_cpp_parser()

        # 读取实际的示例文件
        from pathlib import Path

        header_path = Path("/home/kerfs/AI-CICD-new/examples/cpp-calculator/include/calculator.h")
        if header_path.exists():
            with open(header_path, 'r') as f:
                header_code = f.read()

            result = parser.parse_code(header_code, str(header_path))

            assert len(result.classes) == 1
            calculator = result.classes[0]
            assert calculator.name == "Calculator"

            # 检查方法
            method_names = [m.name for m in calculator.methods]
            assert "add" in method_names
            assert "subtract" in method_names
            assert "multiply" in method_names
            assert "divide" in method_names
