"""
测试发现器

支持多种测试框架的测试用例发现：
- Qt Test
- Google Test
- Catch2
"""

import os
import re
import subprocess
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .base import TestSuite, TestCase, TestStatus
from ....core.logging.logger import get_logger

logger = get_logger(__name__)


class TestFramework(str, Enum):
    """测试框架类型"""
    QT_TEST = "qttest"
    GOOGLE_TEST = "googletest"
    CATCH2 = "catch2"
    UNKNOWN = "unknown"


@dataclass
class TestBinary:
    """测试可执行文件"""
    path: str
    framework: TestFramework
    suite_name: str = ""
    test_cases: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


class TestDiscoveryService:
    """
    测试发现服务

    自动发现项目中的测试用例，支持多种测试框架。
    """

    def __init__(self):
        self.framework_patterns = {
            TestFramework.QT_TEST: [
                "*_test",
                "*test",
                "tst_*",
            ],
            TestFramework.GOOGLE_TEST: [
                "*_gtest",
                "*_test",
            ],
            TestFramework.CATCH2: [
                "*_catch",
                "*_test",
            ],
        }

        # 测试框架检测命令
        self.detection_commands = {
            TestFramework.GOOGLE_TEST: ["--gtest_list_tests"],
            TestFramework.CATCH2: ["--list-tests"],
            TestFramework.QT_TEST: [],  # Qt Test需要特殊处理
        }

    async def discover_tests(
        self,
        build_dir: str,
        source_dir: Optional[str] = None,
        framework_filter: Optional[TestFramework] = None,
    ) -> List[TestSuite]:
        """
        发现所有测试用例

        Args:
            build_dir: 构建目录
            source_dir: 源代码目录（可选）
            framework_filter: 框架过滤（可选）

        Returns:
            测试套件列表
        """
        logger.info(
            "test_discovery_started",
            build_dir=build_dir,
            source_dir=source_dir,
            framework_filter=framework_filter,
        )

        # 1. 查找测试可执行文件
        test_binaries = await self._find_test_binaries(build_dir)

        if not test_binaries:
            logger.warning("no_test_binaries_found", build_dir=build_dir)
            return []

        # 2. 识别测试框架
        for binary in test_binaries:
            if framework_filter and binary.framework != framework_filter:
                continue

            if binary.framework == TestFramework.UNKNOWN:
                binary.framework = await self._detect_framework(binary.path)

        # 3. 过滤掉未知框架
        test_binaries = [
            b for b in test_binaries
            if b.framework != TestFramework.UNKNOWN and
            (not framework_filter or b.framework == framework_filter)
        ]

        # 4. 列出测试用例
        test_suites = []
        for binary in test_binaries:
            suites = await self._list_tests_from_binary(binary)
            test_suites.extend(suites)

        logger.info(
            "test_discovery_completed",
            total_suites=len(test_suites),
            total_tests=sum(len(s.tests) for s in test_suites),
        )

        return test_suites

    async def _find_test_binaries(self, build_dir: str) -> List[TestBinary]:
        """
        查找测试可执行文件

        Args:
            build_dir: 构建目录

        Returns:
            测试可执行文件列表
        """
        test_binaries = []
        build_path = Path(build_dir)

        if not build_path.exists():
            logger.warning("build_dir_not_exists", build_dir=build_dir)
            return []

        # 遍历构建目录查找可执行文件
        for root, dirs, files in os.walk(build_path):
            for file in files:
                file_path = Path(root) / file

                # 检查是否是可执行文件
                if not self._is_executable(file_path):
                    continue

                # 跳过某些目录
                if self._should_skip_directory(root):
                    continue

                # 尝试识别框架
                framework = self._guess_framework_from_name(file)

                test_binaries.append(
                    TestBinary(
                        path=str(file_path),
                        framework=framework,
                        suite_name=file_path.stem,
                    )
                )

        logger.debug(
            "test_binaries_found",
            count=len(test_binaries),
            build_dir=build_dir,
        )

        return test_binaries

    async def _detect_framework(self, binary_path: str) -> TestFramework:
        """
        检测测试框架类型

        Args:
            binary_path: 可执行文件路径

        Returns:
            测试框架类型
        """
        # 尝试运行 --help 或 --gtest_list_tests 等命令
        for framework, test_args in self.detection_commands.items():
            if not test_args:
                continue

            try:
                result = subprocess.run(
                    [binary_path] + test_args,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    # 检查输出是否包含框架特征
                    if self._is_framework_output(framework, result.stdout):
                        return framework

            except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                logger.debug(
                    "framework_detection_failed",
                    binary=binary_path,
                    framework=framework,
                    error=str(e),
                )
                continue

        # 默认尝试从源码分析
        return await self._detect_framework_from_source(binary_path)

    async def _detect_framework_from_source(self, binary_path: str) -> TestFramework:
        """
        从源码检测测试框架

        Args:
            binary_path: 可执行文件路径

        Returns:
            测试框架类型
        """
        # 查找对应的源文件
        binary = Path(binary_path)
        possible_sources = [
            binary.with_suffix(".cpp"),
            binary.with_suffix(".cc"),
            binary.with_suffix(".c"),
        ]

        for source in possible_sources:
            if source.exists():
                content = source.read_text()

                # 检查Qt Test
                if "#include <QtTest>" in content or "QTEST_MAIN" in content:
                    return TestFramework.QT_TEST

                # 检查Google Test
                if "#include <gtest/gtest.h>" in content or "TEST(" in content:
                    return TestFramework.GOOGLE_TEST

                # 检查Catch2
                if "#include <catch2/catch.hpp>" in content or "TEST_CASE(" in content:
                    return TestFramework.CATCH2

        return TestFramework.UNKNOWN

    async def _list_tests_from_binary(self, binary: TestBinary) -> List[TestSuite]:
        """
        从二进制文件列出测试用例

        Args:
            binary: 测试二进制文件

        Returns:
            测试套件列表
        """
        try:
            if binary.framework == TestFramework.GOOGLE_TEST:
                return await self._list_gtest_tests(binary)
            elif binary.framework == TestFramework.CATCH2:
                return await self._list_catch2_tests(binary)
            elif binary.framework == TestFramework.QT_TEST:
                return await self._list_qttest_tests(binary)
            else:
                logger.warning(
                    "unknown_framework",
                    binary=binary.path,
                    framework=binary.framework,
                )
                return []

        except Exception as e:
            logger.error(
                "list_tests_failed",
                binary=binary.path,
                error=str(e),
                exc_info=True,
            )
            return []

    async def _list_gtest_tests(self, binary: TestBinary) -> List[TestSuite]:
        """
        列出Google Test测试用例

        Args:
            binary: 测试二进制文件

        Returns:
            测试套件列表
        """
        try:
            result = await asyncio.create_subprocess_exec(
                binary.path,
                "--gtest_list_tests",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                logger.error(
                    "gtest_list_failed",
                    binary=binary.path,
                    error=stderr.decode(),
                )
                return []

            output = stdout.decode()
            return self._parse_gtest_output(output, binary.path)

        except Exception as e:
            logger.error("gtest_list_error", binary=binary.path, error=str(e))
            return []

    def _parse_gtest_output(self, output: str, binary_path: str) -> List[TestSuite]:
        """
        解析Google Test输出

        Args:
            output: gtest_list_tests输出
            binary_path: 二进制文件路径

        Returns:
            测试套件列表
        """
        test_suites = []
        current_suite = None

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue

            # 测试套件（以"  "开头但不是"    "）
            if line.startswith("  ") and not line.startswith("    "):
                suite_name = line.strip()
                current_suite = TestSuite(
                    name=suite_name,
                    tests=[],
                )
                test_suites.append(current_suite)

            # 测试用例（以"    "开头）
            elif line.startswith("    ") and current_suite:
                test_name = line.strip()
                test_case = TestCase(
                    name=f"{current_suite.name}.{test_name}",
                    suite=current_suite.name,
                    file=binary_path,
                    line=0,
                    status=TestStatus.PENDING,
                )
                current_suite.tests.append(test_case)

        return test_suites

    async def _list_catch2_tests(self, binary: TestBinary) -> List[TestSuite]:
        """
        列出Catch2测试用例

        Args:
            binary: 测试二进制文件

        Returns:
            测试套件列表
        """
        try:
            result = await asyncio.create_subprocess_exec(
                binary.path,
                "--list-tests",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                logger.error(
                    "catch2_list_failed",
                    binary=binary.path,
                    error=stderr.decode(),
                )
                return []

            output = stdout.decode()
            return self._parse_catch2_output(output, binary.path)

        except Exception as e:
            logger.error("catch2_list_error", binary=binary.path, error=str(e))
            return []

    def _parse_catch2_output(self, output: str, binary_path: str) -> List[TestSuite]:
        """
        解析Catch2输出

        Args:
            output: --list-tests输出
            binary_path: 二进制文件路径

        Returns:
            测试套件列表
        """
        test_suites = {}
        suite_pattern = re.compile(r'^([^:]+):(.+)$')

        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith("Matching") or line.startswith("test cases"):
                continue

            match = suite_pattern.match(line)
            if match:
                suite_name = match.group(1)
                test_name = match.group(2)

                if suite_name not in test_suites:
                    test_suites[suite_name] = TestSuite(
                        name=suite_name,
                        tests=[],
                    )

                test_case = TestCase(
                    name=f"{suite_name}:{test_name}",
                    suite=suite_name,
                    file=binary_path,
                    line=0,
                    status=TestStatus.PENDING,
                )
                test_suites[suite_name].tests.append(test_case)

        return list(test_suites.values())

    async def _list_qttest_tests(self, binary: TestBinary) -> List[TestSuite]:
        """
        列出Qt Test测试用例

        Qt Test没有内置的列表功能，需要从源码解析

        Args:
            binary: 测试二进制文件

        Returns:
            测试套件列表
        """
        # 尝试从源码解析
        binary_path = Path(binary.path)
        possible_sources = [
            binary_path.with_suffix(".cpp"),
            binary_path.with_suffix(".cc"),
        ]

        test_methods = []
        class_name = None

        for source in possible_sources:
            if source.exists():
                content = source.read_text()

                # 查找测试类
                class_match = re.search(r'class\s+(\w+)\s*:\s*public\s+QObject', content)
                if class_match:
                    class_name = class_match.group(1)

                # 查找私有槽测试方法
                private_slots_match = re.search(
                    r'private\s+slots:\s*((?:\s*void\s+\w+\(\);\s*)+)',
                    content
                )

                if private_slots_match:
                    slots_text = private_slots_match.group(1)
                    test_methods = re.findall(r'void\s+(\w+)\(\)', slots_text)
                    break

        if not test_methods:
            # 如果无法从源码解析，创建一个默认的测试套件
            return [
                TestSuite(
                    name=binary.suite_name,
                    tests=[
                        TestCase(
                            name=f"{binary.suite_name}.default",
                            suite=binary.suite_name,
                            file=binary.path,
                            line=0,
                            status=TestStatus.PENDING,
                        )
                    ],
                )
            ]

        # 创建测试套件
        suite_name = class_name or binary.suite_name
        tests = []

        for method in test_methods:
            test_case = TestCase(
                name=f"{suite_name}.{method}",
                suite=suite_name,
                file=binary.path,
                line=0,
                status=TestStatus.PENDING,
            )
            tests.append(test_case)

        return [
            TestSuite(
                name=suite_name,
                tests=tests,
            )
        ]

    def _is_executable(self, file_path: Path) -> bool:
        """检查是否是可执行文件"""
        # 在Unix系统上检查执行权限
        if os.access(file_path, os.X_OK):
            return True

        # 在Windows上检查扩展名
        if file_path.suffix in [".exe", ".com"]:
            return True

        return False

    def _should_skip_directory(self, dir_path: str) -> bool:
        """检查是否应该跳过该目录"""
        skip_patterns = [
            "CMakeFiles",
            ".git",
            ".svn",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
        ]

        for pattern in skip_patterns:
            if pattern in dir_path:
                return True

        return False

    def _guess_framework_from_name(self, file_path: Path) -> TestFramework:
        """从文件名猜测测试框架"""
        name = file_path.name.lower()

        # Qt Test 特征
        if name.startswith("tst_"):
            return TestFramework.QT_TEST

        # Google Test 特征
        if "_gtest" in name or "google" in name:
            return TestFramework.GOOGLE_TEST

        # Catch2 特征
        if "_catch" in name or "catch" in name:
            return TestFramework.CATCH2

        # 通用测试文件
        if "_test" in name or name.endswith("test"):
            return TestFramework.GOOGLE_TEST  # 默认使用Google Test

        return TestFramework.UNKNOWN

    def _is_framework_output(self, framework: TestFramework, output: str) -> bool:
        """检查输出是否符合框架特征"""
        if framework == TestFramework.GOOGLE_TEST:
            return "GoogleTest" in output or "gtest" in output.lower()
        elif framework == TestFramework.CATCH2:
            return "Catch" in output or "test case" in output.lower()
        return False


# 全局单例
test_discovery_service = TestDiscoveryService()
