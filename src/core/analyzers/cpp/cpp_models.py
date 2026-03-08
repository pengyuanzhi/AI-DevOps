"""
C++ 代码分析数据模型
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CppParameter:
    """C++ 函数参数"""
    name: str
    type: str
    default_value: Optional[str] = None

    def __str__(self) -> str:
        if self.default_value:
            return f"{self.type} {self.name} = {self.default_value}"
        return f"{self.type} {self.name}"


@dataclass
class CppMethodInfo:
    """C++ 方法信息"""
    name: str
    return_type: str
    parameters: List[CppParameter] = field(default_factory=list)
    is_const: bool = False
    is_static: bool = False
    is_virtual: bool = False
    is_override: bool = False
    is_constexpr: bool = False
    is_noexcept: bool = False
    access_specifier: str = "public"  # public, protected, private
    lineno: int = 0
    class_name: Optional[str] = None  # 所属类名
    is_qt_slot: bool = False  # 是否是 QT slot
    is_qt_signal: bool = False  # 是否是 QT signal

    def get_signature(self) -> str:
        """获取函数签名"""
        params = ", ".join(str(p) for p in self.parameters)
        signature = f"{self.return_type} {self.name}({params})"

        if self.is_const:
            signature += " const"
        if self.is_noexcept:
            signature += " noexcept"
        if self.is_override:
            signature += " override"

        return signature

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "return_type": self.return_type,
            "parameters": [p.__dict__ for p in self.parameters],
            "is_const": self.is_const,
            "is_static": self.is_static,
            "is_virtual": self.is_virtual,
            "is_override": self.is_override,
            "is_constexpr": self.is_constexpr,
            "is_noexcept": self.is_noexcept,
            "access_specifier": self.access_specifier,
            "lineno": self.lineno,
            "class_name": self.class_name,
            "is_qt_slot": self.is_qt_slot,
            "is_qt_signal": self.is_qt_signal,
        }


@dataclass
class CppMemberVariable:
    """C++ 成员变量"""
    name: str
    type: str
    is_static: bool = False
    is_const: bool = False
    is_mutable: bool = False
    access_specifier: str = "private"
    default_value: Optional[str] = None
    lineno: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "type": self.type,
            "is_static": self.is_static,
            "is_const": self.is_const,
            "is_mutable": self.is_mutable,
            "access_specifier": self.access_specifier,
            "default_value": self.default_value,
            "lineno": self.lineno,
        }


@dataclass
class CppClassInfo:
    """C++ 类信息"""
    name: str
    namespace: str = ""
    bases: List[str] = field(default_factory=list)
    methods: List[CppMethodInfo] = field(default_factory=list)
    member_variables: List[CppMemberVariable] = field(default_factory=list)
    is_struct: bool = False
    is_class: bool = True
    is_template: bool = False
    template_parameters: List[str] = field(default_factory=list)
    lineno: int = 0
    end_lineno: int = 0

    # QT 特定
    is_qobject: bool = False  # 是否继承 QObject
    has_q_object_macro: bool = False  # 是否有 Q_OBJECT 宏
    is_qwidget: bool = False  # 是否继承 QWidget
    is_qdialog: bool = False  # 是否继承 QDialog

    @property
    def public_methods(self) -> List[CppMethodInfo]:
        """获取公共方法"""
        return [m for m in self.methods if m.access_specifier == "public"]

    @property
    def private_methods(self) -> List[CppMethodInfo]:
        """获取私有方法"""
        return [m for m in self.methods if m.access_specifier == "private"]

    @property
    def protected_methods(self) -> List[CppMethodInfo]:
        """获取保护方法"""
        return [m for m in self.methods if m.access_specifier == "protected"]

    @property
    def slots(self) -> List[CppMethodInfo]:
        """获取 QT slots"""
        return [m for m in self.methods if m.is_qt_slot]

    @property
    def signals(self) -> List[CppMethodInfo]:
        """获取 QT signals"""
        return [m for m in self.methods if m.is_qt_signal]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "namespace": self.namespace,
            "bases": self.bases,
            "methods": [m.to_dict() for m in self.methods],
            "member_variables": [v.to_dict() for v in self.member_variables],
            "is_struct": self.is_struct,
            "is_class": self.is_class,
            "is_template": self.is_template,
            "template_parameters": self.template_parameters,
            "lineno": self.lineno,
            "end_lineno": self.end_lineno,
            "is_qobject": self.is_qobject,
            "has_q_object_macro": self.has_q_object_macro,
            "is_qwidget": self.is_widget,
            "is_qdialog": self.is_dialog,
        }


@dataclass
class CppFunctionInfo:
    """C++ 自由函数信息"""
    name: str
    return_type: str
    parameters: List[CppParameter] = field(default_factory=list)
    is_constexpr: bool = False
    is_inline: bool = False
    is_static: bool = False
    is_noexcept: bool = False
    lineno: int = 0
    namespace: str = ""

    def get_signature(self) -> str:
        """获取函数签名"""
        params = ", ".join(str(p) for p in self.parameters)
        signature = f"{self.return_type} {self.name}({params})"

        if self.is_constexpr:
            signature = f"constexpr {signature}"
        if self.is_inline:
            signature = f"inline {signature}"
        if self.is_static:
            signature = f"static {signature}"
        if self.is_noexcept:
            signature += " noexcept"

        return signature

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "return_type": self.return_type,
            "parameters": [p.__dict__ for p in self.parameters],
            "is_constexpr": self.is_constexpr,
            "is_inline": self.is_inline,
            "is_static": self.is_static,
            "is_noexcept": self.is_noexcept,
            "lineno": self.lineno,
            "namespace": self.namespace,
        }


@dataclass
class CppIncludeInfo:
    """C++ include 信息"""
    header: str
    is_system: bool = False  # <header> vs "header"
    lineno: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "header": self.header,
            "is_system": self.is_system,
            "lineno": self.lineno,
        }


@dataclass
class CppAnalysisResult:
    """C++ 代码分析结果"""
    file_path: str
    language_version: str = "C++17"  # C++11, C++14, C++17, C++20
    classes: List[CppClassInfo] = field(default_factory=list)
    functions: List[CppFunctionInfo] = field(default_factory=list)
    includes: List[CppIncludeInfo] = field(default_factory=list)
    dependencies: set = field(default_factory=set)
    namespaces: List[str] = field(default_factory=list)

    # QT 特定
    is_qt_project: bool = False
    qt_modules: List[str] = field(default_factory=list)  # QtCore, QtGui, QtWidgets, etc.

    @property
    def total_classes(self) -> int:
        return len(self.classes)

    @property
    def total_functions(self) -> int:
        return len(self.functions)

    @property
    def total_methods(self) -> int:
        return sum(len(cls.methods) for cls in self.classes)

    def get_class_by_name(self, name: str) -> Optional[CppClassInfo]:
        """按名称获取类"""
        for cls in self.classes:
            if cls.name == name:
                return cls
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "file_path": self.file_path,
            "language_version": self.language_version,
            "total_classes": self.total_classes,
            "total_functions": self.total_functions,
            "total_methods": self.total_methods,
            "classes": [c.to_dict() for c in self.classes],
            "functions": [f.to_dict() for f in self.functions],
            "includes": [i.to_dict() for i in self.includes],
            "dependencies": list(self.dependencies),
            "namespaces": self.namespaces,
            "is_qt_project": self.is_qt_project,
            "qt_modules": self.qt_modules,
        }
