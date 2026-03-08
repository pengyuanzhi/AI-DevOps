"""CI/CD configuration template models."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TemplateCategory:
    """模板分类."""

    id: str
    name: str
    description: str
    project_types: List[str] = field(default_factory=list)


@dataclass
class Template:
    """CI/CD配置模板."""

    id: str  # 模板唯一标识，如 "cpp-cmake-gtest"
    name: str  # 显示名称
    description: str  # 模板描述
    category: str  # 所属分类
    project_types: List[str] = field(default_factory=list)  # 适用的项目类型
    build_systems: List[str] = field(default_factory=list)  # 支持的构建系统
    test_frameworks: List[str] = field(default_factory=list)  # 支持的测试框架

    # 模板内容
    content: str = ""  # YAML模板内容

    # 元数据
    tags: List[str] = field(default_factory=list)  # 标签
    estimated_build_time: Optional[str] = None  # 预计构建时间
    complexity: str = "medium"  # simple, medium, complex
    requires_docker: bool = False  # 是否需要Docker

    # 优化配置
    default_optimizations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典格式."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "project_types": self.project_types,
            "build_systems": self.build_systems,
            "test_frameworks": self.test_frameworks,
            "tags": self.tags,
            "estimated_build_time": self.estimated_build_time,
            "complexity": self.complexity,
            "requires_docker": self.requires_docker,
            "default_optimizations": self.default_optimizations,
        }

    def matches_requirements(
        self,
        project_type: str,
        build_system: Optional[str] = None,
        test_framework: Optional[str] = None,
    ) -> bool:
        """检查模板是否匹配给定需求."""
        if project_type not in self.project_types:
            return False
        if build_system and build_system not in self.build_systems:
            return False
        if test_framework and test_framework not in self.test_frameworks:
            return False
        return True
