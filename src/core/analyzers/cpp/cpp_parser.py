"""
C++ 代码解析器（简化版）

使用正则表达式和启发式方法解析 C++ 代码。
适用于 MVP 阶段，生产环境建议使用 tree-sitter-cpp 或 libclang。
"""

import re
from pathlib import Path
from typing import List, Optional

from src.core.analyzers.cpp import (
    CppAnalysisResult,
    CppClassInfo,
    CppFunctionInfo,
    CppMethodInfo,
    CppMemberVariable,
    CppParameter,
    CppIncludeInfo,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SimpleCppParser:
    """简化的 C++ 代码解析器"""

    def __init__(self):
        """初始化解析器"""
        # C++ 关键字
        self.access_specifiers = ["public", "protected", "private"]
        self.qualifiers = ["const", "static", "virtual", "override", "constexpr", "noexcept", "inline"]

        # QT 相关
        self.qt_base_classes = ["QObject", "QWidget", "QDialog", "QMainWindow"]
        self.qt_modules_map = {
            "QObject": "QtCore",
            "QWidget": "QtWidgets",
            "QDialog": "QtWidgets",
            "QMainWindow": "QtWidgets",
            "QString": "QtCore",
            "QVector": "QtCore",
            "QMap": "QtCore",
        }

        logger.info("cpp_parser_initialized")

    def parse_file(self, file_path: str) -> CppAnalysisResult:
        """
        解析 C++ 文件

        Args:
            file_path: 文件路径

        Returns:
            CppAnalysisResult: 分析结果
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            return self.parse_code(content, file_path)

        except Exception as e:
            logger.error(
                "failed_to_parse_cpp_file",
                file_path=file_path,
                error=str(e),
                exc_info=True,
            )
            return CppAnalysisResult(file_path=file_path)

    def parse_code(self, source_code: str, file_path: str = "<string>") -> CppAnalysisResult:
        """
        解析 C++ 代码

        Args:
            source_code: 源代码
            file_path: 文件路径

        Returns:
            CppAnalysisResult: 分析结果
        """
        result = CppAnalysisResult(file_path=file_path)

        # 检测 C++ 版本
        result.language_version = self._detect_cpp_version(source_code)

        # 检测 QT 项目
        result.is_qt_project, result.qt_modules = self._detect_qt_project(source_code)

        # 提取 includes
        result.includes = self._extract_includes(source_code)

        # 提取命名空间
        result.namespaces = self._extract_namespaces(source_code)

        # 提取类
        result.classes = self._extract_classes(source_code)

        # 提取自由函数
        result.functions = self._extract_functions(source_code)

        # 提取依赖
        result.dependencies = self._extract_dependencies(source_code)

        logger.info(
            "cpp_code_parsed",
            file_path=file_path,
            classes_count=len(result.classes),
            functions_count=len(result.functions),
            is_qt_project=result.is_qt_project,
        )

        return result

    def _detect_cpp_version(self, source_code: str) -> str:
        """检测 C++ 版本"""
        # 检查标准库头文件
        if any(h in source_code for h in ["<concepts>", "<ranges>", "<format>", "<span>"]):
            return "C++20"
        elif any(h in source_code for h in ["<optional>", "<variant>", "<string_view>"]):
            return "C++17"
        elif any(h in source_code for h in ["<memory>", "<tuple>", "<chrono>"]):
            return "C++11"
        return "C++17"  # 默认

    def _detect_qt_project(self, source_code: str) -> tuple[bool, List[str]]:
        """检测是否是 QT 项目"""
        qt_modules = set()

        # 检查 QT include
        qt_includes = re.findall(r'#include\s*[<"]Q([A-Z][a-zA-Z]+)[>"]', source_code)
        for include in qt_includes:
            module = f"Qt{include}"
            if module in ["QtCore", "QtGui", "QtWidgets", "QtQuick", "QtCharts"]:
                qt_modules.add(module)

        # 检查 QT 宏
        has_q_object = "Q_OBJECT" in source_code
        has_q_widget = "Q_WIDGET" in source_code

        # 检查是否继承 QT 类
        for base in self.qt_base_classes:
            if f": public {base}" in source_code or f": public {base}," in source_code:
                if base == "QObject":
                    qt_modules.add("QtCore")
                elif base in ["QWidget", "QDialog", "QMainWindow"]:
                    qt_modules.add("QtWidgets")

        is_qt = len(qt_modules) > 0 or has_q_object or has_q_widget

        return is_qt, sorted(list(qt_modules))

    def _extract_includes(self, source_code: str) -> List[CppIncludeInfo]:
        """提取 include 语句"""
        includes = []

        # 匹配 #include 语句
        pattern = r'#include\s+(?P<path>[<"](?P<header>[^>"]+)[>"])'
        for match in re.finditer(pattern, source_code):
            header = match.group("header")
            path = match.group("path")
            is_system = path.startswith("<")

            # 计算行号
            lineno = source_code[:match.start()].count('\n') + 1

            includes.append(
                CppIncludeInfo(
                    header=header,
                    is_system=is_system,
                    lineno=lineno,
                )
            )

        return includes

    def _extract_namespaces(self, source_code: str) -> List[str]:
        """提取命名空间"""
        namespaces = []

        # 简单匹配 namespace 语句
        pattern = r'namespace\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        for match in re.finditer(pattern, source_code):
            namespaces.append(match.group(1))

        return list(set(namespaces))

    def _extract_classes(self, source_code: str) -> List[CppClassInfo]:
        """提取类定义"""
        classes = []

        # 匹配 class/struct 定义
        # 这是一个简化的正则，无法处理所有情况
        pattern = r'(class|struct)\s+(?P<name>[A-Z][a-zA-Z0-9_]*)\s*(?::\s*public\s+(?P<bases>[^{]+))?{'

        for match in re.finditer(pattern, source_code):
            class_type = match.group(1)
            name = match.group("name")
            bases_str = match.group("bases") or ""

            # 解析基类
            bases = [b.strip() for b in bases_str.split(',') if b.strip()] if bases_str else []

            # 获取起始位置
            start_pos = match.start()
            lineno = source_code[:start_pos].count('\n') + 1

            # 尝试找到类结束的 }
            # 这是一个简化的实现
            brace_count = 0
            end_pos = start_pos
            for i, char in enumerate(source_code[start_pos:], start=start_pos):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i
                        break

            end_lineno = source_code[:end_pos].count('\n') + 1

            # 提取类内容
            class_content = source_code[start_pos:end_pos]

            # 解析方法和成员变量
            methods, member_variables = self._extract_class_members(class_content, name)

            # 检查 QT 特性
            is_qobject = any(base in self.qt_base_classes for base in bases)
            has_q_object = "Q_OBJECT" in class_content
            is_qwidget = "QWidget" in bases_str
            is_qdialog = "QDialog" in bases_str

            class_info = CppClassInfo(
                name=name,
                bases=bases,
                methods=methods,
                member_variables=member_variables,
                is_struct=(class_type == "struct"),
                is_class=(class_type == "class"),
                lineno=lineno,
                end_lineno=end_lineno,
                is_qobject=is_qobject,
                has_q_object_macro=has_q_object,
                is_qwidget=is_qwidget,
                is_qdialog=is_qdialog,
            )

            classes.append(class_info)

        return classes

    def _extract_class_members(
        self,
        class_content: str,
        class_name: str,
    ) -> tuple[List[CppMethodInfo], List[CppMemberVariable]]:
        """提取类成员（方法和变量）"""
        methods = []
        member_variables = []

        # 当前访问修饰符
        current_access = "private"

        # 按行解析
        lines = class_content.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()

            # 跳过空行和注释
            if not line or line.startswith('//') or line.startswith('/*'):
                continue

            # 检查访问修饰符
            if line.endswith(':') and line[:-1] in self.access_specifiers:
                current_access = line[:-1]
                continue

            # 检查 QT 宏
            if line in ["Q_OBJECT", "Q_PROPERTY"]:
                continue

            # 尝试解析为方法
            method = self._parse_method_line(line, current_access, class_name)
            if method:
                methods.append(method)
                continue

            # 尝试解析为成员变量
            var = self._parse_member_variable_line(line, current_access)
            if var:
                member_variables.append(var)

        return methods, member_variables

    def _parse_method_line(
        self,
        line: str,
        access: str,
        class_name: str,
    ) -> Optional[CppMethodInfo]:
        """解析方法声明"""
        # 简化的方法声明匹配
        # 格式：[qualifiers...] return_type name(params) [const] [qualifiers...]

        # 跳过明显不是方法的行
        if not ('(' in line and ')' in line):
            return None

        # 检查是否是 QT slot/signal
        is_slot = "slots:" in line or "Q_SLOT" in line
        is_signal = "signals:" in line or "Q_SIGNAL" in line

        # 提取修饰符
        qualifiers = {
            "virtual": False,
            "static": False,
            "const": False,
            "override": False,
            "constexpr": False,
            "noexcept": False,
        }

        for q in qualifiers.keys():
            if q in line:
                qualifiers[q] = True
                line = line.replace(q, "")

        # 提取函数名和参数
        # 简化：假设格式为 "type name(params)"
        match = re.search(r'([a-zA-Z_][a-zA-Z0-9_*&\s]+)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)', line)
        if not match:
            return None

        return_type = match.group(1).strip()
        name = match.group(2).strip()
        params_str = match.group(3).strip()

        # 解析参数
        parameters = self._parse_parameters(params_str)

        return CppMethodInfo(
            name=name,
            return_type=return_type,
            parameters=parameters,
            is_const=qualifiers["const"],
            is_static=qualifiers["static"],
            is_virtual=qualifiers["virtual"],
            is_override=qualifiers["override"],
            is_constexpr=qualifiers["constexpr"],
            is_noexcept=qualifiers["noexcept"],
            access_specifier=access,
            class_name=class_name,
            is_qt_slot=is_slot,
            is_qt_signal=is_signal,
        )

    def _parse_member_variable_line(self, line: str, access: str) -> Optional[CppMemberVariable]:
        """解析成员变量声明"""
        # 简化匹配：type name [= value];
        if not line.endswith(';'):
            return None

        line = line[:-1].strip()

        # 检查修饰符
        is_static = "static" in line
        is_const = "const" in line
        is_mutable = "mutable" in line

        # 移除修饰符
        for keyword in ["static", "const", "mutable"]:
            line = line.replace(keyword, "")

        # 提取类型和名称
        parts = line.split('=')
        decl_part = parts[0].strip()
        default_value = parts[1].strip() if len(parts) > 1 else None

        # 匹配 "type name"
        match = re.match(r'([a-zA-Z_][a-zA-Z0-9_*&\s]+)\s+([a-zA-Z_][a-zA-Z0-9_]*)', decl_part)
        if not match:
            return None

        var_type = match.group(1).strip()
        name = match.group(2).strip()

        return CppMemberVariable(
            name=name,
            type=var_type,
            is_static=is_static,
            is_const=is_const,
            is_mutable=is_mutable,
            access_specifier=access,
            default_value=default_value,
        )

    def _parse_parameters(self, params_str: str) -> List[CppParameter]:
        """解析函数参数"""
        parameters = []

        if not params_str or params_str == "void":
            return parameters

        # 分割参数（简化版，不处理模板）
        for param in params_str.split(','):
            param = param.strip()
            if not param:
                continue

            # 分割类型和名称
            # 格式：type name [= default]
            parts = param.split('=')
            decl_part = parts[0].strip()
            default_value = parts[1].strip() if len(parts) > 1 else None

            # 匹配 "type name"
            match = re.match(r'([a-zA-Z_][a-zA-Z0-9_*&\s]+)\s+([a-zA-Z_][a-zA-Z0-9_]*)', decl_part)
            if match:
                param_type = match.group(1).strip()
                name = match.group(2).strip()

                parameters.append(
                    CppParameter(
                        name=name,
                        type=param_type,
                        default_value=default_value,
                    )
                )

        return parameters

    def _extract_functions(self, source_code: str) -> List[CppFunctionInfo]:
        """提取自由函数"""
        functions = []

        # 移除类定义（避免重复）
        source_without_classes = re.sub(r'(class|struct)\s+[A-Z][a-zA-Z0-9_]*\s*[^{]*{([^{}]*){', '', source_code)

        # 匹配函数定义
        # 格式：[qualifiers...] return_type name(params) { ...
        pattern = r'([a-zA-Z_][a-zA-Z0-9_*&\s]+)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)\s*(?:{|$)'

        for match in re.finditer(pattern, source_without_classes):
            return_type = match.group(1).strip()
            name = match.group(2).strip()
            params_str = match.group(3).strip()

            # 跳过明显不是函数的
            if return_type in ["class", "struct", "if", "for", "while", "return"]:
                continue

            # 获取行号
            start_pos = match.start()
            lineno = source_code[:start_pos].count('\n') + 1

            # 解析参数
            parameters = self._parse_parameters(params_str)

            functions.append(
                CppFunctionInfo(
                    name=name,
                    return_type=return_type,
                    parameters=parameters,
                    lineno=lineno,
                )
            )

        return functions

    def _extract_dependencies(self, source_code: str) -> set:
        """提取依赖关系"""
        dependencies = set()

        # 从 includes 提取
        for include in re.findall(r'#include\s*[<"]([^>"]+)[>"]', source_code):
            # 标准库
            if include.startswith('<'):
                dependencies.add(f"std:{include}")
            # 项目头文件
            else:
                dependencies.add(include)

        return dependencies


# 全局实例
_cpp_parser: Optional[SimpleCppParser] = None


def get_cpp_parser() -> SimpleCppParser:
    """获取 C++ 解析器实例（单例）"""
    global _cpp_parser
    if _cpp_parser is None:
        _cpp_parser = SimpleCppParser()
    return _cpp_parser
