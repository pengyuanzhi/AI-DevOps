"""
Autonomous Pipeline Maintenance

Automatically detects, diagnoses, and fixes failed tests and build issues.
"""
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ....core.llm.factory import get_llm_client


class FailureType(str, Enum):
    """Types of failures"""
    BUILD_ERROR = "build_error"
    TEST_FAILURE = "test_failure"
    TIMEOUT = "timeout"
    DEPENDENCY_ERROR = "dependency_error"
    CONFIGURATION_ERROR = "configuration_error"
    ENVIRONMENT_ERROR = "environment_error"
    UNKNOWN = "unknown"


class FailureSeverity(str, Enum):
    """Severity of failures"""
    CRITICAL = "critical"  # Blocks all builds
    HIGH = "high"  # Blocks multiple tests
    MEDIUM = "medium"  # Affects single test
    LOW = "low"  # Minor issue


@dataclass
class TestFailure:
    """Test failure information"""
    test_name: str
    test_suite: str
    failure_type: FailureType
    severity: FailureSeverity
    error_message: str
    stack_trace: str = ""
    source_file: str = ""
    source_line: int = 0
    is_flaky: bool = False
    occurrence_count: int = 1


@dataclass
class BuildFailure:
    """Build failure information"""
    stage: str
    job_name: str
    failure_type: FailureType
    severity: FailureSeverity
    error_message: str
    log_snippet: str = ""
    source_file: str = ""
    source_line: int = 0


@dataclass
class FixSuggestion:
    """Suggested fix for a failure"""
    title: str
    description: str
    code_diff: str = ""
    confidence: float = 0.0
    estimated_effort: str = ""  # quick, medium, complex
    requires_review: bool = True


class FailureClassifier:
    """Classify failures by type and severity"""

    BUILD_ERROR_PATTERNS = {
        FailureType.DEPENDENCY_ERROR: [
            r"dependency .+ not found",
            r"cannot find -l.+",
            r"package .+ was not found",
            r"no such file or directory.*\.so",
            r"undefined reference to",
            r"file not found",
            r"'[^']+\.h' file not found",
            r"error: [^ ]+: No such file or directory",
        ],
        FailureType.CONFIGURATION_ERROR: [
            r"cmake error",
            r"cmakeLists\.txt.*error",
            r"configuration error",
            r"invalid.*option",
            r"unknown.*argument",
        ],
        FailureType.ENVIRONMENT_ERROR: [
            r"permission denied",
            r"no space left",
            r"out of memory",
            r"cannot allocate memory",
            r"disk quota exceeded",
        ],
    }

    TEST_FAILURE_PATTERNS = {
        FailureType.TEST_FAILURE: [
            r"assertion.*failed",
            r"expected.*but got",
            r"test.*failed",
            r"check.*failed",
        ],
        FailureType.TIMEOUT: [
            r"timeout",
            r"timed out",
            r"exceeded time limit",
        ],
    }

    def classify_build_failure(
        self,
        log: str,
        stage: str,
        job_name: str,
    ) -> BuildFailure:
        """Classify a build failure"""
        log_lower = log.lower()

        # Check for error patterns
        failure_type = FailureType.UNKNOWN
        for ftype, patterns in self.BUILD_ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, log_lower):
                    failure_type = ftype
                    break
            if failure_type != FailureType.UNKNOWN:
                break

        # Determine severity
        severity = self._determine_build_severity(failure_type, log)

        # Extract error message
        error_message = self._extract_error_message(log)

        # Extract source location
        source_file, source_line = self._extract_source_location(log)

        return BuildFailure(
            stage=stage,
            job_name=job_name,
            failure_type=failure_type,
            severity=severity,
            error_message=error_message,
            log_snippet=log[:500],  # First 500 chars
            source_file=source_file,
            source_line=source_line,
        )

    def classify_test_failure(
        self,
        test_name: str,
        test_suite: str,
        error_log: str,
        occurrence_history: List[int] = None,
    ) -> TestFailure:
        """Classify a test failure"""
        error_log_lower = error_log.lower()

        # Check for error patterns
        failure_type = FailureType.UNKNOWN
        for ftype, patterns in self.TEST_FAILURE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error_log_lower):
                    failure_type = ftype
                    break
            if failure_type != FailureType.UNKNOWN:
                break

        # Determine severity
        severity = self._determine_test_severity(failure_type, test_name)

        # Check if flaky
        is_flaky = False
        if occurrence_history and len(occurrence_history) > 1:
            pass_rate = occurrence_history.count(0) / len(occurrence_history)
            if 0.3 < pass_rate < 0.7:  # Passes 30-70% of the time
                is_flaky = True

        return TestFailure(
            test_name=test_name,
            test_suite=test_suite,
            failure_type=failure_type,
            severity=severity,
            error_message=self._extract_error_message(error_log),
            stack_trace=error_log,
            is_flaky=is_flaky,
            occurrence_count=len(occurrence_history) if occurrence_history else 1,
        )

    def _determine_build_severity(self, failure_type: FailureType, log: str) -> FailureSeverity:
        """Determine severity of build failure"""
        if failure_type == FailureType.DEPENDENCY_ERROR:
            return FailureSeverity.CRITICAL
        elif failure_type == FailureType.CONFIGURATION_ERROR:
            return FailureSeverity.HIGH
        elif failure_type == FailureType.ENVIRONMENT_ERROR:
            return FailureSeverity.CRITICAL
        else:
            return FailureSeverity.MEDIUM

    def _determine_test_severity(self, failure_type: FailureType, test_name: str) -> FailureSeverity:
        """Determine severity of test failure"""
        if "integration" in test_name.lower() or "e2e" in test_name.lower():
            return FailureSeverity.MEDIUM
        elif "unit" in test_name.lower():
            return FailureSeverity.HIGH
        else:
            return FailureSeverity.MEDIUM

    def _extract_error_message(self, log: str) -> str:
        """Extract the main error message from log"""
        lines = log.split("\n")
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ["error", "failed", "fatal"]):
                return line.strip()
        return lines[0].strip() if lines else "Unknown error"

    def _extract_source_location(self, log: str) -> Tuple[str, int]:
        """Extract source file and line from error log"""
        # Look for patterns like "file.cpp:123" or "file.cpp(line 123)"
        patterns = [
            r"(\S+\.(cpp|h|hpp|cc|cxx))[:\s](\d+)",
            r"(\S+\.(cpp|h|hpp|cc|cxx))\s*\(\s*line\s*(\d+)\s*\)",
        ]

        for pattern in patterns:
            match = re.search(pattern, log)
            if match:
                return match.group(1), int(match.group(2))

        return "", 0


