"""
Qt Test执行器

支持Qt Test框架的测试执行
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


class QtTestExecutor(BaseTestExecutor):
    """Qt Test执行器"""
    
    def __init__(self):
        super().__init__()
    
    def get_test_type(self) -> str:
        return "qttest"
    
    async def discover(self) -> List[TestSuite]:
        """
        发现Qt测试用例
        
        通过查找可执行文件并运行它们来发现测试
        """
        if not self.config:
            return []
        
        suites = []
        build_path = Path(self.config.build_dir)
        
        # 查找测试可执行文件
        test_executables = []
        for exe in build_path.rglob("*"):
            if exe.is_file() and os.access(exe, os.X_OK):
                if "test" in exe.name.lower():
                    test_executables.append(exe)
        
        # 对每个测试可执行文件，获取测试列表
        for exe in test_executables:
            # 运行测试以获取测试列表（Qt Test的 -datatags 选项）
            result = await self._run_command(
                [str(exe), "-datatags"],
                cwd=self.config.build_dir,
            )
            
            suite = self._parse_test_list(exe.name, result.stdout)
            if suite:
                suites.append(suite)
        
        return suites
    
    async def run(self, config: TestConfig) -> TestResult:
        """
        运行Qt测试
        
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
            test_executables = []
            
            for exe in build_path.rglob("*"):
                if exe.is_file() and os.access(exe, os.X_OK):
                    if "test" in exe.name.lower():
                        test_executables.append(exe)
            
            # 运行每个测试
            for exe in test_executables:
                cmd = [str(exe)]
                
                # 添加XML输出选项
                if config.enable_coverage:
                    # Qt Test支持XML输出
                    pass
                
                result = await self._run_command(
                    cmd,
                    cwd=config.build_dir,
                    env=config.env_vars,
                    timeout=config.timeout,
                )
                
                stdout_parts.append(result.stdout)
                stderr_parts.append(result.stderr)
                
                # 解析测试结果
                suite = self._parse_test_output(exe.name, result.stdout, result.stderr)
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
    
    def _parse_test_list(self, suite_name: str, output: str) -> Optional[TestSuite]:
        """
        解析测试列表输出
        
        Qt Test的-datatags输出格式：
        TestCase::testFunction1
        TestCase::testFunction2
        """
        tests = []
        
        for line in output.splitlines():
            line = line.strip()
            if "::" in line:
                parts = line.split("::")
                if len(parts) == 2:
                    test_case, test_func = parts
                    tests.append(TestCase(
                        name=test_func,
                        suite=test_case,
                        file="",
                        line=0,
                    ))
        
        if tests:
            return TestSuite(
                name=suite_name,
                tests=tests,
            )
        
        return None
    
    def _parse_test_output(
        self,
        suite_name: str,
        stdout: str,
        stderr: str,
    ) -> Optional[TestSuite]:
        """
        解析Qt Test输出
        
        Qt Test输出格式：
        ********* Start testing of TestSuite *********
        Config: Using QtTest library 5.15.2
        PASS   : TestSuite::testCase1()
        FAIL!  : TestSuite::testCase2()
           Loc: [Unknown file](0)
           Error: Assertion failed
        PASS   : TestSuite::testCase3()
        Totals: 3 passed, 1 failed, 0 skipped, 0 blacklisted
        ********* Finished testing of TestSuite *********
        """
        tests = []
        
        lines = (stdout + "\n" + stderr).splitlines()
        
        current_test = None
        for line in lines:
            line = line.strip()
            
            # 检测测试结果行
            # PASS: TestSuite::testCase()
            pass_match = re.match(r'PASS\s*:\s*([^:]+)::([^\s]+)\(\)', line)
            if pass_match:
                suite, test_name = pass_match.groups()
                tests.append(TestCase(
                    name=test_name,
                    suite=suite,
                    file="",
                    line=0,
                    status=TestStatus.PASSED,
                ))
                continue
            
            # FAIL: TestSuite::testCase()
            fail_match = re.match(r'FAIL!\s*:\s*([^:]+)::([^\s]+)\(\)', line)
            if fail_match:
                suite, test_name = fail_match.groups()
                current_test = TestCase(
                    name=test_name,
                    suite=suite,
                    file="",
                    line=0,
                    status=TestStatus.FAILED,
                )
                tests.append(current_test)
                continue
            
            # 错误信息
            if line.startswith("Error:") and current_test:
                current_test.error_message = line.replace("Error:", "").strip()
            
            # 跳过的测试
            skip_match = re.match(r'SKIP\s*:\s*([^:]+)::([^\s]+)\(\)', line)
            if skip_match:
                suite, test_name = skip_match.groups()
                tests.append(TestCase(
                    name=test_name,
                    suite=suite,
                    file="",
                    line=0,
                    status=TestStatus.SKIPPED,
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
            # gcov输出格式：
            # File 'test.cpp'
            # Lines executed:80.00% of 100
            
            coverage_data = {}
            for line in result.stdout.splitlines():
                if "Lines executed:" in line:
                    match = re.search(r'Lines executed:(\d+\.\d+)%', line)
                    if match:
                        coverage_percent = float(match.group(1))
                        return coverage_percent
            
            return None
            
        except Exception as e:
            print(f"Coverage collection error: {e}")
            return None
