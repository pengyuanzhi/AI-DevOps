"""
Cppcheck 静态分析检查器
"""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.quality.cpp.cpp_models import (
    CppcheckIssue,
    StaticAnalysisResult,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CppcheckChecker:
    """Cppcheck 静态分析检查器"""

    # 默认启用项
    DEFAULT_ENABLES = [
        "warning",
        "style",
        "performance",
        "portability",
        "information",
        "unusedFunction",
    ]

    # 默认禁用项（过于严格或误报）
    DEFAULT_DISABLES = [
        "missingIncludeSystem",  # 通常不需要
        "unusedPrivateFunction",  # 某些私有成员可能不使用
    ]

    def __init__(
        self,
        enables: Optional[List[str]] = None,
        disables: Optional[List[str]] = None,
        binary_path: str = "cppcheck",
    ):
        """
        初始化 Cppcheck 检查器

        Args:
            enables: 启用的检查项
            disables: 禁用的检查项
            binary_path: cppcheck 二进制文件路径
        """
        self.enables = enables or self.DEFAULT_ENABLES
        self.disables = disables or self.DEFAULT_DISABLES
        self.binary_path = binary_path

        # 检查 cppcheck 是否可用
        self.available = self._check_availability()

        if self.available:
            logger.info(
                "cppcheck_checker_initialized",
                binary_path=self.binary_path,
                enables_count=len(self.enables),
                disables_count=len(self.disables),
            )
        else:
            logger.warning(
                "cppcheck_not_available",
                message="cppcheck not found, analysis will be skipped",
            )

    def _check_availability(self) -> bool:
        """检查 cppcheck 是否可用"""
        try:
            result = subprocess.run(
                [self.binary_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.info("cppcheck_available", version=version)
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.warning("cppcheck_check_failed", error=str(e))

        return False

    def check_file(
        self,
        file_path: str,
        source_code: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
    ) -> StaticAnalysisResult:
        """
        检查 C++ 文件

        Args:
            file_path: 文件路径
            source_code: 源代码（可选）
            extra_args: 额外的命令行参数

        Returns:
            StaticAnalysisResult: 分析结果
        """
        result = StaticAnalysisResult(file_path=file_path)

        if not self.available:
            logger.warning("cppcheck_not_available_skip", file_path=file_path)
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

                # 启用检查
                cmd.append(f"--enable={'.'.join(self.enables)}")

                # 禁用检查
                for disable in self.disables:
                    cmd.append(f"--disable={disable}")

                # 输出格式为 JSON
                cmd.append("--xml")
                cmd.append(f"--xml-version=2")

                # 抑制某些输出
                cmd.append("--suppressions-list=unusedPrivateFunction")

                # 添加额外参数
                if extra_args:
                    cmd.extend(extra_args)

                # 添加文件
                cmd.append(file_path)

                # 运行 cppcheck
                logger.debug("running_cppcheck", command=" ".join(cmd))
                process_result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                # 解析输出
                issues = self._parse_xml_output(process_result.stdout, file_path)
                result.issues.extend(issues)
                result.cppcheck_issues = [i for i in issues if isinstance(i, CppcheckIssue)]

                # 对问题进行分类
                result.categorize_issues()

                logger.info(
                    "cppcheck_check_completed",
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
            logger.error("cppcheck_timeout", file_path=file_path)
            return result
        except Exception as e:
            logger.error(
                "cppcheck_check_failed",
                file_path=file_path,
                error=str(e),
                exc_info=True,
            )
            return result

    def _parse_xml_output(self, xml_output: str, file_path: str) -> List[CppcheckIssue]:
        """解析 cppcheck XML 输出"""
        issues = []

        try:
            # cppcheck XML 格式示例：
            # <error severity="error" msg="Array 'a[10]' accessed at index 10, which is out of bounds." ...>
            #   <location file="test.cpp" line="5" column="0"/>
            # </error>

            # 简化解析：使用正则表达式
            # <error severity="..." msg="..." id="...">
            error_pattern = r'<error\s+severity="([^"]+)"\s+msg="([^"]+)"(?:\s+id="([^"]+)")?[^>]*>'

            # <location file="..." line="..." column="..."/>
            location_pattern = r'<location\s+file="([^"]+)"\s+line="(\d+)"\s+column="(\d+)"'

            # 找到所有 error 标签
            for error_match in re.finditer(error_pattern, xml_output):
                severity = error_match.group(1)
                message = error_match.group(2).replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')
                rule_id = error_match.group(3) if error_match.group(3) else None

                # 在这个 error 标签后的内容中查找 location
                error_start = error_match.end()
                error_end = xml_output.find('</error>', error_start)
                error_content = xml_output[error_start:error_end]

                location_match = re.search(location_pattern, error_content)
                if location_match:
                    file = location_match.group(1)
                    line = int(location_match.group(2))
                    column = int(location_match.group(3))

                    # 确定严重程度
                    severity_level = self._map_severity(severity)

                    # 确定类别
                    category = self._determine_category(rule_id, message)

                    issue = CppcheckIssue(
                        severity=severity_level,
                        category=category,
                        file=file,
                        line=line,
                        column=column,
                        message=message,
                        rule_id=rule_id,
                    )

                    issues.append(issue)

        except Exception as e:
            logger.error("cppcheck_xml_parse_failed", error=str(e))

        return issues

    def _map_severity(self, cppcheck_severity: str) -> str:
        """映射 cppcheck 严重程度到标准等级"""
        mapping = {
            "error": "critical",
            "warning": "warning",
            "style": "style",
            "performance": "info",
            "portability": "info",
            "information": "info",
        }
        return mapping.get(cppcheck_severity, "info")

    def _determine_category(self, rule_id: Optional[str], message: str) -> str:
        """根据规则 ID 确定类别"""
        if not rule_id:
            return "style"

        rule_id_lower = rule_id.lower()
        message_lower = message.lower()

        # 内存相关
        memory_keywords = [
            "memory leak", "leak", "dealloc", "delete", "free", "buffer",
            "overflow", "underflow", "null pointer", "dangling", "uninitialized",
            "array index", "out of bounds", "uninitvar", "nullPointer",
        ]
        if any(kw in rule_id_lower or kw in message_lower for kw in memory_keywords):
            return "memory"

        # 性能相关
        perf_keywords = [
            "performance", "inefficient", "slow", "redundant",
            "unnecessary", "unused", "temporarily",
        ]
        if any(kw in rule_id_lower or kw in message_lower for kw in perf_keywords):
            return "performance"

        # 现代 C++
        modern_keywords = [
            "c++11", "c++14", "c++17", "auto", "nullptr", "smart",
            "override", "const", "explicit",
        ]
        # cppcheck 通常不标记现代 C++ 问题，所以这个很少用

        # 线程安全
        thread_keywords = ["thread", "mutex", "lock", "race", "concurrency"]
        if any(kw in rule_id_lower or kw in message_lower for kw in thread_keywords):
            return "thread-safety"

        # 默认为风格问题
        return "style"

    def check_multiple_files(
        self,
        file_paths: List[str],
        extra_args: Optional[List[str]] = None,
    ) -> Dict[str, StaticAnalysisResult]:
        """批量检查文件"""
        results = {}

        for file_path in file_paths:
            results[file_path] = self.check_file(file_path, extra_args=extra_args)

        logger.info(
            "cppcheck_batch_check_completed",
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
            for issue in result.cppcheck_issues:
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
_cppcheck_checker: Optional[CppcheckChecker] = None


def get_cppcheck_checker() -> CppcheckChecker:
    """获取 Cppcheck 检查器实例（单例）"""
    global _cppcheck_checker
    if _cppcheck_checker is None:
        _cppcheck_checker = CppcheckChecker()
    return _cppcheck_checker