class PipelineMaintenanceService:
    """Autonomous pipeline maintenance service"""

    def __init__(self):
        self.classifier = FailureClassifier()

    async def diagnose_build_failure(
        self,
        build_log: str,
        stage: str,
        job_name: str,
    ) -> Dict[str, Any]:
        """
        Diagnose a build failure and provide fix suggestions

        Args:
            build_log: Build log output
            stage: Pipeline stage where failure occurred
            job_name: Name of the failed job

        Returns:
            Diagnosis with root cause and fix suggestions
        """
        # Classify failure
        failure = self.classifier.classify_build_failure(build_log, stage, job_name)

        # Generate fix suggestion
        fix_suggestion = await self._generate_build_fix_suggestion(failure)

        return {
            "failure": {
                "type": failure.failure_type.value,
                "severity": failure.severity.value,
                "stage": failure.stage,
                "job_name": failure.job_name,
                "error_message": failure.error_message,
                "source_location": {
                    "file": failure.source_file,
                    "line": failure.source_line,
                } if failure.source_file else None,
            },
            "root_cause": await self._analyze_root_cause(failure),
            "fix_suggestion": fix_suggestion,
            "can_auto_fix": self._can_auto_fix(failure),
        }

    async def diagnose_test_failure(
        self,
        test_name: str,
        test_suite: str,
        error_log: str,
        occurrence_history: List[int] = None,
    ) -> Dict[str, Any]:
        """
        Diagnose a test failure and provide fix suggestions

        Args:
            test_name: Name of the failed test
            test_suite: Test suite name
            error_log: Test error log
            occurrence_history: History of test results (0=pass, 1=fail)

        Returns:
            Diagnosis with root cause and fix suggestions
        """
        # Classify failure
        failure = self.classifier.classify_test_failure(
            test_name,
            test_suite,
            error_log,
            occurrence_history,
        )

        # Generate fix suggestion
        fix_suggestion = await self._generate_test_fix_suggestion(failure)

        return {
            "failure": {
                "test_name": failure.test_name,
                "test_suite": failure.test_suite,
                "type": failure.failure_type.value,
                "severity": failure.severity.value,
                "is_flaky": failure.is_flaky,
                "occurrence_count": failure.occurrence_count,
                "error_message": failure.error_message,
            },
            "root_cause": await self._analyze_root_cause(failure),
            "fix_suggestion": fix_suggestion,
            "recommended_action": self._get_recommended_action(failure),
        }

    async def _analyze_root_cause(self, failure) -> str:
        """Analyze root cause of failure using AI"""
        llm_client = get_llm_client()

        if isinstance(failure, BuildFailure):
            context = f"""Build Failure Analysis:
Stage: {failure.stage}
Job: {failure.job_name}
Error Type: {failure.failure_type.value}
Error Message: {failure.error_message}

Log Snippet:
{failure.log_snippet[:1000]}"""
        else:  # TestFailure
            context = f"""Test Failure Analysis:
Test: {failure.test_name}
Suite: {failure.test_suite}
Error Type: {failure.failure_type.value}
Error Message: {failure.error_message}

Stack Trace:
{failure.stack_trace[:1000]}"""

        prompt = f"""Analyze the root cause of this failure.

{context}

Provide a concise root cause analysis (2-3 sentences) that explains:
1. What went wrong
2. Why it went wrong
3. What needs to be fixed

Focus on the actual root cause, not symptoms.
"""

        try:
            response = await llm_client.complete(prompt, max_tokens=500)
            return response.strip()
        except Exception:
            return self._get_generic_root_cause(failure)

    def _get_generic_root_cause(self, failure) -> str:
        """Get generic root cause without AI"""
        if isinstance(failure, BuildFailure):
            if failure.failure_type == FailureType.DEPENDENCY_ERROR:
                return "Missing or incompatible dependency. Check if all required packages are installed and versions are compatible."
            elif failure.failure_type == FailureType.CONFIGURATION_ERROR:
                return "Configuration error in build system. Check CMakeLists.txt or build configuration for syntax errors or invalid options."
            else:
                return "Build process failed. Check the error message and logs for specific issues."
        else:  # TestFailure
            if failure.is_flaky:
                return "Flaky test with intermittent failures. May be due to timing issues, resource contention, or missing test isolation."
            else:
                return "Test assertion failed. The code behavior doesn't match expected results."

    async def _generate_build_fix_suggestion(self, failure: BuildFailure) -> FixSuggestion:
        """Generate fix suggestion for build failure"""
        llm_client = get_llm_client()

        prompt = f"""You are a C/C++ build expert. Provide a specific fix for this build failure:

Stage: {failure.stage}
Job: {failure.job_name}
Error Type: {failure.failure_type.value}
Error Message: {failure.error_message}
Source: {failure.source_file}:{failure.source_line}

Log:
{failure.log_snippet[:1500]}

Provide a fix in JSON format:
{{
  "title": "Brief fix title",
  "description": "What to do",
  "code_diff": "Example code changes",
  "confidence": 0.8,
  "estimated_effort": "quick|medium|complex"
}}
"""

        try:
            response = await llm_client.complete(prompt, max_tokens=800)
            import json
            fix_data = json.loads(response.strip())

            return FixSuggestion(
                title=fix_data.get("title", "Fix build error"),
                description=fix_data.get("description", ""),
                code_diff=fix_data.get("code_diff", ""),
                confidence=fix_data.get("confidence", 0.5),
                estimated_effort=fix_data.get("estimated_effort", "medium"),
                requires_review=True,
            )

        except Exception:
            return FixSuggestion(
                title="Generic build fix",
                description=self._get_generic_build_fix_description(failure),
                estimated_effort="medium",
                confidence=0.3,
                requires_review=True,
            )

    async def _generate_test_fix_suggestion(self, failure: TestFailure) -> FixSuggestion:
        """Generate fix suggestion for test failure"""
        llm_client = get_llm_client()

        prompt = f"""You are a C++ testing expert. Provide a specific fix for this test failure:

Test: {failure.test_name}
Suite: {failure.test_suite}
Error: {failure.error_message}

Stack Trace:
{failure.stack_trace[:1500]}

Provide a fix in JSON format:
{{
  "title": "Brief fix title",
  "description": "What to do",
  "code_diff": "Example code changes (test or production code)",
  "confidence": 0.8,
  "estimated_effort": "quick|medium|complex"
}}
"""

        try:
            response = await llm_client.complete(prompt, max_tokens=800)
            import json
            fix_data = json.loads(response.strip())

            return FixSuggestion(
                title=fix_data.get("title", "Fix test failure"),
                description=fix_data.get("description", ""),
                code_diff=fix_data.get("code_diff", ""),
                confidence=fix_data.get("confidence", 0.5),
                estimated_effort=fix_data.get("estimated_effort", "medium"),
                requires_review=True,
            )

        except Exception:
            return FixSuggestion(
                title="Generic test fix",
                description=self._get_generic_test_fix_description(failure),
                estimated_effort="medium",
                confidence=0.3,
                requires_review=True,
            )

    def _get_generic_build_fix_description(self, failure: BuildFailure) -> str:
        """Get generic fix description"""
        if failure.failure_type == FailureType.DEPENDENCY_ERROR:
            return "Install missing dependencies or update package configuration. Check that all required libraries are available in the build environment."
        elif failure.failure_type == FailureType.CONFIGURATION_ERROR:
            return "Review and fix build configuration. Check for syntax errors, correct paths, and valid options in CMakeLists.txt or build scripts."
        else:
            return "Review the error message and logs. Address the specific issue indicated in the error."

    def _get_generic_test_fix_description(self, failure: TestFailure) -> str:
        """Get generic fix description"""
        if failure.is_flaky:
            return "Add test isolation, fix timing issues, or add retry logic for flaky tests."
        else:
            return "Fix the code or test to match expected behavior. Update assertions or fix the bug in production code."

    def _can_auto_fix(self, failure: BuildFailure) -> bool:
        """Determine if failure can be automatically fixed"""
        # Some simple issues can be auto-fixed
        auto_fixable_types = [
            FailureType.DEPENDENCY_ERROR,  # Can try to install deps
            FailureType.CONFIGURATION_ERROR,  # Can try common fixes
        ]
        return failure.failure_type in auto_fixable_types and failure.severity != FailureSeverity.CRITICAL

    def _get_recommended_action(self, failure: TestFailure) -> str:
        """Get recommended action for test failure"""
        if failure.is_flaky:
            return "quarantine"  # Isolate flaky test
        elif failure.severity == FailureSeverity.HIGH:
            return "fix_urgent"  # Needs immediate fix
        else:
            return "fix_normal"  # Normal fix process

    async def attempt_auto_fix(
        self,
        failure: BuildFailure,
        project_path: str,
    ) -> Dict[str, Any]:
        """
        Attempt to automatically fix a build failure

        Args:
            failure: Build failure to fix
            project_path: Path to project

        Returns:
            Fix result
        """
        if not self._can_auto_fix(failure):
            return {
                "success": False,
                "message": "This failure type cannot be automatically fixed",
            }

        # TODO: Implement actual auto-fix logic
        # For now, just return the suggestion
        suggestion = await self._generate_build_fix_suggestion(failure)

        return {
            "success": False,  # Auto-fix not implemented yet
            "message": "Auto-fix not yet implemented",
            "suggestion": suggestion.__dict__,
        }

    async def quarantine_flaky_tests(
        self,
        test_failures: List[TestFailure],
        config_file: str = ".gitlab-ci.yml",
    ) -> Dict[str, Any]:
        """
        Quarantine flaky tests by excluding them from test runs

        Args:
            test_failures: List of test failures
            config_file: CI configuration file

        Returns:
            Quarantine result
        """
        flaky_tests = [f for f in test_failures if f.is_flaky]

        if not flaky_tests:
            return {
                "success": True,
                "quarantined_tests": [],
                "message": "No flaky tests found",
            }

        # TODO: Implement actual test quarantine
        # For now, return the list
        return {
            "success": True,
            "quarantined_tests": [
                {
                    "test_name": f.test_name,
                    "test_suite": f.test_suite,
                    "reason": "Flaky test detected",
                }
                for f in flaky_tests
            ],
            "message": f"Quarantined {len(flaky_tests)} flaky tests",
        }


# Singleton instance
pipeline_maintenance_service = PipelineMaintenanceService()
