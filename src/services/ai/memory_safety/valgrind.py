"""
Valgrind integration for memory safety detection

Integrates Valgrind Memcheck to detect memory leaks, buffer overflows,
and other memory-related errors.
"""
import asyncio
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from ...build.base import BuildConfig


class MemoryErrorType(str, Enum):
    """Memory error types"""
    LEAK = "leak"
    INVALID_FREE = "invalid_free"
    MISMATCHED_FREE = "mismatched_free"
    INVALID_READ = "invalid_read"
    INVALID_WRITE = "invalid_write"
    ACCESS_BEYOND_HEAP = "access_beyond_heap"
    ACCESS_BEYOND_STACK = "access_beyond_stack"
    USE_UNINITIALIZED = "use_uninitialized"
    CONDITIONAL_JUMP_UNINITIALIZED = "conditional_jump_uninitialized"
    OVERLAPPING_SOURCE = "overlapping_source"
    SYSCALL_PARAM = "syscall_param"
    CLIENT_CHECK = "client_check"
    UNKNOWN = "unknown"


class MemoryErrorSeverity(str, Enum):
    """Memory error severity"""
    CRITICAL = "critical"  # Memory leaks, invalid frees
    HIGH = "high"  # Invalid read/write
    MEDIUM = "medium"  # Uninitialized value use
    LOW = "low"  # Minor issues
    INFO = "info"  # Informational


@dataclass
class MemoryError:
    """Memory error detected by Valgrind"""
    error_type: MemoryErrorType
    severity: MemoryErrorSeverity
    what: str  # Brief description
    auxwhat: str = ""  # Additional description
    backtrace: List[str] = None  # Call stack
    leaked_bytes: int = 0
    leaked_blocks: int = 0
    source_file: str = ""
    source_line: int = 0

    def __post_init__(self):
        if self.backtrace is None:
            self.backtrace = []


@dataclass
class ValgrindResult:
    """Valgrind analysis result"""
    success: bool
    errors: List[MemoryError]
    total_leaked_bytes: int
    total_leaked_blocks: int
    still_reachable_bytes: int
    still_reachable_blocks: int
    indirectly_lost_bytes: int
    indirectly_lost_blocks: int
    execution_time: float
    command: str


