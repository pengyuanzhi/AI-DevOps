"""项目类型检测器.

自动检测项目类型、构建系统和测试框架。
"""

import re
from typing import List, Optional

from src.models.project import ProjectContext
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ProjectDetector:
    """项目类型检测器.

    根据项目文件列表自动检测项目类型和构建系统。
    """

    # 文件模式映射
    FILE_PATTERNS = {
        "cpp": [r"\.cpp$", r"\.cc$", r"\.cxx$", r"\.h$", r"\.hpp$", r"\.hxx$"],
        "python": [r"\.py$", r"requirements\.txt$", r"setup\.py$", r"pyproject\.toml$"],
        "nodejs": [r"package\.json$", r"\.js$", r"\.ts$", r"\.jsx$", r"\.tsx$"],
        "java": [r"\.java$", r"pom\.xml$", r"build\.gradle$"],
        "go": [r"\.go$", r"go\.mod$"],
        "rust": [r"\.rs$", r"Cargo\.toml$"],
    }

    # 配置文件映射
    CONFIG_FILES = {
        "cmake": [r"CMakeLists\.txt$", r"CMakeCache\.txt$"],
        "make": [r"Makefile$", r"makefile$", r"\.mk$"],
        "qmake": [r"\.pro$"],
        "npm": [r"package\.json$"],
        "maven": [r"pom\.xml$"],
        "gradle": [r"build\.gradle$", r"settings\.gradle$"],
        "cargo": [r"Cargo\.toml$"],
    }

    # 测试框架模式
    TEST_FRAMEWORK_PATTERNS = {
        "gtest": [r"#include\s*[<\"]gtest/gtest\.h", r"TEST\s*\(", r"TEST_F\s*\("],
        "catch2": [r"#include\s*[<\"]catch2\w*/catch\.h", r"#include\s*[<\"]catch\.hpp"],
        "qtest": [r"#include\s*[<\"]QTest", r"QTEST_MAIN"],
        "pytest": [r"import pytest", r"from pytest import", r"@pytest"],
        "unittest": [r"import unittest", r"from unittest import", r"class.*TestCase"],
        "jest": [r"from '@jest/globals'", r"describe\s*\(", r"test\s*\("],
    }

    # QT 特征
    QT_PATTERNS = [
        r"Q_OBJECT",
        r"#include\s*[<\"]Q",
        r"QApplication",
        r"QWidget",
        r"QMainWindow",
    ]

    def __init__(self):
        """初始化检测器."""
        self.detected_projects = {}

    async def detect_project_type(
        self, project_files: List[str], file_contents: Optional[dict] = None
    ) -> ProjectContext:
        """检测项目类型和上下文.

        Args:
            project_files: 项目文件列表
            file_contents: 可选的文件内容映射 {filename: content}

        Returns:
            项目上下文对象

        示例:
            >>> detector = ProjectDetector()
            >>> context = await detector.detect_project_type([
            ...     "CMakeLists.txt",
            ...     "src/main.cpp",
            ...     "tests/test_calc.cpp"
            ... ])
            >>> print(context.project_type)
            'cpp'
            >>> print(context.build_system)
            'cmake'
        """
        logger.info(
            "detect_project_start",
            file_count=len(project_files),
        )

        # 检测项目类型
        project_type = self._detect_project_type(project_files)

        # 检测构建系统
        build_system = self._detect_build_system(project_files)

        # 检测测试框架
        test_framework = await self._detect_test_framework(
            project_files, file_contents
        )

        # 检测是否为 QT 项目
        is_qt_project = self._is_qt_project(project_files, file_contents)

        # 如果检测到 QT，更新项目类型
        if is_qt_project and project_type == "cpp":
            project_type = "qt"

        # 构建项目上下文
        context = ProjectContext(
            project_type=project_type,
            build_system=build_system,
            test_framework=test_framework,
            files=project_files,
            config_files=self._get_config_files(project_files),
            is_qt_project=is_qt_project,
            uses_cmake=(build_system == "cmake"),
            uses_qmake=(build_system == "qmake"),
            has_tests=(test_framework is not None),
        )

        logger.info(
            "detect_project_success",
            project_type=context.project_type,
            build_system=context.build_system,
            test_framework=context.test_framework,
            is_qt_project=context.is_qt_project,
        )

        return context

    def _detect_project_type(self, files: List[str]) -> str:
        """检测项目类型.

        Args:
            files: 文件列表

        Returns:
            项目类型字符串
        """
        scores = {}

        # 根据文件扩展名评分
        for file_path in files:
            for project_type, patterns in self.FILE_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, file_path, re.IGNORECASE):
                        scores[project_type] = scores.get(project_type, 0) + 1

        # 返回得分最高的类型
        if scores:
            detected = max(scores, key=scores.get)
            logger.debug(
                "project_type_scores",
                scores=scores,
                detected=detected,
            )
            return detected

        # 默认返回 cpp
        logger.warning("no_project_type_detected_using_default")
        return "cpp"

    def _detect_build_system(self, files: List[str]) -> Optional[str]:
        """检测构建系统.

        Args:
            files: 文件列表

        Returns:
            构建系统名称，如果未检测到则返回 None
        """
        for file_path in files:
            for build_system, patterns in self.CONFIG_FILES.items():
                for pattern in patterns:
                    if re.search(pattern, file_path, re.IGNORECASE):
                        logger.debug(
                            "build_system_detected",
                            build_system=build_system,
                            config_file=file_path,
                        )
                        return build_system

        return None

    async def _detect_test_framework(
        self, files: List[str], file_contents: Optional[dict] = None
    ) -> Optional[str]:
        """检测测试框架.

        Args:
            files: 文件列表
            file_contents: 文件内容映射

        Returns:
            测试框架名称，如果未检测到则返回 None
        """
        if not file_contents:
            # 如果没有文件内容，基于文件名猜测
            test_files = [f for f in files if "test" in f.lower()]
            if test_files:
                # 默认假设 C++ 项目使用 gtest
                if any(f.endswith((".cpp", ".cc", ".cxx")) for f in test_files):
                    return "gtest"
            return None

        # 检查文件内容中的测试框架特征
        scores = {}

        for file_path, content in file_contents.items():
            # 只检查测试相关文件
            if "test" not in file_path.lower():
                continue

            for framework, patterns in self.TEST_FRAMEWORK_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, content, re.MULTILINE):
                        scores[framework] = scores.get(framework, 0) + 1

        if scores:
            detected = max(scores, key=scores.get)
            logger.debug(
                "test_framework_detected",
                framework=detected,
                scores=scores,
            )
            return detected

        return None

    def _is_qt_project(
        self, files: List[str], file_contents: Optional[dict] = None
    ) -> bool:
        """检测是否为 QT 项目.

        Args:
            files: 文件列表
            file_contents: 文件内容

        Returns:
            是否为 QT 项目
        """
        # 检查配置文件
        for file_path in files:
            if re.search(r"\.pro$", file_path, re.IGNORECASE):
                return True

        # 如果有文件内容，检查 QT 特征
        if file_contents:
            for content in file_contents.values():
                for pattern in self.QT_PATTERNS:
                    if re.search(pattern, content):
                        logger.debug("qt_pattern_detected", pattern=pattern)
                        return True

        return False

    def _get_config_files(self, files: List[str]) -> List[str]:
        """获取配置文件列表.

        Args:
            files: 文件列表

        Returns:
            配置文件列表
        """
        config_files = []

        config_patterns = []
        for patterns in self.CONFIG_FILES.values():
            config_patterns.extend(patterns)

        for file_path in files:
            for pattern in config_patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    config_files.append(file_path)
                    break

        return config_files

    def get_include_paths(self, source_files: List[str]) -> List[str]:
        """从源文件列表推断 include 路径.

        Args:
            source_files: 源文件列表

        Returns:
            可能的 include 路径列表
        """
        include_paths = set()

        for file_path in source_files:
            # 提取目录路径
            parts = file_path.split("/")
            if len(parts) > 1:
                # 添加各级目录
                for i in range(1, len(parts)):
                    include_paths.add("/".join(parts[:i]))

        return sorted(include_paths)

    def get_test_directories(self, files: List[str]) -> List[str]:
        """从文件列表推断测试目录.

        Args:
            files: 文件列表

        Returns:
            测试目录列表
        """
        test_dirs = set()

        for file_path in files:
            if "test" in file_path.lower():
                parts = file_path.split("/")
                # 找到包含 test 的目录
                for i, part in enumerate(parts):
                    if "test" in part.lower():
                        test_dirs.add("/".join(parts[: i + 1]))
                        break

        return sorted(test_dirs)
