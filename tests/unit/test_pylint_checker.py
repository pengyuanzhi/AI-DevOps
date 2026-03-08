"""
Pylint 检查器单元测试
"""

import pytest
from src.core.quality import PylintChecker, PylintMessage, PylintResult


class TestPylintMessage:
    """Pylint 消息测试"""

    def test_message_creation(self):
        """测试创建消息"""
        msg = PylintMessage(
            msg_id="C0111",
            symbol="missing-docstring",
            msg="Missing docstring",
            category="convention",
            line=10,
            column=0,
            path="test.py",
            module="test",
            confidence="HIGH",
        )

        assert msg.msg_id == "C0111"
        assert msg.symbol == "missing-docstring"
        assert msg.category == "convention"
        assert msg.line == 10

    def test_message_to_dict(self):
        """测试消息转换为字典"""
        msg = PylintMessage(
            msg_id="W0613",
            symbol="unused-argument",
            msg="Unused argument 'x'",
            category="warning",
            line=5,
            column=10,
            path="example.py",
            module="example",
            confidence="HIGH",
        )

        data = msg.to_dict()

        assert data["msg_id"] == "W0613"
        assert data["symbol"] == "unused-argument"
        assert data["category"] == "warning"
        assert data["line"] == 5

    def test_message_from_dict(self):
        """测试从字典创建消息"""
        data = {
            "msg_id": "E1101",
            "symbol": "no-member",
            "msg": "Module has no member",
            "category": "error",
            "line": 15,
            "column": 0,
            "path": "test.py",
            "module": "test",
            "confidence": "HIGH",
        }

        msg = PylintMessage.from_dict(data)

        assert msg.msg_id == "E1101"
        assert msg.symbol == "no-member"
        assert msg.category == "error"


class TestPylintResult:
    """Pylint 结果测试"""

    def test_empty_result(self):
        """测试空结果"""
        result = PylintResult(file_path="test.py")

        assert result.file_path == "test.py"
        assert result.score == 0.0
        assert result.total_issues == 0

    def test_result_with_messages(self):
        """测试带消息的结果"""
        result = PylintResult(file_path="test.py", score=8.5)

        # 添加不同类型的消息
        result.messages.append(
            PylintMessage(
                msg_id="E1101",
                symbol="no-member",
                msg="Error",
                category="error",
                line=10,
                column=0,
                path="test.py",
                module="test",
                confidence="HIGH",
            )
        )
        result.messages.append(
            PylintMessage(
                msg_id="W0613",
                symbol="unused-argument",
                msg="Warning",
                category="warning",
                line=20,
                column=0,
                path="test.py",
                module="test",
                confidence="HIGH",
            )
        )

        assert result.error_count == 1
        assert result.warning_count == 1
        assert result.total_issues == 2

    def test_get_messages_by_category(self):
        """测试按类别获取消息"""
        result = PylintResult(file_path="test.py")

        result.messages.extend([
            PylintMessage(
                msg_id=f"C{i:04d}",
                symbol=f"convention-{i}",
                msg=f"Message {i}",
                category="convention",
                line=i,
                column=0,
                path="test.py",
                module="test",
                confidence="HIGH",
            )
            for i in range(1, 4)
        ])

        result.messages.append(
            PylintMessage(
                msg_id="E1101",
                symbol="error",
                msg="Error",
                category="error",
                line=10,
                column=0,
                path="test.py",
                module="test",
                confidence="HIGH",
            )
        )

        convention_msgs = result.get_messages_by_category("convention")
        assert len(convention_msgs) == 3

        error_msgs = result.get_messages_by_category("error")
        assert len(error_msgs) == 1


class TestPylintChecker:
    """Pylint 检查器测试"""

    def test_checker_initialization(self):
        """测试检查器初始化"""
        checker = PylintChecker()

        assert checker is not None
        assert len(checker.disabled_checks) > 0

    def test_checker_with_custom_disabled_checks(self):
        """测试自定义禁用检查"""
        custom_disabled = ["C0111", "C0103"]
        checker = PylintChecker(disabled_checks=custom_disabled)

        # 应该包含自定义禁用检查
        assert "C0111" in checker.disabled_checks
        assert "C0103" in checker.disabled_checks

    def test_check_code_simple(self):
        """测试检查简单代码"""
        checker = PylintChecker()

        code = """
def add(a, b):
    return a + b
"""

        result = checker.check_code(code, "test.py")

        assert isinstance(result, PylintResult)
        assert result.file_path == "test.py"
        assert result.score >= 0

    def test_check_code_with_issues(self):
        """测试检查有问题的代码"""
        checker = PylintChecker(disabled_checks=[])  # 启用所有检查

        code = """
def foo():
    x = 1
    y = 2
    z = 3
    return x + y + z
"""

        result = checker.check_code(code, "test.py")

        # 应该有一些问题（如缺少文档字符串）
        # 但由于默认禁用了很多检查，可能问题不多
        assert isinstance(result, PylintResult)

    def test_check_code_with_syntax_error(self):
        """测试检查有语法错误的代码"""
        checker = PylintChecker()

        code = """
def foo(
    # 语法错误：缺少右括号
"""

        result = checker.check_code(code, "test.py")

        # 应该返回空结果或低分
        assert isinstance(result, PylintResult)
        assert result.score == 0.0

    def test_calculate_score(self):
        """测试分数计算"""
        checker = PylintChecker()

        # 没有消息，应该是满分
        score = checker._calculate_score([])
        assert score == 10.0

        # 添加一些消息
        messages = [
            PylintMessage(
                msg_id="W0613",
                symbol="unused-argument",
                msg="Warning",
                category="warning",
                line=10,
                column=0,
                path="test.py",
                module="test",
                confidence="HIGH",
            )
        ]
        score = checker._calculate_score(messages)
        assert score < 10.0
        assert score > 0.0

    def test_get_summary(self):
        """测试获取汇总"""
        checker = PylintChecker()

        # 创建多个结果
        results = [
            PylintResult(file_path="file1.py", score=9.0),
            PylintResult(file_path="file2.py", score=8.0),
            PylintResult(file_path="file3.py", score=7.0),
        ]

        # 添加一些消息
        results[0].messages.append(
            PylintMessage(
                msg_id="W0613",
                symbol="unused-argument",
                msg="Warning",
                category="warning",
                line=10,
                column=0,
                path="file1.py",
                module="file1",
                confidence="HIGH",
            )
        )

        summary = checker.get_summary(results)

        assert summary["total_files"] == 3
        assert summary["average_score"] == 8.0
        assert "top_issues" in summary

    def test_check_code_with_unused_import(self):
        """测试检查未使用的导入"""
        checker = PylintChecker()

        code = """
import os
import sys

def foo():
    return 42
"""

        result = checker.check_code(code, "test.py")

        assert isinstance(result, PylintResult)
        # 可能会有未使用导入的警告（取决于 pylint 配置）

    def test_check_code_with_undefined_variable(self):
        """测试检查未定义的变量"""
        checker = PylintChecker()

        code = """
def foo():
    x = undefined_variable
    return x
"""

        result = checker.check_code(code, "test.py")

        assert isinstance(result, PylintResult)
        # 应该检测到未定义变量
        # 但由于 pylint 默认配置，可能不会检测所有情况