class ValgrindAnalyzer:
    """Valgrind Memcheck analyzer"""

    def __init__(self, valgrind_path: str = "valgrind"):
        self.valgrind_path = valgrind_path

    async def analyze(
        self,
        executable: str,
        args: List[str] = None,
        working_dir: str = None,
        timeout: int = 300,
        suppressions: str = None,
    ) -> ValgrindResult:
        """
        Run Valgrind Memcheck on executable

        Args:
            executable: Path to executable to analyze
            args: Command-line arguments for the executable
            working_dir: Working directory
            timeout: Timeout in seconds
            suppressions: Path to suppression file

        Returns:
            ValgrindResult with detected errors
        """
        import time

        args = args or []
        working_dir = working_dir or "."

        # Build Valgrind command
        cmd = [
            self.valgrind_path,
            "--tool=memcheck",
            "--leak-check=full",
            "--show-leak-kinds=all",
            "--track-origins=yes",
            "--xml=yes",
            "--xml-file=valgrind-results.xml",
            "--log-file=valgrind-output.log",
        ]

        if suppressions:
            cmd.extend(["--suppressions", suppressions])

        cmd.extend(["--", executable] + args)

        start_time = time.time()

        try:
            # Run Valgrind
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            execution_time = time.time() - start_time

            # Parse XML output
            xml_path = Path(working_dir) / "valgrind-results.xml"

            if xml_path.exists():
                errors = await self._parse_xml_output(xml_path)
            else:
                errors = []

            # Calculate totals
            total_leaked_bytes = sum(e.leaked_bytes for e in errors if e.error_type == MemoryErrorType.LEAK)
            total_leaked_blocks = sum(e.leaked_blocks for e in errors if e.error_type == MemoryErrorType.LEAK)

            return ValgrindResult(
                success=process.returncode == 0,
                errors=errors,
                total_leaked_bytes=total_leaked_bytes,
                total_leaked_blocks=total_leaked_blocks,
                still_reachable_bytes=0,
                still_reachable_blocks=0,
                indirectly_lost_bytes=0,
                indirectly_lost_blocks=0,
                execution_time=execution_time,
                command=" ".join(cmd),
            )

        except asyncio.TimeoutError:
            return ValgrindResult(
                success=False,
                errors=[],
                total_leaked_bytes=0,
                total_leaked_blocks=0,
                still_reachable_bytes=0,
                still_reachable_blocks=0,
                indirectly_lost_bytes=0,
                indirectly_lost_blocks=0,
                execution_time=time.time() - start_time,
                command=" ".join(cmd),
            )

    async def _parse_xml_output(self, xml_path: Path) -> List[MemoryError]:
        """Parse Valgrind XML output"""
        errors = []

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Find all errors
            for error_elem in root.findall(".//error"):
                error = self._parse_error_element(error_elem)
                if error:
                    errors.append(error)

        except Exception as e:
            print(f"Failed to parse Valgrind XML: {e}")

        return errors

    def _parse_error_element(self, error_elem: ET.Element) -> Optional[MemoryError]:
        """Parse a single error element from Valgrind XML"""
        # Get error kind
        kind_elem = error_elem.find("kind")
        if kind_elem is None:
            return None

        kind = kind_elem.text
        error_type, severity = self._map_error_kind(kind)

        # Get what happened
        what_elem = error_elem.find("what")
        what = what_elem.text if what_elem is not None else ""

        # Get additional what
        auxwhat_elem = error_elem.find("auxwhat")
        auxwhat = auxwhat_elem.text if auxwhat_elem is not None else ""

        # Get leaked bytes/blocks for memory leaks
        leaked_bytes = 0
        leaked_blocks = 0

        if error_type == MemoryErrorType.LEAK:
            for xwhat_elem in error_elem.findall("xwhat"):
                text_elem = xwhat_elem.find("text")
                if text_elem is not None and "definitely lost" in text_elem.text.lower():
                    leaked_bytes_elem = xwhat_elem.find("leakedbytes")
                    leaked_blocks_elem = xwhat_elem.find("leakedblocks")

                    if leaked_bytes_elem is not None:
                        leaked_bytes = int(leaked_bytes_elem.text)
                    if leaked_blocks_elem is not None:
                        leaked_blocks = int(leaked_blocks_elem.text)

        # Get stack trace
        backtrace = []
        for stack_elem in error_elem.findall(".//stack"):
            for frame_elem in stack_elem.findall("frame"):
                # Get source location
                source_file = ""
                source_line = 0

                ip_elem = frame_elem.find("ip")
                if ip_elem is not None:
                    source_file = ip_elem.get("objfile", "")
                    source_line = int(ip_elem.get("lineno", 0))

                # Get function name
                fn_elem = frame_elem.find("fn")
                fn_name = fn_elem.text if fn_elem is not None else "???"

                # Format frame
                if source_file and source_line > 0:
                    frame_str = f"  {fn_name} ({source_file}:{source_line})"
                else:
                    frame_str = f"  {fn_name} (???:0)"

                backtrace.append(frame_str)

        return MemoryError(
            error_type=error_type,
            severity=severity,
            what=what,
            auxwhat=auxwhat,
            backtrace=backtrace,
            leaked_bytes=leaked_bytes,
            leaked_blocks=leaked_blocks,
            source_file=source_file,
            source_line=source_line,
        )

    def _map_error_kind(self, kind: str) -> tuple[MemoryErrorType, MemoryErrorSeverity]:
        """Map Valgrind error kind to our type and severity"""
        kind_lower = kind.lower()

        if "leak" in kind_lower or "memloss" in kind_lower:
            if "definitely" in kind_lower:
                return MemoryErrorType.LEAK, MemoryErrorSeverity.CRITICAL
            elif "indirectly" in kind_lower:
                return MemoryErrorType.LEAK, MemoryErrorSeverity.MEDIUM
            else:
                return MemoryErrorType.LEAK, MemoryErrorSeverity.LOW

        elif "invalidfree" in kind_lower:
            return MemoryErrorType.INVALID_FREE, MemoryErrorSeverity.CRITICAL

        elif "mismatchedfree" in kind_lower or "invalidptr" in kind_lower:
            return MemoryErrorType.MISMATCHED_FREE, MemoryErrorSeverity.CRITICAL

        elif "invalidread" in kind_lower or "addrread" in kind_lower:
            return MemoryErrorType.INVALID_READ, MemoryErrorSeverity.HIGH

        elif "invalidwrite" in kind_lower or "addrwrite" in kind_lower:
            return MemoryErrorType.INVALID_WRITE, MemoryErrorSeverity.HIGH

        elif "jump" in kind_lower or "cond" in kind_lower:
            return MemoryErrorType.CONDITIONAL_JUMP_UNINITIALIZED, MemoryErrorSeverity.HIGH

        elif "param" in kind_lower:
            return MemoryErrorType.SYSCALL_PARAM, MemoryErrorSeverity.MEDIUM

        elif "overlap" in kind_lower:
            return MemoryErrorType.OVERLAPPING_SOURCE, MemoryErrorSeverity.MEDIUM

        else:
            return MemoryErrorType.UNKNOWN, MemoryErrorSeverity.INFO


