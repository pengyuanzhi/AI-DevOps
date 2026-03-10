"""
失败分类器单元测试
"""

import pytest
from src.services.ai.pipeline_maintenance.failure_classifier import (
    FailureClassifier,
    FailureType,
    FailureSeverity,
    FailurePattern,
)


class TestFailureClassifier:
    """失败分类器测试"""

    @pytest.fixture
    def classifier(self):
        """创建分类器实例"""
        return FailureClassifier()

    def test_classify_link_error(self, classifier):
        """测试链接错误分类"""
        log = """
        /usr/bin/ld: /tmp/main.o: in function `main':
        main.cpp:(.text+0x42): undefined reference to `foo'
        collect2: error: ld returned 1 exit status
        """

        result = classifier.classify(log, {"is_build": True})

        assert result.failure_type == FailureType.LINK_ERROR
        assert result.severity in [FailureSeverity.HIGH, FailureSeverity.CRITICAL]
        assert result.confidence > 0.5
        assert result.error_location is not None
        assert "undefined reference" in result.error_message.lower()

    def test_classify_compilation_error(self, classifier):
        """测试编译错误分类"""
        log = """
        error: main.cpp:42:5: error: 'foo' was not declared in this scope
             42 |     foo();
                |     ^~~
        """

        result = classifier.classify(log, {"is_build": True})

        assert result.failure_type == FailureType.COMPILATION_ERROR
        assert result.confidence > 0.5
        assert "main.cpp" in result.error_location

    def test_classify_missing_header(self, classifier):
        """测试缺失头文件分类"""
        log = """
        fatal error: foo.h: No such file or directory
         #include <foo.h>
                  ^~~~~~~
        """

        result = classifier.classify(log, {"is_build": True})

        assert result.failure_type == FailureType.MISSING_DEPENDENCY
        assert result.confidence > 0.5
        assert any("header" in action.lower() or "include" in action.lower()
                   for action in result.suggested_actions)

    def test_classify_test_assertion_failed(self, classifier):
        """测试断言失败分类"""
        log = """
        Running tests...
        Test Suite: MyTest
        Test Case: testFoo
        Assertion failed: expected == actual
          Expected: 42
          Actual: 24
        """

        result = classifier.classify(log, {"is_test": True})

        assert result.failure_type == FailureType.ASSERTION_FAILED
        assert result.severity == FailureSeverity.MEDIUM

    def test_classify_test_timeout(self, classifier):
        """测试超时分类"""
        log = """
        Test Case: slowTest
        Timeout after 30 seconds
        Test killed due to timeout
        """

        result = classifier.classify(log, {"is_test": True})

        assert result.failure_type == FailureType.TEST_TIMEOUT
        assert result.confidence > 0.3

    def test_classify_test_crash(self, classifier):
        """测试崩溃分类"""
        log = """
        Running test: crashTest
        Segmentation fault (core dumped)
        Test terminated abnormally
        """

        result = classifier.classify(log, {"is_test": True})

        assert result.failure_type in [FailureType.TEST_CRASH, FailureType.SEGMENTATION_FAULT]
        assert result.severity == FailureSeverity.CRITICAL

    def test_classify_memory_leak(self, classifier):
        """测试内存泄漏分类"""
        log = """
        ==12345== HEAP SUMMARY:
        ==12345==     in use at exit: 1,234 bytes in 10 blocks
        ==12345==   total heap usage: 100 allocs, 90 frees, 5,000 bytes allocated
        ==12345==
        ==12345== LEAK SUMMARY:
        ==12345==    definitely lost: 1,000 bytes in 8 blocks
        ==12345==    indirectly lost: 234 bytes in 2 blocks
        """

        result = classifier.classify(log, {"is_test": True})

        assert result.failure_type == FailureType.MEMORY_LEAK
        assert result.severity == FailureSeverity.MEDIUM

    def test_classify_out_of_memory(self, classifier):
        """测试内存不足分类"""
        log = """
        CMake Error: CMake failed with error: Cannot allocate memory
        Compilation failed: Out of memory
        """

        result = classifier.classify(log, {"is_build": True})

        assert result.failure_type == FailureType.OUT_OF_MEMORY
        assert result.severity == FailureSeverity.CRITICAL

    def test_classify_disk_full(self, classifier):
        """测试磁盘空间不足分类"""
        log = """
        error: No space left on device
        Build failed: cannot write output file
        """

        result = classifier.classify(log, {"is_build": True})

        assert result.failure_type == FailureType.DISK_FULL
        assert result.severity == FailureSeverity.CRITICAL

    def test_classify_unknown_error(self, classifier):
        """测试未知错误分类"""
        log = """
        Some unexpected error occurred
        No specific pattern matched
        """

        result = classifier.classify(log, {"is_build": True})

        assert result.failure_type == FailureType.UNKNOWN
        assert result.confidence < 0.5

    def test_batch_classify(self, classifier):
        """测试批量分类"""
        logs = [
            {"log_content": "undefined reference to 'foo'", "context": {"is_build": True}},
            {"log_content": "fatal error: missing.h: No such file", "context": {"is_build": True}},
            {"log_content": "Assertion failed: expected 5 but got 3", "context": {"is_test": True}},
        ]

        results = classifier.classify_batch(logs)

        assert len(results) == 3
        assert results[0].failure_type == FailureType.LINK_ERROR
        assert results[1].failure_type == FailureType.MISSING_DEPENDENCY
        assert results[2].failure_type == FailureType.ASSERTION_FAILED

    def test_add_custom_pattern(self, classifier):
        """测试添加自定义模式"""
        custom_pattern = FailurePattern(
            pattern_id="custom_error",
            name="自定义错误",
            description="测试自定义模式",
            failure_type=FailureType.OTHER,
            severity=FailureSeverity.MEDIUM,
            regex_patterns=[r"CUSTOM_ERROR:\s*\d+"],
            keywords=["custom", "error"],
        )

        classifier.add_pattern(custom_pattern)

        log = "CUSTOM_ERROR: 12345"
        result = classifier.classify(log, {})

        assert "custom_error" in result.matched_patterns

    def test_pattern_statistics(self, classifier):
        """测试获取模式统计"""
        stats = classifier.get_pattern_statistics()

        assert isinstance(stats, dict)
        assert len(stats) > 0
        assert all("name" in v and "failure_type" in v for v in stats.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
