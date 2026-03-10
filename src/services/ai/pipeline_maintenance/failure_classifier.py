"""
流水线失败分类器

分析构建和测试失败日志，自动分类失败类型
"""

import re
from enum import Enum
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime

from ....utils.logger import get_logger

logger = get_logger(__name__)


class FailureType(str, Enum):
    """失败类型"""
    # 编译错误
    COMPILATION_ERROR = "compilation_error"
    LINK_ERROR = "link_error"
    MISSING_DEPENDENCY = "missing_dependency"
    SYNTAX_ERROR = "syntax_error"

    # 测试失败
    TEST_FAILURE = "test_failure"
    TEST_TIMEOUT = "test_timeout"
    TEST_CRASH = "test_crash"
    ASSERTION_FAILED = "assertion_failed"

    # 运行时错误
    RUNTIME_ERROR = "runtime_error"
    SEGMENTATION_FAULT = "segmentation_fault"
    MEMORY_LEAK = "memory_leak"
    DEADLOCK = "deadlock"

    # 配置问题
    CONFIGURATION_ERROR = "configuration_error"
    ENVIRONMENT_ERROR = "environment_error"
    PERMISSION_ERROR = "permission_error"

    # 资源问题
    OUT_OF_MEMORY = "out_of_memory"
    DISK_FULL = "disk_full"
    NETWORK_ERROR = "network_error"

    # 代码质量
    CODE_QUALITY = "code_quality"
    LINT_ERROR = "lint_error"
    STATIC_ANALYSIS = "static_analysis"

    # 其他
    UNKNOWN = "unknown"
    OTHER = "other"


class FailureSeverity(str, Enum):
    """失败严重程度"""
    CRITICAL = "critical"  # 阻塞所有功能
    HIGH = "high"  # 影响核心功能
    MEDIUM = "medium"  # 影响部分功能
    LOW = "low"  # 轻微影响
    INFO = "info"  # 仅信息性


@dataclass
class FailurePattern:
    """失败模式"""
    pattern_id: str
    name: str
    description: str
    failure_type: FailureType
    severity: FailureSeverity

    # 匹配规则
    regex_patterns: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    file_patterns: List[str] = field(default_factory=list)
    exclude_keywords: List[str] = field(default_factory=list)  # 排除关键词

    # 上下文要求
    requires_test_context: bool = False
    requires_build_context: bool = False

    # 修复建议
    auto_fixable: bool = False
    common_fixes: List[str] = field(default_factory=list)

    # 统计信息
    occurrence_count: int = 0
    last_seen: Optional[datetime] = None


@dataclass
class ClassificationResult:
    """分类结果"""
    failure_type: FailureType
    severity: FailureSeverity
    confidence: float  # 0-1

    # 匹配的模式
    matched_patterns: List[str] = field(default_factory=list)

    # 关键信息
    error_location: Optional[str] = None  # 文件:行号
    error_message: Optional[str] = None
    context_lines: List[str] = field(default_factory=list)

    # 建议操作
    suggested_actions: List[str] = field(default_factory=list)
    auto_fix_available: bool = False


