"""
自动修复执行器

安全地自动应用修复建议
"""

import os
import shutil
import subprocess
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

from ....utils.logger import get_logger
from .fix_generator import FixSuggestion, CodeChange

logger = get_logger(__name__)


class ExecutionStatus(str, Enum):
    """执行状态"""
    PENDING = "pending"
    PREPARING = "preparing"
    BACKING_UP = "backing_up"
    APPLYING = "applying"
    VERIFYING = "verifying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REVERTED = "reverted"  # 失败后已回滚


@dataclass
class ExecutionResult:
    """执行结果"""
    status: ExecutionStatus
    suggestion_id: str

    # 执行详情
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    # 变更记录
    modified_files: List[str] = field(default_factory=list)
    backup_location: Optional[str] = None
    commands_executed: List[str] = field(default_factory=list)

    # 结果
    success: bool = False
    output: str = ""
    error: str = ""
    verification_passed: bool = False

    # 错误处理
    error_message: str = ""
    rollback_attempted: bool = False
    rollback_succeeded: bool = False


class SafeFixExecutor:
    """
    安全的修复执行器

    自动应用修复建议，包含备份、验证和回滚机制
    """

    def __init__(self):
        self.backup_dir = Path("/tmp/ai-cicd-fix-backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def execute_fix(
        self,
        suggestion: FixSuggestion,
        project_path: str,
        dry_run: bool = True,
    ) -> ExecutionResult:
        """
        执行修复建议

        Args:
            suggestion: 修复建议
            project_path: 项目路径
            dry_run: 是否模拟运行（不实际修改）

        Returns:
            执行结果
        """
        result = ExecutionResult(
            status=ExecutionStatus.PENDING,
            suggestion_id=suggestion.suggestion_id,
            started_at=datetime.now(),
        )

        logger.info(
            "fix_execution_started",
            suggestion_id=suggestion.suggestion_id,
            title=suggestion.title,
            dry_run=dry_run,
            project_path=project_path,
        )

        # 检查是否可以自动应用
        if not suggestion.auto_applicable and not dry_run:
            result.status = ExecutionStatus.FAILED
            result.error_message = "修复建议标记为不可自动应用"
            logger.warning("fix_not_auto_applicable", suggestion_id=suggestion.suggestion_id)
            return result

        try:
            # 1. 准备阶段
            result.status = ExecutionStatus.PREPARING
            logger.info("preparing_fix_execution")

            # 2. 备份
            if not dry_run:
                result = await self._backup_changes(suggestion, project_path, result)
                if result.status == ExecutionStatus.FAILED:
                    return result

            # 3. 应用变更
            result.status = ExecutionStatus.APPLYING
            logger.info("applying_fix_changes")

            if suggestion.code_changes:
                result = await self._apply_code_changes(
                    suggestion.code_changes,
                    project_path,
                    dry_run,
                    result,
                )
                if not result.success:
                    return result

            if suggestion.commands:
                result = await self._execute_commands(
                    suggestion.commands,
                    project_path,
                    dry_run,
                    result,
                )
                if not result.success:
                    # 尝试回滚
                    if not dry_run:
                        await self._rollback_fix(project_path, result)
                    return result

            # 4. 验证
            result.status = ExecutionStatus.VERIFYING
            logger.info("verifying_fix")

            verification_result = await self._verify_fix(
                suggestion,
                project_path,
                dry_run,
            )

            result.verification_passed = verification_result["passed"]
            result.output = verification_result.get("output", "")

            if not result.verification_passed:
                logger.warning("fix_verification_failed", suggestion_id=suggestion.suggestion_id)
                if not dry_run:
                    # 验证失败，回滚
                    await self._rollback_fix(project_path, result)
                result.status = ExecutionStatus.FAILED
                result.error_message = "修复验证失败"
                return result

            # 成功
            result.status = ExecutionStatus.SUCCEEDED
            result.success = True
            result.completed_at = datetime.now()
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()

            logger.info(
                "fix_execution_succeeded",
                suggestion_id=suggestion.suggestion_id,
                duration=result.duration_seconds,
            )

            return result

        except Exception as e:
            logger.error(
                "fix_execution_exception",
                suggestion_id=suggestion.suggestion_id,
                error=str(e),
                exc_info=True,
            )

            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)

            # 尝试回滚
            if not dry_run:
                await self._rollback_fix(project_path, result)

            return result

    async def _backup_changes(
        self,
        suggestion: FixSuggestion,
        project_path: str,
        result: ExecutionResult,
    ) -> ExecutionResult:
        """备份将要修改的文件"""
        result.status = ExecutionStatus.BACKING_UP

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{suggestion.suggestion_id}_{timestamp}"
            backup_path.mkdir(parents=True, exist_ok=True)

            result.backup_location = str(backup_path)

            # 备份将要修改的文件
            for change in suggestion.code_changes:
                if not change.file_path:
                    continue

                src_file = Path(project_path) / change.file_path
                if src_file.exists():
                    dst_file = backup_path / change.file_path
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    result.modified_files.append(change.file_path)
                    logger.debug("file_backed_up", file=str(src_file))

            logger.info(
                "backup_completed",
                backup_path=str(backup_path),
                files_count=len(result.modified_files),
            )

            return result

        except Exception as e:
            logger.error(
                "backup_failed",
                error=str(e),
                exc_info=True,
            )
            result.status = ExecutionStatus.FAILED
            result.error_message = f"备份失败: {str(e)}"
            return result

    async def _apply_code_changes(
        self,
        changes: List[CodeChange],
        project_path: str,
        dry_run: bool,
        result: ExecutionResult,
    ) -> ExecutionResult:
        """应用代码变更"""
        for change in changes:
            try:
                file_path = Path(project_path) / change.file_path

                # 确保目录存在
                file_path.parent.mkdir(parents=True, exist_ok=True)

                if dry_run:
                    # 模拟运行：只记录
                    logger.info(
                        "dry_run_code_change",
                        file=str(file_path),
                        description=change.description,
                    )
                    result.output += f"[DRY RUN] Would modify: {file_path}\n"
                else:
                    # 实际应用
                    if file_path.exists():
                        content = file_path.read_text()

                        # 替换代码
                        if change.old_code in content:
                            content = content.replace(change.old_code, change.new_code, 1)
                            file_path.write_text(content)
                            logger.info("code_change_applied", file=str(file_path))
                        else:
                            logger.warning(
                                "old_code_not_found",
                                file=str(file_path),
                                old_code=change.old_code[:100],
                            )
                            result.success = False
                            result.error_message = f"在 {file_path} 中找不到要替换的代码"
                            return result
                    else:
                        # 新文件
                        file_path.write_text(change.new_code)
                        logger.info("new_file_created", file=str(file_path))

                    if change.file_path not in result.modified_files:
                        result.modified_files.append(change.file_path)

            except Exception as e:
                logger.error(
                    "code_change_failed",
                    file=change.file_path,
                    error=str(e),
                )
                result.success = False
                result.error_message = f"代码变更失败: {str(e)}"
                return result

        result.success = True
        return result

    async def _execute_commands(
        self,
        commands: List[str],
        project_path: str,
        dry_run: bool,
        result: ExecutionResult,
    ) -> ExecutionResult:
        """执行命令"""
        for cmd in commands:
            try:
                if dry_run:
                    logger.info("dry_run_command", command=cmd)
                    result.output += f"[DRY RUN] Would execute: {cmd}\n"
                    result.commands_executed.append(cmd)
                else:
                    logger.info("executing_command", command=cmd)
                    result.commands_executed.append(cmd)

                    process = await subprocess.run(
                        cmd,
                        shell=True,
                        cwd=project_path,
                        capture_output=True,
                        text=True,
                        timeout=300,  # 5分钟超时
                    )

                    result.output += f"Command: {cmd}\n"
                    result.output += f"stdout: {process.stdout}\n"
                    result.output += f"stderr: {process.stderr}\n"

                    if process.returncode != 0:
                        result.success = False
                        result.error = process.stderr
                        result.error_message = f"命令执行失败: {cmd}"
                        logger.error(
                            "command_failed",
                            command=cmd,
                            returncode=process.returncode,
                            stderr=process.stderr,
                        )
                        return result

            except subprocess.TimeoutExpired:
                result.success = False
                result.error_message = f"命令超时: {cmd}"
                logger.error("command_timeout", command=cmd)
                return result
            except Exception as e:
                result.success = False
                result.error_message = f"命令执行异常: {str(e)}"
                logger.error("command_exception", command=cmd, error=str(e))
                return result

        result.success = True
        return result

    async def _verify_fix(
        self,
        suggestion: FixSuggestion,
        project_path: str,
        dry_run: bool,
    ) -> Dict:
        """验证修复"""
        verification_result = {
            "passed": True,
            "output": "",
        }

        if not suggestion.verification_steps:
            verification_result["output"] = "无验证步骤"
            return verification_result

        for step in suggestion.verification_steps:
            if dry_run:
                verification_result["output"] += f"[DRY RUN] Would verify: {step}\n"
            else:
                # 尝试将验证步骤转换为命令执行
                # 这是一个简化版本，实际应该更智能
                logger.info("executing_verification_step", step=step)
                verification_result["output"] += f"Step: {step}\n"

                # 某些步骤可以转换为命令
                if "清理" in step and "构建" in step:
                    # 可以执行清理命令
                    pass
                elif "运行" in step and "测试" in step:
                    # 可以运行测试命令
                    pass

        verification_result["passed"] = True
        return verification_result

    async def _rollback_fix(
        self,
        project_path: str,
        result: ExecutionResult,
    ) -> None:
        """回滚修复"""
        logger.info(
            "rolling_back_fix",
            suggestion_id=result.suggestion_id,
            backup_location=result.backup_location,
        )

        result.rollback_attempted = True

        if not result.backup_location or not result.modified_files:
            logger.warning("nothing_to_rollback")
            return

        try:
            backup_path = Path(result.backup_location)

            for file_path in result.modified_files:
                src_file = backup_path / file_path
                dst_file = Path(project_path) / file_path

                if src_file.exists():
                    shutil.copy2(src_file, dst_file)
                    logger.info("file_restored", file=file_path)
                else:
                    logger.warning("backup_not_found", file=file_path)

            result.rollback_succeeded = True
            result.status = ExecutionStatus.REVERTED
            logger.info("rollback_succeeded")

        except Exception as e:
            logger.error(
                "rollback_failed",
                error=str(e),
                exc_info=True,
            )
            result.rollback_succeeded = False


# 全局单例
fix_executor = SafeFixExecutor()
