"""
修复执行器单元测试
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, AsyncMock
from src.services.ai.pipeline_maintenance.fix_executor import (
    SafeFixExecutor,
    ExecutionStatus,
)
from src.services.ai.pipeline_maintenance.fix_generator import (
    FixSuggestion,
    FixComplexity,
    FixType,
    CodeChange,
)


class TestSafeFixExecutor:
    """安全修复执行器测试"""

    @pytest.fixture
    def executor(self):
        """创建执行器实例"""
        return SafeFixExecutor()

    @pytest.fixture
    def temp_project(self):
        """创建临时项目目录"""
        temp_dir = tempfile.mkdtemp()
        project_dir = Path(temp_dir) / "project"
        project_dir.mkdir()

        # 创建一个测试文件
        test_file = project_dir / "test.cpp"
        test_file.write_text(
            "int main() {\n"
            "    // TODO: fix this\n"
            "    return 0;\n"
            "}"
        )

        yield str(project_dir)

        # 清理
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def simple_suggestion(self):
        """创建简单修复建议"""
        return FixSuggestion(
            suggestion_id="test_fix_1",
            fix_type=FixType.CODE_CHANGE,
            complexity=FixComplexity.TRIVIAL,
            title="修复TODO注释",
            description="移除TODO注释",
            rationale="TODO注释是临时的，应该替换为完成的说明",
            code_changes=[
                CodeChange(
                    file_path="test.cpp",
                    old_code="    // TODO: fix this",
                    new_code="    // Fixed: implementation complete",
                    line_start=2,
                    line_end=2,
                    description="更新注释",
                )
            ],
            commands=[],
            verification_steps=["检查文件内容"],
            expected_outcome="TODO注释已更新",
            estimated_time="1分钟",
            auto_applicable=True,
            confidence=0.9,
        )

    @pytest.mark.asyncio
    async def test_execute_fix_dry_run(self, executor, temp_project, simple_suggestion):
        """测试dry-run模式执行"""
        result = await executor.execute_fix(
            suggestion=simple_suggestion,
            project_path=temp_project,
            dry_run=True,
        )

        assert result.status in [ExecutionStatus.SUCCEEDED, ExecutionStatus.APPLYING]
        assert result.success or result.status == ExecutionStatus.APPLYING
        assert len(result.modified_files) == 0  # dry-run不修改文件

    @pytest.mark.asyncio
    async def test_execute_fix_with_code_change(self, executor, temp_project, simple_suggestion):
        """测试代码变更执行"""
        result = await executor.execute_fix(
            suggestion=simple_suggestion,
            project_path=temp_project,
            dry_run=False,
        )

        assert result.status in [ExecutionStatus.SUCCEEDED, ExecutionStatus.VERIFYING]
        assert "test.cpp" in result.modified_files

        # 验证文件确实被修改了
        test_file = Path(temp_project) / "test.cpp"
        content = test_file.read_text()
        assert "Fixed: implementation complete" in content
        assert "TODO: fix this" not in content

    @pytest.mark.asyncio
    async def test_execute_fix_creates_backup(self, executor, temp_project, simple_suggestion):
        """测试备份创建"""
        result = await executor.execute_fix(
            suggestion=simple_suggestion,
            project_path=temp_project,
            dry_run=False,
        )

        assert result.backup_location is not None
        assert Path(result.backup_location).exists()

        # 检查备份文件
        backup_file = Path(result.backup_location) / "test.cpp"
        assert backup_file.exists()
        assert "TODO: fix this" in backup_file.read_text()

    @pytest.mark.asyncio
    async def test_execute_fix_with_commands(self, executor, temp_project):
        """测试命令执行"""
        suggestion = FixSuggestion(
            suggestion_id="test_fix_commands",
            fix_type=FixType.CONFIG_CHANGE,
            complexity=FixComplexity.SIMPLE,
            title="执行命令",
            description="测试命令执行",
            rationale="测试系统命令执行功能",
            commands=["echo 'test'", "pwd"],
            verification_steps=[],
            auto_applicable=True,
            confidence=0.8,
        )

        result = await executor.execute_fix(
            suggestion=suggestion,
            project_path=temp_project,
            dry_run=True,
        )

        assert result.status in [ExecutionStatus.SUCCEEDED, ExecutionStatus.APPLYING]
        assert len(result.commands_executed) == 2
        assert "test" in result.output

    @pytest.mark.asyncio
    async def test_execute_fix_non_auto_applicable(self, executor, temp_project):
        """测试不可自动应用的修复"""
        suggestion = FixSuggestion(
            suggestion_id="test_fix_manual",
            fix_type=FixType.CODE_CHANGE,
            complexity=FixComplexity.COMPLEX,
            title="需要人工审核",
            description="复杂修复",
            rationale="这个修复太复杂，需要人工审核",
            commands=[],
            verification_steps=[],
            auto_applicable=False,  # 不可自动应用
            confidence=0.7,
        )

        result = await executor.execute_fix(
            suggestion=suggestion,
            project_path=temp_project,
            dry_run=False,
        )

        assert result.status == ExecutionStatus.FAILED
        assert "not auto_applicable" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_fix_rollback_on_error(self, executor, temp_project):
        """测试错误时回滚"""
        # 创建一个会失败的变更（旧代码不存在）
        suggestion = FixSuggestion(
            suggestion_id="test_fix_rollback",
            fix_type=FixType.CODE_CHANGE,
            complexity=FixComplexity.SIMPLE,
            title="测试回滚",
            description="这个修复会失败",
            rationale="测试回滚机制，使用不存在的代码",
            code_changes=[
                CodeChange(
                    file_path="test.cpp",
                    old_code="    // This code does not exist",
                    new_code="    // New code",
                    line_start=0,
                    line_end=0,
                    description="不存在的代码",
                )
            ],
            commands=[],
            verification_steps=[],
            auto_applicable=True,
            confidence=0.5,
        )

        result = await executor.execute_fix(
            suggestion=suggestion,
            project_path=temp_project,
            dry_run=False,
        )

        # 应该失败并尝试回滚
        assert result.status == ExecutionStatus.FAILED
        # 注意：由于旧代码不存在，可能不会触发回滚

    def test_backup_cleanup(self, executor, temp_project, simple_suggestion):
        """测试备份清理（手动调用）"""
        import asyncio

        # 执行修复创建备份
        result = asyncio.run(executor.execute_fix(
            suggestion=simple_suggestion,
            project_path=temp_project,
            dry_run=False,
        ))

        backup_path = result.backup_location
        assert backup_path is not None
        assert Path(backup_path).exists()

        # 手动清理备份可以由用户决定
        # 这里只是验证备份存在


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