class FailureClassifier:
    """
    失败分类器

    使用基于规则和模式匹配的方法分类失败日志
    """

    def __init__(self):
        self.patterns: Dict[str, FailurePattern] = {}
        self._initialize_builtin_patterns()

    def _initialize_builtin_patterns(self):
        """初始化内置失败模式"""
        # 编译错误
        self.add_pattern(FailurePattern(
            pattern_id="compilation_error_generic",
            name="通用编译错误",
            description="C/C++编译错误",
            failure_type=FailureType.COMPILATION_ERROR,
            severity=FailureSeverity.HIGH,
            regex_patterns=[
                r"error:\s*\w+:\d+:\d+:",
                r"\.cpp:\d+:\d+:\s*error:",
                r"\.c:\d+:\d+:\s*error:",
                r"\.cpp:\d+:\d+:\s*fatal error:",  # C++ fatal errors
                r"compilation terminated",  # Compiler stopped
                r"was not declared in this scope",  # Undeclared identifier
            ],
            keywords=["compilation failed", "compiler error", "fatal error"],
            requires_build_context=True,
            common_fixes=[
                "检查语法错误",
                "修复类型不匹配",
                "添加缺失的头文件",
            ]
        ))

        self.add_pattern(FailurePattern(
            pattern_id="compilation_error_cmake",
            name="CMake编译错误",
            description="CMake构建过程中的编译错误",
            failure_type=FailureType.COMPILATION_ERROR,
            severity=FailureSeverity.HIGH,
            regex_patterns=[
                r"\[\s*\d+%\]\]\s*Building.*object",
                r"make\[2\]:.*\*\*\*.*Error",
                r"Error \d+",  # Make error
                r"fatal error:\s*[\w/.]+\.(h|hpp):.*No such file",  # Missing header in CMake
            ],
            keywords=["building", "cmakefiles", "error", "compilation"],
            requires_build_context=True,
            common_fixes=[
                "检查CMakeLists.txt配置",
                "修复源代码错误",
                "添加缺失的头文件或依赖",
            ]
        ))

        self.add_pattern(FailurePattern(
            pattern_id="link_error_undefined",
            name="未定义引用错误",
            description="链接时找不到符号定义",
            failure_type=FailureType.LINK_ERROR,
            severity=FailureSeverity.HIGH,
            regex_patterns=[
                r"undefined reference to",
                r"unresolved external symbol",
                r"link.*error.*ld returned",
                r"ld returned.*exit status",
            ],
            keywords=["link error", "undefined reference", "ld"],
            common_fixes=[
                "链接缺失的库文件",
                "检查函数声明和定义是否匹配",
                "添加相应的源文件到编译列表",
            ]
        ))

        self.add_pattern(FailurePattern(
            pattern_id="missing_header",
            name="缺失头文件",
            description="找不到头文件",
            failure_type=FailureType.MISSING_DEPENDENCY,
            severity=FailureSeverity.HIGH,
            regex_patterns=[
                r"fatal error:\s*[\w/]+\.h:\s*No such file or directory",
                r"cannot find\s*[\w/]+\.h",
                r"No such file or.*\.h",
            ],
            keywords=["no such file", "file not found", "fatal error"],
            common_fixes=[
                "添加头文件搜索路径",
                "安装依赖的开发包",
                "检查include路径配置",
            ]
        ))

        # 测试失败
        self.add_pattern(FailurePattern(
            pattern_id="test_assertion_failed",
            name="断言失败",
            description="测试断言失败",
            failure_type=FailureType.ASSERTION_FAILED,
            severity=FailureSeverity.MEDIUM,
            regex_patterns=[
                r"Assertion.*failed",
                r"EXPECT_.*\s*failed",
                r"ASSERT_.*\s*failed",
                r"Expected:.*Actual:",
                r"Compared values are not the same",  # Qt Test
                r"FAIL!\s*:\s*.*::.*\(\)",  # Qt Test failure format
            ],
            keywords=["assertion failed", "test failed", "compared values"],
            requires_test_context=True,
            common_fixes=[
                "修复代码逻辑",
                "更新测试期望值",
                "检查测试数据",
            ]
        ))

        self.add_pattern(FailurePattern(
            pattern_id="test_failure_qt",
            name="Qt测试失败",
            description="Qt Test框架测试失败（不包括超时）",
            failure_type=FailureType.TEST_FAILURE,
            severity=FailureSeverity.MEDIUM,
            regex_patterns=[
                r"FAIL!\s*:\s*[\w:]+::[\w]+\(\)",
                r"Totals:\s*\d+\s*passed,\s*\d+\s*failed",
                r"Loc:\s*\[.*\(\d+\)\]",  # Qt Test location format
            ],
            keywords=["FAIL!", "Totals:", "passed", "failed"],
            exclude_keywords=["timeout", "timed out", "did not finish"],  # 排除超时
            requires_test_context=True,
            common_fixes=[
                "检查测试断言",
                "修复代码逻辑",
                "更新测试数据",
            ]
        ))

        self.add_pattern(FailurePattern(
            pattern_id="test_timeout",
            name="测试超时",
            description="测试执行超时",
            failure_type=FailureType.TEST_TIMEOUT,
            severity=FailureSeverity.MEDIUM,
            regex_patterns=[
                r"Test.*timeout",
                r"Timeout.*exceeded",
                r"Killed.*after.*timeout",
                r"Timeout!.*did not finish",  # Qt Test timeout
                r"forcing termination",  # Process killed
                r"Test timed out",  # Qt Test specific
                r"did not finish after.*ms",  # Timeout with milliseconds
            ],
            keywords=["timeout", "time out", "killed", "timed out"],
            requires_test_context=True,
            common_fixes=[
                "优化测试代码",
                "增加超时时间",
                "检查死循环或死锁",
            ]
        ))

        self.add_pattern(FailurePattern(
            pattern_id="test_crash",
            name="测试崩溃",
            description="测试执行时程序崩溃",
            failure_type=FailureType.TEST_CRASH,
            severity=FailureSeverity.HIGH,
            regex_patterns=[
                r"Segmentation fault",
                r"core dumped",
                r"Exception.*access violation",
                r"stack overflow",
                r"aborted",
            ],
            requires_test_context=True,
            common_fixes=[
                "检查空指针访问",
                "检查数组越界",
                "检查内存访问错误",
            ]
        ))

        # 运行时错误
        self.add_pattern(FailurePattern(
            pattern_id="segfault",
            name="段错误",
            description="程序访问非法内存",
            failure_type=FailureType.SEGMENTATION_FAULT,
            severity=FailureSeverity.CRITICAL,
            regex_patterns=[
                r"Segmentation fault",
                r"segfault",
                r"SIGSEGV",
            ],
            common_fixes=[
                "使用调试器定位崩溃位置",
                "检查指针初始化",
                "检查数组边界",
                "使用valgrind检查内存错误",
            ]
        ))

        self.add_pattern(FailurePattern(
            pattern_id="memory_leak",
            name="内存泄漏",
            description="程序未释放分配的内存",
            failure_type=FailureType.MEMORY_LEAK,
            severity=FailureSeverity.MEDIUM,
            regex_patterns=[
                r"still reachable:\s*\d+\s*bytes",
                r"definitely lost:\s*\d+\s*bytes",
                r"Indirectly lost:\s*\d+\s*bytes",
                r"memory leak",
                r"LEAK SUMMARY:",  # Valgrind leak summary
                r"ERROR SUMMARY:.*errors from",  # Valgrind error summary
                r"==\d+==.*definitely lost",  # Valgrind PID prefix
            ],
            keywords=["memory leak", "definitely lost", "indirectly lost", "valgrind"],
            common_fixes=[
                "添加缺失的free/delete",
                "使用智能指针",
                "检查资源释放路径",
            ]
        ))

        # 配置问题
        self.add_pattern(FailurePattern(
            pattern_id="config_error",
            name="配置错误",
            description="构建或测试配置错误",
            failure_type=FailureType.CONFIGURATION_ERROR,
            severity=FailureSeverity.HIGH,
            regex_patterns=[
                r"configuration error",
                r"config.*invalid",
                r"CMake Error at",
            ],
            keywords=["config", "cmake error"],
            common_fixes=[
                "检查配置文件",
                "验证CMakeLists.txt",
                "检查环境变量",
            ]
        ))

        # 资源问题
        self.add_pattern(FailurePattern(
            pattern_id="out_of_memory",
            name="内存不足",
            description="系统或进程内存不足",
            failure_type=FailureType.OUT_OF_MEMORY,
            severity=FailureSeverity.CRITICAL,
            regex_patterns=[
                r"Cannot allocate memory",
                r"Out of memory",
                r"OOM killed",
                r"memory exhausted",
            ],
            common_fixes=[
                "增加系统内存",
                "优化内存使用",
                "减少并行编译数量",
            ]
        ))

        self.add_pattern(FailurePattern(
            pattern_id="disk_full",
            name="磁盘空间不足",
            description="磁盘空间已满",
            failure_type=FailureType.DISK_FULL,
            severity=FailureSeverity.CRITICAL,
            regex_patterns=[
                r"No space left on device",
                r"disk full",
                r"out of disk space",
            ],
            common_fixes=[
                "清理磁盘空间",
                "增加磁盘容量",
                "清理构建产物",
            ]
        ))

        # 代码质量
        self.add_pattern(FailurePattern(
            pattern_id="lint_error",
            name="代码规范错误",
            description="代码风格或规范检查失败",
            failure_type=FailureType.LINT_ERROR,
            severity=FailureSeverity.LOW,
            regex_patterns=[
                r"lint.*error",
                r"clang-tidy.*error",
                r"cpplint.*error",
                r"style.*error",
            ],
            common_fixes=[
                "修复代码风格问题",
                "遵循编码规范",
                "添加必要的注释",
            ]
        ))

        logger.info(
            "failure_patterns_initialized",
            pattern_count=len(self.patterns),
        )

    def add_pattern(self, pattern: FailurePattern) -> None:
        """添加失败模式"""
        self.patterns[pattern.pattern_id] = pattern
        logger.debug("pattern_added", pattern_id=pattern.pattern_id)

    def classify(
        self,
        log_content: str,
        context: Optional[Dict] = None,
    ) -> ClassificationResult:
        """
        分类失败日志

        Args:
            log_content: 失败日志内容
            context: 上下文信息（阶段、项目等）

        Returns:
            分类结果
        """
        context = context or {}
        lines = log_content.split('\n')

        results: List[Tuple[FailurePattern, float, List[str]]] = []

        # 检查每个模式
        for pattern in self.patterns.values():
            # 检查上下文要求
            if pattern.requires_build_context and not context.get("is_build", False):
                continue
            if pattern.requires_test_context and not context.get("is_test", False):
                continue

            matches, confidence = self._match_pattern(lines, pattern)
            if matches:
                results.append((pattern, confidence, matches))

        if not results:
            # 未匹配任何模式
            return ClassificationResult(
                failure_type=FailureType.UNKNOWN,
                severity=FailureSeverity.MEDIUM,
                confidence=0.0,
                error_message=log_content[:500] if log_content else None,
            )

        # 选择最高置信度的结果
        best_pattern, confidence, matches = max(results, key=lambda x: x[1])

        # 提取错误位置和消息
        error_location, error_message, context_lines = self._extract_error_info(
            lines, matches
        )

        # 生成建议操作
        suggested_actions = self._generate_suggestions(
            best_pattern, error_location, error_message
        )

        return ClassificationResult(
            failure_type=best_pattern.failure_type,
            severity=best_pattern.severity,
            confidence=confidence,
            matched_patterns=[best_pattern.pattern_id],
            error_location=error_location,
            error_message=error_message,
            context_lines=context_lines,
            suggested_actions=suggested_actions,
            auto_fix_available=best_pattern.auto_fixable,
        )

    def _match_pattern(
        self,
        lines: List[str],
        pattern: FailurePattern,
    ) -> Tuple[List[str], float]:
        """
        匹配失败模式

        Returns:
            (匹配的行列表, 置信度)
        """
        matched_lines = []
        confidence = 0.0

        # 首先检查是否有排除关键词（如果有则跳过此模式）
        full_text = " ".join(lines).lower()
        for exclude_kw in pattern.exclude_keywords:
            if exclude_kw.lower() in full_text:
                return [], 0.0  # 包含排除关键词，不匹配此模式

        for line in lines:
            # 检查正则表达式
            for regex in pattern.regex_patterns:
                if re.search(regex, line, re.IGNORECASE):
                    matched_lines.append(line.strip())
                    confidence += 0.3
                    break

            # 检查关键词
            for keyword in pattern.keywords:
                if keyword.lower() in line.lower():
                    if line not in matched_lines:
                        matched_lines.append(line.strip())
                    confidence += 0.1

        # 限制置信度范围
        confidence = min(confidence, 1.0)

        # 确保至少有一个匹配才算成功
        if not matched_lines:
            return [], 0.0

        return matched_lines, confidence

    def _extract_error_info(
        self,
        lines: List[str],
        matches: List[str],
    ) -> Tuple[Optional[str], Optional[str], List[str]]:
        """
        提取错误信息

        Returns:
            (错误位置, 错误消息, 上下文行)
        """
        error_location = None
        error_message = None
        context_lines = []

        # 查找错误位置（文件:行号）
        location_pattern = r"([\w/.]+\.(cpp|c|h|hpp)):(\d+):(\d+)?"
        for match in matches:
            location_match = re.search(location_pattern, match)
            if location_match:
                file_path = location_match.group(1)
                line_num = location_match.group(3)
                error_location = f"{file_path}:{line_num}"
                break

        # 提取错误消息
        for match in matches:
            if "error:" in match.lower():
                error_message = match
                break

        # 获取上下文行（从原始日志中）
        if matches:
            first_match = matches[0]
            try:
                match_index = lines.index(first_match + "\n") if first_match + "\n" in lines else -1
                if match_index >= 0:
                    start = max(0, match_index - 2)
                    end = min(len(lines), match_index + 3)
                    context_lines = [line.strip() for line in lines[start:end]]
            except ValueError:
                context_lines = matches[:3]  # 如果找不到，就用匹配的行

        return error_location, error_message, context_lines

    def _generate_suggestions(
        self,
        pattern: FailurePattern,
        error_location: Optional[str],
        error_message: Optional[str],
    ) -> List[str]:
        """生成修复建议"""
        suggestions = []

        # 添加通用修复建议
        if pattern.common_fixes:
            suggestions.extend(pattern.common_fixes)

        # 添加特定建议
        if error_location:
            suggestions.append(f"检查错误位置: {error_location}")

        if pattern.severity in [FailureSeverity.CRITICAL, FailureSeverity.HIGH]:
            suggestions.append("高优先级问题，建议立即修复")

        return suggestions

    def classify_batch(
        self,
        logs: List[Dict[str, str]],
    ) -> List[ClassificationResult]:
        """
        批量分类失败日志

        Args:
            logs: 日志列表，每个包含 log_content 和 context

        Returns:
            分类结果列表
        """
        results = []
        for log_entry in logs:
            result = self.classify(
                log_entry.get("log_content", ""),
                log_entry.get("context"),
            )
            results.append(result)

        return results

    def get_pattern_statistics(self) -> Dict[str, Dict]:
        """获取模式统计信息"""
        stats = {}
        for pattern_id, pattern in self.patterns.items():
            stats[pattern_id] = {
                "name": pattern.name,
                "failure_type": pattern.failure_type.value,
                "occurrence_count": pattern.occurrence_count,
                "last_seen": pattern.last_seen.isoformat() if pattern.last_seen else None,
            }
        return stats

    def update_pattern_stats(self, pattern_id: str) -> None:
        """更新模式统计信息"""
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            pattern.occurrence_count += 1
            pattern.last_seen = datetime.now()
            logger.debug(
                "pattern_stats_updated",
                pattern_id=pattern_id,
                count=pattern.occurrence_count,
            )


# 全局单例
failure_classifier = FailureClassifier()
