"""
Clang-tidy 静态分析检查器
"""

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.quality.cpp.cpp_models import (
    CppIssue,
    ClangTidyIssue,
    StaticAnalysisResult,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ClangTidyConfig:
    """Clang-tidy 配置"""
    checks: List[str] = field(default_factory=list)
    warnings_as_errors: List[str] = field(default_factory=list)
    header_filter: str = ".*"
    extra_args: List[str] = field(default_factory=list)

    def to_command_line_args(self) -> List[str]:
        """转换为命令行参数"""
        args = []

        if self.checks:
            checks_str = ",".join(self.checks)
            args.append(f"-checks={checks_str}")

        if self.warnings_as_errors:
            warnings_str = ",".join(self.warnings_as_errors)
            args.append(f"-warnings-as-errors={warnings_str}")

        args.append(f"-header-filter={self.header_filter}")

        if self.extra_args:
            args.extend(self.extra_args)

        return args


class ClangTidyChecker:
    """Clang-tidy 静态分析检查器"""

    # 默认启用的检查
    DEFAULT_CHECKS = [
        # 现代 C++ 建议
        "modernize-*",
        "modernize-use-nullptr",
        "modernize-use-override",
        "modernize-use-auto",
        "modernize-avoid-c-arrays",
        "modernize-use-enum-class",

        # C++ 核心指南
        "cppcoreguidelines-*",
        "-cppcoreguidelines-avoid-magic-numbers",  # 太严格
        "-cppcoreguidelines-pro-bounds-pointer-arithmetic",  # C++ 代码常见
        "-cppcoreguidelines-owning-memory",  # C++ 代码常见

        # 性能
        "performance-*",
        "-performance-no-int-to-ptr",  # 某些情况下可以接受

        # 可读性
        "readability-*",
        "-readability-magic-numbers",  # 太严格
        "-readability-function-cognitive-complexity",  # 可选

        # Bug 检测
        "bugprone-*",
        "-bugprone-easily-swappable-parameters",  # 有时误报

        # CERT 建议
        "cert-*",

        # 内存安全
        "clang-analyzer-*",
        "-clang-analyzer-security.insecureAPI.DeprecatedOrUnsafeBufferHandling",

        # 代码风格
        "google-*",
        "-google-readability-todo",  # 太严格
        "-google-runtime-references",  # C++11 后可选
    ]

    def __init__(
        self,
        config: Optional[ClangTidyConfig] = None,
        binary_path: str = "clang-tidy",
    ):
        """
        初始化 Clang-tidy 检查器

        Args:
            config: Clang-tidy 配置
            binary_path: clang-tidy 二进制文件路径
        """
        self.config = config or ClangTidyConfig(checks=self.DEFAULT_CHECKS)
        self.binary_path = binary_path

        # 检查 clang-tidy 是否可用
        self.available = self._check_availability()

        if self.available:
            logger.info(
                "clang_tidy_checker_initialized",
                binary_path=self.binary_path,
                checks_count=len(self.config.checks),
            )
        else:
            logger.warning(
                "clang_tidy_not_available",
                message="clang-tidy not found, analysis will be skipped",
            )

    def _check_availability(self) -> bool:
        """检查 clang-tidy 是否可用"""
        try:
            result = subprocess.run(
                [self.binary_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.info("clang_tidy_available", version=version)
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.warning("clang_tidy_check_failed", error=str(e))

        return False

    def check_file(
        self,
        file_path: str,
        compile_commands_dir: Optional[str] = None,
        source_code: Optional[str] = None,
    ) -> StaticAnalysisResult:
        """
        检查 C++ 文件

        Args:
            file_path: 文件路径
            compile_commands_dir: compile_commands.json 所在目录
            source_code: 源代码（可选，用于直接检查）

        Returns:
            StaticAnalysisResult: 分析结果
        """
        result = StaticAnalysisResult(file_path=file_path)

        if not self.available:
            logger.warning("clang_tidy_not_available_skip", file_path=file_path)
            return result

        try:
            # 如果提供了源代码，写入临时文件
            if source_code:
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
                    f.write(source_code)
                    temp_file = f.name
                file_path = temp_file

            try:
                # 构建命令
                cmd = [self.binary_path]
                cmd.extend(self.config.to_command_line_args())
                cmd.append(file_path)

                # 添加 compile_commands 目录
                if compile_commands_dir:
                    cmd.append(f"-p={compile_commands_dir}")

                # 运行 clang-tidy
                logger.debug("running_clang_tidy", command=" ".join(cmd))
                process_result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,  # 60 秒超时
                )

                # 解析输出
                issues = self._parse_output(process_result.stdout, process_result.stderr, file_path)
                result.issues.extend(issues)
                result.clang_tidy_issues = [i for i in issues if isinstance(i, ClangTidyIssue)]

                # 对问题进行分类
                result.categorize_issues()

                logger.info(
                    "clang_tidy_check_completed",
                    file_path=file_path,
                    issues_count=len(issues),
                )

            finally:
                # 清理临时文件
                if source_code and 'temp_file' in locals():
                    try:
                        os.unlink(temp_file)
                    except:
                        pass

            return result

        except subprocess.TimeoutExpired:
            logger.error("clang_tidy_timeout", file_path=file_path)
            return result
        except Exception as e:
            logger.error(
                "clang_tidy_check_failed",
                file_path=file_path,
                error=str(e),
                exc_info=True,
            )
            return result

    def _parse_output(
        self,
        stdout: str,
        stderr: str,
        file_path: str,
    ) -> List[ClangTidyIssue]:
        """解析 clang-tidy 输出"""
        issues = []

        # clang-tidy 输出格式：
        # file:line:column: note: message [rule-id]
        # file:line:column: warning: message [rule-id]
        # file:line:column: error: message [rule-id]

        pattern = r'^([^:]+):(\d+):(\d+):\s+(warning|error|note|info|remark):\s+([^\[]+)(?:\[([^\]]+)\])?'

        for line in stdout.split('\n'):
            match = re.match(pattern, line)
            if match:
                file = match.group(1)
                line_no = int(match.group(2))
                column = int(match.group(3))
                severity = match.group(4)
                message = match.group(5).strip()
                rule_id = match.group(6) if match.group(6) else None

                # 确定类别
                category = self._determine_category(rule_id, message)

                # 确定严重程度
                if severity == "error":
                    severity_level = "critical"
                elif severity == "warning":
                    severity_level = "warning"
                elif severity == "note":
                    severity_level = "info"
                else:
                    severity_level = "info"

                issue = ClangTidyIssue(
                    severity=severity_level,
                    category=category,
                    file=file,
                    line=line_no,
                    column=column,
                    message=message,
                    rule_id=rule_id,
                )

                issues.append(issue)

        # 也可以从 stderr 读取
        for line in stderr.split('\n'):
            if line.strip() and not line.startswith('Use -header-filter'):
                logger.debug("clang_tidy_stderr", line=line)

        return issues

    def _determine_category(self, rule_id: Optional[str], message: str) -> str:
        """根据规则 ID 确定类别"""
        if not rule_id:
            return "style"

        rule_id_lower = rule_id.lower()

        # 内存安全
        if any(prefix in rule_id_lower for prefix in [
            "clang-analyzer-security",
            "cert-msc",
            "cppcoreguidelines-pro-type-reinterpret-cast",
            "cppcoreguidelines-pro-bounds-array-to-pointer-decay",
        ]):
            return "memory"

        # 性能
        if rule_id_lower.startswith("performance-"):
            return "performance"

        # 现代 C++
        if rule_id_lower.startswith("modernize-"):
            return "modern-cpp"

        # 线程安全
        if any(prefix in rule_id_lower for prefix in [
            "cert-msc",  # Concurrency
            "cppcoreguidelines-pro-type-reinterpret-cast",
        ]):
            return "thread-safety"

        # 默认为风格
        return "style"

    def check_multiple_files(
        self,
        file_paths: List[str],
        compile_commands_dir: Optional[str] = None,
    ) -> Dict[str, StaticAnalysisResult]:
        """批量检查文件"""
        results = {}

        for file_path in file_paths:
            results[file_path] = self.check_file(file_path, compile_commands_dir)

        logger.info(
            "clang_tidy_batch_check_completed",
            total_files=len(file_paths),
            total_issues=sum(r.total_issues for r in results.values()),
        )

        return results

    def get_summary(self, results: List[StaticAnalysisResult]) -> Dict[str, Any]:
        """获取检查结果汇总"""
        total_files = len(results)
        total_issues = sum(r.total_issues for r in results)

        # 按严重性统计
        critical = sum(r.critical_count for r in results)
        error = sum(r.error_count for r in results)
        warning = sum(r.warning_count for r in results)
        info = sum(r.info_count for r in results)
        style = sum(r.style_count for r in results)

        # 按类别统计
        memory = sum(len(r.memory_issues) for r in results)
        performance = sum(len(r.performance_issues) for r in results)
        modern_cpp = sum(len(r.modern_cpp_issues) for r in results)
        thread_safety = sum(len(r.thread_safety_issues) for r in results)

        # 找出最常见的问题
        rule_counts: Dict[str, int] = {}
        for result in results:
            for issue in result.clang_tidy_issues:
                if issue.rule_id:
                    rule_counts[issue.rule_id] = rule_counts.get(issue.rule_id, 0) + 1

        top_issues = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_files": total_files,
            "total_issues": total_issues,
            "by_severity": {
                "critical": critical,
                "error": error,
                "warning": warning,
                "info": info,
                "style": style,
            },
            "by_category": {
                "memory": memory,
                "performance": performance,
                "modern_cpp": modern_cpp,
                "thread_safety": thread_safety,
                "style": style,
            },
            "top_issues": top_issues,
        }


# 全局实例
_clang_tidy_checker: Optional[ClangTidyChecker] = None


def get_clang_tidy_checker() -> ClangTidyChecker:
    """获取 Clang-tidy 检查器实例（单例）"""
    global _clang_tidy_checker
    if _clang_tidy_checker is None:
        _clang_tidy_checker = ClangTidyChecker()
    return _clang_tidy_checker
