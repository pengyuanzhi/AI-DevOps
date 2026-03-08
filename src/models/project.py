"""Project context and detection models."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ProjectContext:
    """项目上下文信息.

    包含项目类型、构建系统、依赖关系等信息。
    """

    project_type: str  # cpp, qt, python, nodejs, etc.
    build_system: Optional[str] = None  # cmake, make, qmake, npm, etc.
    test_framework: Optional[str] = None  # gtest, catch2, pytest, etc.

    # 项目文件
    files: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)  # CMakeLists.txt, package.json, etc.

    # 依赖信息
    dependencies: List[str] = field(default_factory=list)
    include_paths: List[str] = field(default_factory=list)

    # 项目结构
    has_tests: bool = False
    test_directories: List[str] = field(default_factory=list)
    source_directories: List[str] = field(default_factory=list)

    # 特殊标识
    is_qt_project: bool = False
    uses_cmake: bool = False
    uses_qmake: bool = False

    # 元数据
    name: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典格式."""
        return {
            "project_type": self.project_type,
            "build_system": self.build_system,
            "test_framework": self.test_framework,
            "files": self.files,
            "config_files": self.config_files,
            "dependencies": self.dependencies,
            "include_paths": self.include_paths,
            "has_tests": self.has_tests,
            "test_directories": self.test_directories,
            "source_directories": self.source_directories,
            "is_qt_project": self.is_qt_project,
            "uses_cmake": self.uses_cmake,
            "uses_qmake": self.uses_qmake,
            "name": self.name,
            "description": self.description,
        }


@dataclass
class DependencyGraph:
    """依赖关系图.

    用于分析代码变更影响范围和智能测试选择。
    """

    nodes: List[str] = field(default_factory=list)  # 文件节点
    edges: Dict[str, List[str]] = field(default_factory=dict)  # 依赖关系: file -> [depends_on...]
    impact_map: Dict[str, List[str]] = field(default_factory=dict)  # 影响映射: file -> [affects...]

    def get_affected_files(self, changed_files: List[str]) -> List[str]:
        """获取受影响的文件列表."""
        affected = set(changed_files)
        to_process = list(changed_files)

        while to_process:
            file = to_process.pop(0)
            if file in self.impact_map:
                for affected_file in self.impact_map[file]:
                    if affected_file not in affected:
                        affected.add(affected_file)
                        to_process.append(affected_file)

        return list(affected)

    def get_affected_tests(
        self, changed_files: List[str], test_files: List[str]
    ) -> List[str]:
        """获取受影响的测试文件."""
        affected_source = self.get_affected_files(changed_files)
        affected_tests = []

        for test_file in test_files:
            # 检查测试文件是否依赖了受影响的源文件
            if test_file in self.edges:
                for dependency in self.edges[test_file]:
                    if dependency in affected_source:
                        affected_tests.append(test_file)
                        break

        return affected_tests
