"""
Test Executor Service

Handles discovery, execution, and reporting of automated tests.
Supports Qt Test framework with coverage analysis.
"""
import asyncio
import json
import os
import re
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import time
import xml.etree.ElementTree as ET

from ....core.logging.logger import get_logger
from ....services.websocket.manager import manager


logger = get_logger(__name__)


class TestStatus(str, Enum):
    """Test status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class TestFramework(str, Enum):
    """Supported test frameworks"""
    QT_TEST = "qt_test"
    GTEST = "gtest"
    CATCH2 = "catch2"
    AUTO = "auto"


@dataclass
class TestCase:
    """Test case data"""
    name: str
    suite: str
    file_path: str
    line_number: int
    test_type: str = "unit"  # unit, integration, ui
    is_flaky: bool = False
    avg_duration: float = 0.0


@dataclass
class TestResult:
    """Test execution result"""
    test_case: TestCase
    status: TestStatus
    duration: float = 0.0
    output: str = ""
    error_message: str = ""
    stack_trace: str = ""
    coverage_lines: Optional[float] = None
    coverage_functions: Optional[float] = None
    coverage_branches: Optional[float] = None


@dataclass
class TestSuiteResult:
    """Test suite execution result"""
    suite_name: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration: float
    results: List[TestResult] = field(default_factory=list)


class TestDiscoveryService:
    """Test discovery service"""

    async def discover_tests(
        self,
        project_path: str,
        framework: TestFramework = TestFramework.AUTO
    ) -> List[TestCase]:
        """
        Discover all tests in the project

        Args:
            project_path: Path to project directory
            framework: Test framework to use

        Returns:
            List of discovered test cases
        """
        test_cases = []

        if framework == TestFramework.AUTO:
            framework = await self._detect_framework(project_path)

        if framework == TestFramework.QT_TEST:
            test_cases = await self._discover_qt_tests(project_path)
        elif framework == TestFramework.GTEST:
            test_cases = await self._discover_gtest_tests(project_path)
        elif framework == TestFramework.CATCH2:
            test_cases = await self._discover_catch2_tests(project_path)

        logger.info(f"Discovered {len(test_cases)} tests using {framework.value}")
        return test_cases

    async def _detect_framework(self, project_path: str) -> TestFramework:
        """Auto-detect test framework"""
        project_path = Path(project_path)

        # Check for Qt Test
        qt_test_files = list(project_path.rglob("*test*.cpp"))
        for file in qt_test_files:
            content = file.read_text()
            if "#include <QtTest>" in content or "#include <QTest>" in content:
                return TestFramework.QT_TEST

        # Check for GTest
        gtest_files = list(project_path.rglob("*test*.cpp"))
        for file in gtest_files:
            content = file.read_text()
            if "#include <gtest/" in content or "#include <gmock/" in content:
                return TestFramework.GTEST

        # Check for Catch2
        catch2_files = list(project_path.rglob("*test*.cpp"))
        for file in catch2_files:
            content = file.read_text()
            if "#include <catch2/" in content:
                return TestFramework.CATCH2

        # Default to Qt Test
        return TestFramework.QT_TEST

    async def _discover_qt_tests(self, project_path: str) -> List[TestCase]:
        """Discover Qt Test cases"""
        test_cases = []
        project_path = Path(project_path)

        # Find test files
        test_files = list(project_path.rglob("tst_*.cpp")) + list(project_path.rglob("*test*.cpp"))

        for test_file in test_files:
            content = test_file.read_text()

            # Extract test class names
            class_pattern = r'class\s+(\w+)\s*:\s*public\s+QObject'
            matches = re.finditer(class_pattern, content)

            for match in matches:
                class_name = match.group(1)

                # Extract test methods (private slots)
                method_pattern = r'private\s+slots:\s*void\s+(\w+)\(\)'
                method_matches = re.finditer(method_pattern, content[match.end():])

                for method_match in method_matches:
                    method_name = method_match.group(1)

                    if method_name.startswith('test') or method_name.startswith('init'):
                        test_cases.append(TestCase(
                            name=f"{class_name}::{method_name}",
                            suite=class_name,
                            file_path=str(test_file.relative_to(project_path)),
                            line_number=self._find_line_number(content, method_name),
                            test_type="unit"
                        ))

        return test_cases

    async def _discover_gtest_tests(self, project_path: str) -> List[TestCase]:
        """Discover Google Test cases"""
        # This would require parsing GTest output or using --gtest_list_tests
        # For now, return placeholder
        return []

    async def _discover_catch2_tests(self, project_path: str) -> List[TestCase]:
        """Discover Catch2 tests"""
        # This would require parsing Catch2 source code
        # For now, return placeholder
        return []

    def _find_line_number(self, content: str, method_name: str) -> int:
        """Find line number of a method in source code"""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if method_name in line:
                return i + 1
        return 0


class TestExecutorService:
    """
    Test execution service with real-time streaming and coverage
    """

    def __init__(self):
        self.discovery = TestDiscoveryService()
        self.active_test_runs: Dict[str, asyncio.subprocess.Process] = {}

    async def execute_tests(
        self,
        project_path: str,
        build_dir: str,
        framework: TestFramework = TestFramework.AUTO,
        selected_tests: Optional[List[str]] = None,
        run_coverage: bool = True,
        parallel_jobs: int = 4,
        timeout: int = 300,
    ) -> TestSuiteResult:
        """
        Execute tests with coverage analysis

        Args:
            project_path: Path to project directory
            build_dir: Build directory containing test executables
            framework: Test framework
            selected_tests: Optional list of specific tests to run
            run_coverage: Whether to collect code coverage
            parallel_jobs: Number of parallel test jobs
            timeout: Test timeout in seconds

        Returns:
            TestSuiteResult with all test results
        """
        start_time = time.time()

        try:
            # Discover tests
            all_tests = await self.discovery.discover_tests(project_path, framework)

            # Filter tests if selection provided
            tests_to_run = all_tests
            if selected_tests:
                tests_to_run = [t for t in all_tests if t.name in selected_tests]

            logger.info(f"Running {len(tests_to_run)} tests (coverage: {run_coverage})")

            # Find test executables
            test_executables = await self._find_test_executables(Path(build_dir))

            if not test_executables:
                return TestSuiteResult(
                    suite_name="all",
                    total_tests=0,
                    passed=0,
                    failed=0,
                    skipped=0,
                    duration=0.0
                )

            # Execute tests
            results = []
            total_passed = 0
            total_failed = 0

            for executable in test_executables:
                executable_results = await self._run_test_executable(
                    executable=executable,
                    framework=framework,
                    run_coverage=run_coverage,
                    timeout=timeout
                )

                results.extend(executable_results)
                total_passed += sum(1 for r in executable_results if r.status == TestStatus.PASSED)
                total_failed += sum(1 for r in executable_results if r.status == TestStatus.FAILED)

            duration = time.time() - start_time

            suite_result = TestSuiteResult(
                suite_name="all",
                total_tests=len(tests_to_run),
                passed=total_passed,
                failed=total_failed,
                skipped=0,
                duration=duration,
                results=results
            )

            # Generate coverage report if enabled
            if run_coverage:
                await self._generate_coverage_report(project_path, build_dir)

            return suite_result

        except Exception as e:
            logger.error(f"Test execution error: {str(e)}")
            raise

    async def _find_test_executables(self, build_dir: Path) -> List[Path]:
        """Find test executables in build directory"""
        executables = []

        # Common patterns for test executables
        patterns = ["tst_*", "*test*", "test_*"]

        for pattern in patterns:
            executables.extend(build_dir.rglob(pattern))

        # Filter for executable files
        executables = [e for e in executables if e.is_file() and os.access(e, os.X_OK)]

        return executables

    async def _run_test_executable(
        self,
        executable: Path,
        framework: TestFramework,
        run_coverage: bool,
        timeout: int
    ) -> List[TestResult]:
        """Run a single test executable"""
        results = []

        try:
            # Build command
            cmd = [str(executable)]

            if framework == TestFramework.QT_TEST:
                # Qt Test: Run with XML output
                cmd.extend(["-xml", "-o", f"/tmp/{executable.name}.xml"])

            # Run with coverage if enabled
            if run_coverage:
                # Use lcov for coverage (Linux)
                cmd = ["lcov", "--zero-counts", "--directory", "."]
                subprocess.run(cmd, check=False, capture_output=True)

                cmd = ["lcov", "--capture", "--directory", ".", "--output-file", "coverage.info"]
                subprocess.run(cmd, check=False, capture_output=True)

                # Run actual test
                test_cmd = [str(executable)]
                if framework == TestFramework.QT_TEST:
                    test_cmd = [str(executable), "-xml"]

                process = await asyncio.create_subprocess_exec(
                    *test_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    raise TimeoutError(f"Test timeout after {timeout}s")

                # Parse results
                if framework == TestFramework.QT_TEST:
                    results = await self._parse_qt_test_results(
                        executable.name,
                        f"/tmp/{executable.name}.xml",
                        stdout.decode('utf-8', errors='ignore'),
                        stderr.decode('utf-8', errors='ignore')
                    )

                # Generate coverage report
                cmd = ["genhtml", "coverage.info", "--output-directory", "coverage"]
                subprocess.run(cmd, check=False, capture_output=True)

            else:
                # Run without coverage
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    raise TimeoutError(f"Test timeout after {timeout}s")

                # Parse results
                if framework == TestFramework.QT_TEST:
                    results = await self._parse_qt_test_results(
                        executable.name,
                        f"/tmp/{executable.name}.xml",
                        stdout.decode('utf-8', errors='ignore'),
                        stderr.decode('utf-8', errors='ignore')
                    )

        except Exception as e:
            logger.error(f"Error running test executable {executable}: {str(e)}")
            # Create a failed result for this executable
            results = [TestResult(
                test_case=TestCase(
                    name=executable.name,
                    suite="unknown",
                    file_path=str(executable),
                    line_number=0
                ),
                status=TestStatus.FAILED,
                error_message=str(e)
            )]

        return results

    async def _parse_qt_test_results(
        self,
        executable_name: str,
        xml_file: str,
        stdout: str,
        stderr: str
    ) -> List[TestResult]:
        """Parse Qt Test XML results"""
        results = []

        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            for test_element in root.findall('TestFunction'):
                test_name = test_element.get('name')
                duration = float(test_element.get('duration', 0))

                # Check if test passed
                incident = test_element.find('Incident')
                if incident is not None:
                    status = TestStatus.FAILED
                    error_message = incident.get('description', '')
                    file = incident.get('file', '')
                    line = incident.get('line', '0')
                else:
                    status = TestStatus.PASSED
                    error_message = ''
                    file = ''
                    line = '0'

                results.append(TestResult(
                    test_case=TestCase(
                        name=test_name,
                        suite=executable_name,
                        file_path=file,
                        line_number=int(line),
                        test_type="unit"
                    ),
                    status=status,
                    duration=duration,
                    error_message=error_message,
                    output=stdout + stderr
                ))

        except Exception as e:
            logger.error(f"Error parsing Qt Test results: {str(e)}")

        return results

    async def _generate_coverage_report(
        self,
        project_path: str,
        build_dir: str
    ):
        """Generate code coverage report"""
        # Parse coverage.info
        coverage_file = Path(build_dir) / "coverage.info"

        if not coverage_file.exists():
            logger.warning("Coverage file not found")
            return

        # Generate HTML report
        output_dir = Path(build_dir) / "coverage"
        output_dir.mkdir(exist_ok=True)

        try:
            subprocess.run([
                "genhtml",
                str(coverage_file),
                "--output-directory",
                str(output_dir)
            ], check=True, capture_output=True)

            logger.info(f"Coverage report generated: {output_dir}")

        except subprocess.CalledProcessError as e:
            logger.error(f"Error generating coverage report: {e.stderr.decode()}")

    async def run_test_selection(
        self,
        project_path: str,
        build_dir: str,
        selected_test_ids: List[str],
        run_coverage: bool = False
    ) -> TestSuiteResult:
        """
        Run only selected tests (for intelligent test selection)

        Args:
            project_path: Path to project
            build_dir: Build directory
            selected_test_ids: List of test IDs to run
            run_coverage: Whether to collect coverage

        Returns:
            TestSuiteResult
        """
        return await self.execute_tests(
            project_path=project_path,
            build_dir=build_dir,
            selected_tests=selected_test_ids,
            run_coverage=run_coverage
        )


# Singleton instance
test_executor_service = TestExecutorService()
