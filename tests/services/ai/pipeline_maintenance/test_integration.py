"""
端到端集成测试
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, AsyncMock

from src.services.ai.pipeline_maintenance.failure_classifier import (
    failure_classifier,
    FailureType,
)
from src.services.ai.pipeline_maintenance.root_cause_analyzer import (
    root_cause_analyzer,
    AnalysisContext,
    RootCauseType,
)
from src.services.ai.pipeline_maintenance.fix_generator import (
    fix_generator,
    FixSuggestion,
    FixType,
)
from src.services.ai.pipeline_maintenance.fix_executor import (
    fix_executor,
    ExecutionStatus,
)


class TestPipelineMaintenanceIntegration:
    """端到端集成测试"""

    @pytest.fixture
    def sample_build_log(self):
        """示例构建日志"""
        return """
        [ 25%] Building CXX object CMakeFiles/demo.dir/main.cpp.o
        /home/user/project/main.cpp: In function 'int main(int, char**)':
        /home/user/project/main.cpp:42:10: fatal error: foo.h: No such file or directory
           42 | #include <foo.h>
              |          ^~~~~~~
        compilation terminated.
        make[2]: *** [CMakeFiles/demo.dir/main.cpp.o] Error 1
        make[1]: *** [CMakeFiles/demo.dir/all] Error 2
        make: *** [all] Error 2
        """

    @pytest.fixture
    def sample_test_log(self):
        """示例测试日志"""
        return """
        Running main() from main.cpp
        [==========] Running 3 tests from 1 test suite.
        [----------] Global test environment set-up.
        [----------] 3 tests from CalculatorTest
        [ RUN      ] CalculatorTest.testAdd
        [       OK ] CalculatorTest.testAdd (5 ms)
        [ RUN      ] CalculatorTest.testSubtract
        calculator_test.cpp:42: FAILURE
        Expected: (5 - 3) == 2
          Actual: 5
        calculator_test.cpp:43: Assertion failed: expected == actual
        [  FAILED  ] CalculatorTest.testSubtract (10 ms)
        [----------] 3 tests from CalculatorTest (45 ms total)
        """

    @pytest.fixture
    def temp_project(self):
        """创建临时项目"""
        temp_dir = tempfile.mkdtemp()
        project_dir = Path(temp_dir) / "test_project"
        project_dir.mkdir()

        # 创建CMakeLists.txt
        cmake_file = project_dir / "CMakeLists.txt"
        cmake_file.write_text("""
            cmake_minimum_required(VERSION 3.10)
            project(TestProject)
            add_executable(demo main.cpp)
        """)

        # 创建main.cpp
        main_file = project_dir / "main.cpp"
        main_file.write_text("""
            #include <iostream>
            // #include <foo.h>  // Missing include

            int main() {
                std::cout << "Hello World" << std::endl;
                return 0;
            }
        """)

        yield str(project_dir)

        # 清理
        shutil.rmtree(temp_dir)

    def test_full_classification_workflow(self, sample_build_log):
        """测试完整分类工作流"""
        # 1. 分类失败
        result = failure_classifier.classify(
            sample_build_log,
            {"is_build": True},
        )

        assert result.failure_type == FailureType.MISSING_DEPENDENCY
        assert result.confidence > 0.5
        assert "foo.h" in result.error_message or "No such file" in result.error_message
        assert len(result.suggested_actions) > 0

    def test_full_root_cause_analysis_workflow(self, sample_build_log):
        """测试完整根因分析工作流"""
        # 1. 先分类
        classification = failure_classifier.classify(
            sample_build_log,
            {"is_build": True},
        )

        # 2. 构建分析上下文
        context = AnalysisContext(
            failure_log=sample_build_log,
            failure_type=classification.failure_type,
            error_location=classification.error_location,
            changed_files=["main.cpp", "CMakeLists.txt"],
            project_id=1,
            pipeline_id="pipeline_1",
            job_id="job_1",
        )

        # 3. 分析根因（使用规则，不使用AI以加快测试）
        import asyncio
        root_cause = asyncio.run(root_cause_analyzer.analyze(
            context=context,
            use_ai=False,
        ))

        assert root_cause is not None
        assert root_cause.confidence > 0
        assert len(root_cause.suggested_fixes) > 0

    @pytest.mark.asyncio
    async def test_full_fix_generation_workflow(self, sample_test_log):
        """测试完整修复生成工作流"""
        # 1. 分类
        classification = failure_classifier.classify(
            sample_test_log,
            {"is_test": True},
        )

        assert classification.failure_type == FailureType.ASSERTION_FAILED

        # 2. 根因分析
        context = AnalysisContext(
            failure_log=sample_test_log,
            failure_type=classification.failure_type,
            error_location=classification.error_location,
            changed_files=["calculator_test.cpp"],
            project_id=1,
            pipeline_id="pipeline_1",
            job_id="job_1",
        )

        root_cause = await root_cause_analyzer.analyze(
            context=context,
            use_ai=False,
        )

        # 3. 生成修复建议
        suggestions = await fix_generator.generate_fix(
            root_cause=root_cause,
            use_ai=False,
        )

        assert len(suggestions) > 0
        assert all(isinstance(s, FixSuggestion) for s in suggestions)
        assert all(s.confidence > 0 for s in suggestions)

    @pytest.mark.asyncio
    async def test_full_workflow_dry_run(self, temp_project):
        """测试完整工作流（dry-run模式）"""
        # 模拟场景：CMakeLists.txt缺少链接库

        # 1. 模拟失败日志
        failure_log = """
        /usr/bin/ld: /tmp/demo-main.o: in function `main':
        main.cpp:(.text+0x10): undefined reference to `calculate'
        collect2: error: ld returned 1 exit status
        """

        # 2. 分类
        classification = failure_classifier.classify(
            failure_log,
            {"is_build": True},
        )

        assert classification.failure_type in [
            FailureType.LINK_ERROR,
            FailureType.MISSING_DEPENDENCY,
        ]

        # 3. 根因分析
        context = AnalysisContext(
            failure_log=failure_log,
            failure_type=classification.failure_type,
            error_location=classification.error_location,
            changed_files=["CMakeLists.txt", "main.cpp"],
            project_id=1,
            pipeline_id="pipeline_1",
            job_id="job_1",
        )

        root_cause = await root_cause_analyzer.analyze(
            context=context,
            use_ai=False,
        )

        # 4. 生成修复建议
        suggestions = await fix_generator.generate_fix(
            root_cause=root_cause,
            use_ai=False,
        )

        assert len(suggestions) > 0

        # 5. Dry-run执行修复
        result = await fix_executor.execute_fix(
            suggestion=suggestions[0],
            project_path=temp_project,
            dry_run=True,
        )

        assert result.status in [ExecutionStatus.SUCCEEDED, ExecutionStatus.PENDING]
        assert result.modified_files == []  # dry-run不修改文件

    def test_error_recovery_workflow(self):
        """测试错误恢复工作流"""
        # 测试无法识别的错误
        unknown_log = """
        Something went wrong
        No specific error pattern
        Unknown issue occurred
        """

        # 1. 分类应该返回UNKNOWN
        result = failure_classifier.classify(unknown_log, {"is_build": True})
        assert result.failure_type == FailureType.UNKNOWN
        assert result.confidence < 0.5

        # 2. 根因分析应该仍能工作
        context = AnalysisContext(
            failure_log=unknown_log,
            failure_type=result.failure_type,
            project_id=1,
            pipeline_id="pipeline_1",
            job_id="job_1",
        )

        import asyncio
        root_cause = asyncio.run(root_cause_analyzer.analyze(
            context=context,
            use_ai=False,
        ))

        assert root_cause is not None
        # 应该提供通用的建议
        assert len(root_cause.suggested_fixes) > 0

    def test_batch_processing(self):
        """测试批量处理"""
        logs = [
            "error: undefined reference to `foo'",
            "fatal error: missing.h: No such file",
            "Assertion failed: expected 5 but got 3",
            "Segmentation fault (core dumped)",
        ]

        results = failure_classifier.classify_batch([
            {"log_content": log, "context": {"is_build": True}}
            for log in logs
        ])

        assert len(results) == 4
        # 应该有不同的失败类型
        failure_types = [r.failure_type for r in results]
        assert len(set(failure_types)) > 1  # 至少有2种不同类型


class TestErrorScenarios:
    """错误场景测试"""

    def test_empty_log(self):
        """测试空日志"""
        result = failure_classifier.classify("", {})
        assert result.failure_type == FailureType.UNKNOWN
        assert result.confidence == 0.0

    def test_malformed_log(self):
        """测试格式错误的日志"""
        malformed_log = "!@#$%^&*()_+"
        result = failure_classifier.classify(malformed_log, {})
        assert result.failure_type == FailureType.UNKNOWN

    def test_very_long_log(self):
        """测试超长日志"""
        long_log = "error: " + "x" * 10000 + "\n" * 100
        # 应该能处理而不崩溃
        result = failure_classifier.classify(long_log, {"is_build": True})
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