class MemorySafetyAnalyzer:
    """High-level memory safety analyzer with AI enhancement"""

    def __init__(self):
        self.valgrind = ValgrindAnalyzer()

    async def analyze_memory_safety(
        self,
        executable: str,
        build_dir: str = ".",
        use_ai_filtering: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze memory safety of executable

        Args:
            executable: Path to executable
            build_dir: Build directory
            use_ai_filtering: Use AI to filter false positives

        Returns:
            Analysis results
        """
        # Run Valgrind
        valgrind_result = await self.valgrind.analyze(
            executable=executable,
            working_dir=build_dir,
        )

        # Filter errors using AI if enabled
        if use_ai_filtering and valgrind_result.errors:
            filtered_errors = await self._filter_with_ai(valgrind_result.errors)
        else:
            filtered_errors = valgrind_result.errors

        # Calculate score
        score = self._calculate_memory_safety_score(
            valgrind_result,
            filtered_errors,
        )

        return {
            "success": valgrind_result.success,
            "score": score,
            "total_errors": len(valgrind_result.errors),
            "filtered_errors": len(valgrind_result.errors) - len(filtered_errors),
            "errors": [self._error_to_dict(e) for e in filtered_errors],
            "summary": {
                "leaked_bytes": valgrind_result.total_leaked_bytes,
                "leaked_blocks": valgrind_result.total_leaked_blocks,
                "execution_time": valgrind_result.execution_time,
            },
        }

    async def _filter_with_ai(self, errors: List[MemoryError]) -> List[MemoryError]:
        """Use AI to filter false positives"""
        from ....core.llm.factory import get_llm_client

        llm_client = get_llm_client()

        # Format errors for AI
        errors_text = "\n\n".join([
            f"Type: {e.error_type.value}\n"
            f"Severity: {e.severity.value}\n"
            f"What: {e.what}\n"
            f"Location: {e.source_file}:{e.source_line}\n"
            f"Backtrace:\n" + "\n".join(e.backtrace[:5])  # First 5 frames
            for e in errors[:20]  # Limit to 20 errors for token efficiency
        ])

        prompt = f"""Analyze these Valgrind memory errors and identify which are likely false positives.

Consider these as false positives:
- Errors in third-party libraries
- Errors in test frameworks
- Expected memory leaks in long-running processes
- Known issues in system libraries
- Errors without clear source location

Errors:
{errors_text}

Return a JSON list of error indices (0-based) that are TRUE positives (not false positives).
Format: [0, 2, 5, ...]
Only return the JSON array, no explanation.
"""

        try:
            response = await llm_client.complete(prompt, max_tokens=500)
            import json

            # Parse indices
            true_positive_indices = json.loads(response.strip())

            # Filter errors
            return [
                e for i, e in enumerate(errors)
                if i in true_positive_indices
            ]

        except Exception:
            # If AI fails, return all errors
            return errors

    def _calculate_memory_safety_score(
        self,
        valgrind_result: ValgrindResult,
        filtered_errors: List[MemoryError],
    ) -> float:
        """Calculate memory safety score (0-100)"""
        # Start with 100
        score = 100.0

        # Deduct for critical errors
        critical_count = sum(1 for e in filtered_errors if e.severity == MemoryErrorSeverity.CRITICAL)
        score -= critical_count * 15

        # Deduct for high severity
        high_count = sum(1 for e in filtered_errors if e.severity == MemoryErrorSeverity.HIGH)
        score -= high_count * 10

        # Deduct for medium severity
        medium_count = sum(1 for e in filtered_errors if e.severity == MemoryErrorSeverity.MEDIUM)
        score -= medium_count * 5

        # Deduct for low severity
        low_count = sum(1 for e in filtered_errors if e.severity == MemoryErrorSeverity.LOW)
        score -= low_count * 2

        # Deduct for memory leaks (proportional to bytes)
        leak_mb = valgrind_result.total_leaked_bytes / (1024 * 1024)
        score -= min(leak_mb * 2, 20)  # Max 20 points for leaks

        return max(0.0, min(100.0, score))

    def _error_to_dict(self, error: MemoryError) -> Dict[str, Any]:
        """Convert MemoryError to dictionary"""
        return {
            "type": error.error_type.value,
            "severity": error.severity.value,
            "what": error.what,
            "auxwhat": error.auxwhat,
            "backtrace": error.backtrace,
            "leaked_bytes": error.leaked_bytes,
            "leaked_blocks": error.leaked_blocks,
            "source_file": error.source_file,
            "source_line": error.source_line,
        }
