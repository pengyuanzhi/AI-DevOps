"""
Catch2执行器

支持Catch2测试框架的测试执行
"""

import os
import asyncio
import re
import json
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


class Catch2Executor(BaseTestExecutor):
    """Catch2执行器"""

    def __init__(self):
        super().__init__()

    def get_test_type(self) -> str:
        return "catch2"

    async def discover(self) -> List[TestSuite]:
        """
        发现Catch2测试用例

        使用 --list-tests 选项列出所有测试
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
        运行Catch2测试

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

                # 添加测试过滤器
                if config.test_filter:
                    cmd.append(config.test_filter)

                # 添加Reporter选项（使用JSON格式以便解析）
                json_output = Path(config.build_dir) / f"{exe.name}_results.json"
                cmd.append(f"--reporter=json")
                cmd.append(f"--out:{json_output}")

                # 添加其他选项
                cmd.append("--use-colour")  # 使用颜色输出
                cmd.append("--durations")  # 显示执行时间
                cmd.append("yes")  # 显示所有测试的执行时间

                result = await self._run_command(
                    cmd,
                    cwd=config.build_dir,
                    env=config.env_vars,
                    timeout=config.timeout,
                )

                stdout_parts.append(result.stdout)
                stderr_parts.append(result.stderr)

                # 解析测试结果
                if json_output.exists():
                    suite = self._parse_json_output(json_output)
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
            logger.error("catch2_execution_error", error=str(e), exc_info=True)
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
                if "test" in exe.name.lower() or "catch" in exe.name.lower():
                    test_executables.append(exe)

        return test_executables

    async def _list_tests_from_binary(self, exe: Path) -> List[TestSuite]:
        """从二进制文件列出测试"""
        try:
            result = await asyncio.create_subprocess_exec(
                str(exe),
                "--list-tests",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                logger.error("catch2_list_failed", binary=exe.name, error=stderr.decode())
                return []

            output = stdout.decode()
            return self._parse_catch2_list_output(output, exe.name)

        except Exception as e:
            logger.error("catch2_list_error", binary=exe.name, error=str(e))
            return []

    def _parse_catch2_list_output(self, output: str, binary_name: str) -> List[TestSuite]:
        """解析--list-tests输出"""
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
                    file=binary_name,
                    line=0,
                    status=TestStatus.PENDING,
                )
                test_suites[suite_name].tests.append(test_case)

        return list(test_suites.values())

    def _parse_json_output(self, json_file: Path) -> Optional[TestSuite]:
        """解析Catch2 JSON输出"""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            all_tests = []

            # Catch2 JSON格式
            for test_data in data.get('tests', []):
                suite_name = test_data.get('suite', 'default')
                test_name = test_data.get('name', '')

                status = TestStatus.PASSED
                if test_data.get('status') == 'FAILED':
                    status = TestStatus.FAILED
                elif test_data.get('status') == 'SKIPPED':
                    status = TestStatus.SKIPPED

                error_msg = ""
                if 'error_message' in test_data:
                    error_msg = test_data['error_message']

                test = TestCase(
                    name=f"{suite_name}:{test_name}",
                    suite=suite_name,
                    file=test_data.get('file', ''),
                    line=int(test_data.get('line', 0)),
                    status=status,
                    error_message=error_msg,
                    duration_ms=test_data.get('duration_ms', 0),
                )

                all_tests.append(test)

            if all_tests:
                return TestSuite(
                    name=data.get('name', 'tests'),
                    tests=all_tests,
                )

            return None

        except Exception as e:
            logger.error("catch2_json_parse_error", error=str(e))
            return None

    def _parse_test_output(self, suite_name: str, stdout: str) -> Optional[TestSuite]:
        """
        解析Catch2文本输出

        Catch2输出格式：
        test.cpp:10: TEST_CASEsuite_name:test_name
          FAILED:
          explicitly with message:
        test.cpp:15: TEST_CASEsuite_name:test_name
          PASSED
        """
        tests = []

        for line in stdout.splitlines():
            line = line.strip()

            # 测试用例
            test_match = re.match(r'.+:\d+:\s*TEST_CASE\s+\[([^\]]+)\]\s+([^\s]+)', line)
            if test_match:
                suite, test_name = test_match.groups()
                test_name_full = f"{suite}:{test_name}"
                continue

            # PASSED标记
            if "PASSED" in line:
                # 查找前面的测试名称
                if test_match:
                    suite, test_name = test_match.groups()
                    test_name_full = f"{suite}:{test_name}"
                    tests.append(TestCase(
                        name=test_name_full,
                        suite=suite,
                        file="",
                        line=0,
                        status=TestStatus.PASSED,
                    ))
                    test_match = None

            # FAILED标记
            elif "FAILED" in line:
                if test_match:
                    suite, test_name = test_match.groups()
                    test_name_full = f"{suite}:{test_name}"
                    tests.append(TestCase(
                        name=test_name_full,
                        suite=suite,
                        file="",
                        line=0,
                        status=TestStatus.FAILED,
                    ))
                    test_match = None

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
