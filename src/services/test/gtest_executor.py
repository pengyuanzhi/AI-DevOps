"""
Google Test执行器

支持Google Test框架的测试执行
"""

import os
import asyncio
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .base import (
    BaseTestExecutor,
    TestConfig,
    TestResult,
    TestStatus,
    TestSuite,
    TestCase,
)

from ....core.logging.logger import get_logger

logger = get_logger(__name__)


class GTestExecutor(BaseTestExecutor):
    """Google Test执行器"""

    def __init__(self):
        super().__init__()

    def get_test_type(self) -> str:
        return "googletest"

    async def discover(self) -> List[TestSuite]:
        """
        发现Google Test测试用例

        使用 --gtest_list_tests 选项列出所有测试
        """
        if not self.config:
            return []

        suites = []
        build_path = Path(self.config.build_dir)

        # 查找测试可执行文件
        test_executables = await self._find_test_binaries(build_path)

        # 对每个测试可执行文件，获取测试列表
        for exe in test_executables:
            test_suites = await self._list_tests_from_binary(exe)
            suites.extend(test_suites)

        return suites

    async def run(self, config: TestConfig) -> TestResult:
        """
        运行Google Test测试

        Args:
            config: 测试配置

        Returns:
            测试结果
        """
        self.config = config
        self.status = TestStatus.RUNNING

        started_at = datetime.now()
        suites = []
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0
        failed_cases = []

        stdout_parts = []
        stderr_parts = []

        try:
            # 查找测试可执行文件
            build_path = Path(config.build_dir)
            test_executables = await self._find_test_binaries(build_path)

            # 运行每个测试
            for exe in test_executables:
                cmd = [str(exe)]

                # 添加gtest选项
                if config.test_filter:
                    cmd.append(f"--gtest_filter={config.test_filter}")

                # 添加XML输出
                xml_output = Path(config.build_dir) / "test_results.xml"
                cmd.append(f"--gtest_output=xml:{xml_output}")

                result = await self._run_command(
                    cmd,
                    cwd=config.build_dir,
                    env=config.env_vars,
                    timeout=config.timeout,
                )

                stdout_parts.append(result.stdout)
                stderr_parts.append(result.stderr)

                # 解析测试结果
                if xml_output.exists():
                    suite = self._parse_xml_output(xml_output)
                else:
                    suite = self._parse_test_output(exe.name, result.stdout)

                if suite:
                    suite.calculate_stats()
                    suites.append(suite)

                    total_tests += suite.total
                    passed_tests += suite.passed
                    failed_tests += suite.failed
                    skipped_tests += suite.skipped

                    # 收集失败的测试
                    for test in suite.tests:
                        if test.status == TestStatus.FAILED:
                            failed_cases.append(test)

            finished_at = datetime.now()
            duration = (finished_at - started_at).total_seconds()

            # 计算覆盖率（如果启用）
            coverage_percent = None
            if config.enable_coverage:
                coverage_percent = await self._collect_coverage(config)

            # 确定总体状态
            status = TestStatus.PASSED if failed_tests == 0 else TestStatus.FAILED

            self.status = status

            return TestResult(
                status=status,
                suites=suites,
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                skipped_tests=skipped_tests,
                coverage_percent=coverage_percent,
                duration_seconds=duration,
                stdout="\n".join(stdout_parts),
                stderr="\n".join(stderr_parts),
                started_at=started_at,
                finished_at=finished_at,
                failed_test_cases=failed_cases,
            )

        except asyncio.TimeoutError:
            self.status = TestStatus.TIMEOUT
            return TestResult(
                status=TestStatus.TIMEOUT,
                suites=suites,
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                skipped_tests=skipped_tests,
                duration_seconds=(datetime.now() - started_at).total_seconds(),
                stdout="\n".join(stdout_parts),
                stderr="\n".join(stderr_parts),
                started_at=started_at,
                finished_at=datetime.now(),
            )

        except Exception as e:
            logger.error("gtest_execution_error", error=str(e), exc_info=True)
            self.status = TestStatus.FAILED
            return TestResult(
                status=TestStatus.FAILED,
                suites=suites,
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                skipped_tests=skipped_tests,
                duration_seconds=(datetime.now() - started_at).total_seconds(),
                stdout="\n".join(stdout_parts),
                stderr="\n".join(stderr_parts),
                started_at=started_at,
                finished_at=datetime.now(),
            )

    async def _find_test_binaries(self, build_path: Path) -> List[Path]:
        """查找测试可执行文件"""
        test_executables = []

        for exe in build_path.rglob("*"):
            if exe.is_file() and os.access(exe, os.X_OK):
                if "test" in exe.name.lower():
                    test_executables.append(exe)

        return test_executables

    async def _list_tests_from_binary(self, exe: Path) -> List[TestSuite]:
        """从二进制文件列出测试"""
        try:
            result = await asyncio.create_subprocess_exec(
                str(exe),
                "--gtest_list_tests",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                logger.error("gtest_list_failed", binary=exe.name, error=stderr.decode())
                return []

            output = stdout.decode()
            return self._parse_gtest_list_output(output, exe.name)

        except Exception as e:
            logger.error("gtest_list_error", binary=exe.name, error=str(e))
            return []

    def _parse_gtest_list_output(self, output: str, binary_name: str) -> List[TestSuite]:
        """解析gtest_list_tests输出"""
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
                    file=binary_name,
                    line=0,
                    status=TestStatus.PENDING,
                )
                current_suite.tests.append(test_case)

        return test_suites

    def _parse_xml_output(self, xml_file: Path) -> Optional[TestSuite]:
        """解析Google Test XML输出"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            all_tests = []

            for suite_elem in root.findall('testsuite'):
                suite_name = suite_elem.get('name', '')

                for test_elem in suite_elem.findall('testcase'):
                    test_name = test_elem.get('name', '')
                    full_name = f"{suite_name}.{test_name}"

                    # 检查失败
                    failure = test_elem.find('failure')
                    status = TestStatus.FAILED if failure is not None else TestStatus.PASSED

                    error_msg = ""
                    if failure is not None:
                        error_msg = failure.get('message', '')

                    test = TestCase(
                        name=full_name,
                        suite=suite_name,
                        file=test_elem.get('file', ''),
                        line=int(test_elem.get('line', 0)),
                        status=status,
                        error_message=error_msg,
                    )

                    all_tests.append(test)

            if all_tests:
                return TestSuite(
                    name=root.get('name', 'tests'),
                    tests=all_tests,
                )

            return None

        except Exception as e:
            logger.error("xml_parse_error", error=str(e))
            return None

    def _parse_test_output(self, suite_name: str, stdout: str) -> Optional[TestSuite]:
        """
        解析Google Test文本输出

        Google Test输出格式：
        [==========] Running 3 tests from 1 test suite.
        [----------] 1 test from TestSuite
        [ RUN      ] TestSuite.testName
        [       OK ] TestSuite.testName (100 ms)
        [  FAILED  ] TestSuite.testName (50 ms)
        """
        tests = []

        for line in stdout.splitlines():
            line = line.strip()

            # 运行测试
            run_match = re.match(r'\[\s*RUN\s*\]\s+([^.\s]+)\.([^\s]+)', line)
            if run_match:
                continue

            # 测试通过
            ok_match = re.match(r'\[\s*OK\s*\]\s+([^.\s]+)\.([^\s]+)\s+\((\d+)\s*ms\)', line)
            if ok_match:
                suite, test_name, duration = ok_match.groups()
                tests.append(TestCase(
                    name=f"{suite}.{test_name}",
                    suite=suite,
                    file="",
                    line=0,
                    status=TestStatus.PASSED,
                    duration_ms=float(duration),
                ))
                continue

            # 测试失败
            failed_match = re.match(r'\[\s*FAILED\s*\]\s+([^.\s]+)\.([^\s]+)\s+\((\d+)\s*ms\)', line)
            if failed_match:
                suite, test_name, duration = failed_match.groups()
                tests.append(TestCase(
                    name=f"{suite}.{test_name}",
                    suite=suite,
                    file="",
                    line=0,
                    status=TestStatus.FAILED,
                    duration_ms=float(duration),
                ))

        if tests:
            return TestSuite(
                name=suite_name,
                tests=tests,
            )

        return None

    async def _run_command(
        self,
        cmd: List[str],
        cwd: str,
        env: dict = None,
        timeout: int = None,
    ):
        """运行命令"""
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            env=process_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise

        return type('Result', (), {
            'returncode': process.returncode,
            'stdout': stdout.decode('utf-8', errors='replace'),
            'stderr': stderr.decode('utf-8', errors='replace'),
        })()

    async def _collect_coverage(self, config: TestConfig) -> Optional[float]:
        """
        收集代码覆盖率

        使用gcov/lcov收集覆盖率数据
        """
        try:
            # 检查是否有gcov数据
            build_path = Path(config.build_dir)
            gcov_files = list(build_path.rglob("*.gcda"))

            if not gcov_files:
                return None

            # 运行gcov
            result = await self._run_command(
                ["gcov", "-r", "-o", config.build_dir],
                cwd=config.build_dir,
            )

            # 解析gcov输出获取覆盖率
            coverage_data = {}
            for line in result.stdout.splitlines():
                if "Lines executed:" in line:
                    match = re.search(r'Lines executed:(\d+\.\d+)%', line)
                    if match:
                        coverage_percent = float(match.group(1))
                        return coverage_percent

            return None

        except Exception as e:
            logger.error("coverage_collection_error", error=str(e))
            return None
