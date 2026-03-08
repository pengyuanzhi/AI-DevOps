"""
C++ 项目 GitLab 集成服务
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.agents import (
    CppCodeReviewResult,
    CppTestGenerationResult,
    get_cpp_reviewer,
    get_gtest_generator,
)
from src.core.analyzers.cpp import get_cpp_parser
from src.integrations.gitlab import FileOperations, MROperations
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ProcessingStatus(str, Enum):
    """处理状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CppMRProcessingResult:
    """C++ MR 处理结果"""
    project_id: int
    mr_iid: int
    source_branch: str
    target_branch: str
    mr_title: str

    # 处理状态
    status: ProcessingStatus = ProcessingStatus.PENDING

    # 文件分析
    changed_files: List[str] = field(default_factory=list)
    cpp_files: List[str] = field(default_factory=list)
    header_files: List[str] = field(default_factory=list)

    # 测试生成
    test_generation_results: List[CppTestGenerationResult] = field(default_factory=list)
    generated_test_files: List[str] = field(default_factory=list)
    cmake_updates: List[str] = field(default_factory=list)

    # 代码审查
    review_results: List[CppCodeReviewResult] = field(default_factory=list)

    # GitLab 操作
    commits_created: List[str] = field(default_factory=list)
    comments_posted: List[str] = field(default_factory=list)

    # 时间统计
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0

    # 错误
    errors: List[str] = field(default_factory=list)

    @property
    def total_tests_generated(self) -> int:
        """生成的测试总数"""
        return sum(len(result.tests) for result in self.test_generation_results)

    @property
    def total_reviews_done(self) -> int:
        """完成的审查总数"""
        return len(self.review_results)

    @property
    def success(self) -> bool:
        """是否成功"""
        return self.status == ProcessingStatus.COMPLETED and len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "project_id": self.project_id,
            "mr_iid": self.mr_iid,
            "source_branch": self.source_branch,
            "target_branch": self.target_branch,
            "mr_title": self.mr_title,
            "status": self.status.value,
            "changed_files_count": len(self.changed_files),
            "cpp_files_count": len(self.cpp_files),
            "total_tests_generated": self.total_tests_generated,
            "total_reviews_done": self.total_reviews_done,
            "commits_created_count": len(self.commits_created),
            "comments_posted_count": len(self.comments_posted),
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "errors": self.errors,
        }


class CppGitLabService:
    """C++ 项目 GitLab 集成服务"""

    def __init__(
        self,
        mr_operations: Optional[MROperations] = None,
        file_operations: Optional[FileOperations] = None,
        auto_commit: bool = True,
    ):
        """
        初始化服务

        Args:
            mr_operations: MR 操作客户端
            file_operations: 文件操作客户端
            auto_commit: 是否自动提交
        """
        self.mr_operations = mr_operations
        self.file_operations = file_operations
        self.auto_commit = auto_commit

        logger.info(
            "cpp_gitlab_service_initialized",
            has_mr_ops=mr_operations is not None,
            has_file_ops=file_operations is not None,
            auto_commit=auto_commit,
        )

    async def process_merge_request(
        self,
        project_id: int,
        mr_iid: int,
        options: Optional[Dict[str, Any]] = None,
    ) -> CppMRProcessingResult:
        """
        处理 GitLab MR（C++ 项目）

        Args:
            project_id: 项目 ID
            mr_iid: MR IID
            options: 处理选项

        Returns:
            CppMRProcessingResult: 处理结果
        """
        options = options or {}

        result = CppMRProcessingResult(
            project_id=project_id,
            mr_iid=mr_iid,
            status=ProcessingStatus.IN_PROGRESS,
        )

        try:
            logger.info(
                "cpp_mr_processing_started",
                project_id=project_id,
                mr_iid=mr_iid,
            )

            # 1. 获取 MR 信息
            if not self.mr_operations:
                raise RuntimeError("MR operations client not configured")

            mr_details = await self.mr_operations.client.get_mr_details(project_id, mr_iid)
            result.source_branch = mr_details.source_branch
            result.target_branch = mr_details.target_branch
            result.mr_title = mr_details.title

            # 2. 获取变更的文件
            changed_files = await self.mr_operations.get_changed_files(
                project_id=project_id,
                mr_iid=mr_iid,
                extensions=[".cpp", ".h", ".hpp", ".cc", ".cxx"],  # C++ 文件
            )
            result.changed_files = [f["new_path"] for f in changed_files if not f["deleted_file"]]

            # 3. 识别源文件和头文件
            result.cpp_files = [f for f in result.changed_files if f.endswith((".cpp", ".cc", ".cxx"))]
            result.header_files = [f for f in result.changed_files if f.endswith((".h", ".hpp"))]

            logger.info(
                "mr_files_analyzed",
                cpp_files_count=len(result.cpp_files),
                header_files_count=len(result.header_files),
            )

            # 4. 批量获取文件内容
            if result.cpp_files:
                file_contents = await self.file_operations.batch_get_files(
                    project_id=project_id,
                    file_paths=result.cpp_files,
                    ref=result.source_branch,
                )
            else:
                file_contents = {}

            # 5. 生成测试
            if options.get("generate_tests", True):
                await self._generate_tests(
                    project_id=project_id,
                    mr_iid=mr_iid,
                    file_contents=file_contents,
                    result=result,
                )

            # 6. 代码审查
            if options.get("run_review", True):
                await self._run_code_review(
                    project_id=project_id,
                    mr_iid=mr_iid,
                    file_contents=file_contents,
                    result=result,
                )

            # 7. 提交生成的测试文件
            if self.auto_commit and result.generated_test_files:
                await self._commit_generated_files(
                    project_id=project_id,
                    mr_iid=mr_iid,
                    result=result,
                )

            # 8. 发布审查评论
            if options.get("post_comments", True):
                await self._post_review_comments(
                    project_id=project_id,
                    mr_iid=mr_iid,
                    result=result,
                )

            result.status = ProcessingStatus.COMPLETED
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()

            logger.info(
                "cpp_mr_processing_completed",
                project_id=project_id,
                mr_iid=mr_iid,
                duration_seconds=result.duration_seconds,
                tests_generated=result.total_tests_generated,
                reviews_done=result.total_reviews_done,
            )

            return result

        except Exception as e:
            logger.error(
                "cpp_mr_processing_failed",
                project_id=project_id,
                mr_iid=mr_iid,
                error=str(e),
                exc_info=True,
            )
            result.status = ProcessingStatus.FAILED
            result.errors.append(str(e))
            return result

    async def _generate_tests(
        self,
        project_id: int,
        mr_iid: int,
        file_contents: Dict[str, Optional[str]],
        result: CppMRProcessingResult,
    ) -> None:
        """生成测试"""
        try:
            generator = get_gtest_generator()

            for file_path, source_code in file_contents.items():
                if not source_code:
                    continue

                logger.info("generating_test_for_file", file_path=file_path)

                # 生成测试
                gen_result = await generator.generate_tests(
                    source_code=source_code,
                    file_path=file_path,
                )

                if gen_result and gen_result.tests:
                    result.test_generation_results.append(gen_result)

                    # 记录生成的测试文件
                    for test in gen_result.tests:
                        result.generated_test_files.append(test.test_file)

                    # 记录 CMake 更新
                    if gen_result.cmake_updates:
                        result.cmake_updates.extend(gen_result.cmake_updates)

        except Exception as e:
            logger.error("test_generation_failed", error=str(e))
            result.errors.append(f"测试生成失败: {e}")

    async def _run_code_review(
        self,
        project_id: int,
        mr_iid: int,
        file_contents: Dict[str, Optional[str]],
        result: CppMRProcessingResult,
    ) -> None:
        """运行代码审查"""
        try:
            reviewer = get_cpp_reviewer()

            # 获取 MR diff
            diffs = await self.mr_operations.client.get_mr_diff(project_id, mr_iid)
            diff_text = self._format_diffs(diffs)

            for file_path, source_code in file_contents.items():
                if not source_code:
                    continue

                logger.info("reviewing_file", file_path=file_path)

                # 运行审查
                review_result = await reviewer.review_cpp_file(
                    project_id=project_id,
                    mr_iid=mr_iid,
                    file_path=file_path,
                    diff=diff_text,
                    source_code=source_code,
                )

                result.review_results.append(review_result)

        except Exception as e:
            logger.error("code_review_failed", error=str(e))
            result.errors.append(f"代码审查失败: {e}")

    async def _commit_generated_files(
        self,
        project_id: int,
        mr_iid: int,
        result: CppMRProcessingResult,
    ) -> None:
        """提交生成的测试文件"""
        try:
            if not self.file_operations:
                logger.warning("file_operations_not_available_skip_commit")
                return

            # 获取 MR 详情（需要分支信息）
            mr_details = await self.mr_operations.client.get_mr_details(
                project_id, mr_iid
            )
            source_branch = mr_details.source_branch

            # 提交测试文件
            for gen_result in result.test_generation_results:
                if not gen_result.tests:
                    continue

                # 获取生成的测试代码
                test_code = gen_result.get_test_code()
                if not test_code:
                    continue

                # 确定测试文件路径
                # 源文件: src/calculator.cpp -> 测试文件: tests/test_calculator.cpp
                test_file_path = gen_result.tests[0].test_file

                logger.info(
                    "committing_test_file",
                    file_path=test_file_path,
                    code_size=len(test_code),
                )

                # 创建文件并提交到 GitLab
                commit_action = {
                    "action": "create",
                    "file_path": test_file_path,
                    "content": test_code,
                }

                # 提交到源分支
                await self.file_operations.create_file(
                    project_id=project_id,
                    file_path=test_file_path,
                    content=test_code,
                    commit_message=f"AI-CICD: 生成单元测试 ({test_file_path})",
                    branch=source_branch,
                )

                result.commits_created.append(test_file_path)
                logger.info(
                    "test_file_committed",
                    file_path=test_file_path,
                    branch=source_branch,
                )

            # 更新 CMakeLists.txt
            if result.cmake_updates:
                cmake_file = "CMakeLists.txt"
                logger.info(
                    "updating_cmake",
                    updates_count=len(result.cmake_updates),
                )

                # 获取当前的 CMakeLists.txt
                current_cmake = await self.file_operations.get_file(
                    project_id=project_id,
                    file_path=cmake_file,
                    ref=source_branch,
                )

                if current_cmake:
                    # 合并 CMake 更新
                    updated_cmake = self._merge_cmake_updates(
                        current_cmake, result.cmake_updates
                    )

                    # 提交更新后的 CMakeLists.txt
                    await self.file_operations.update_file(
                        project_id=project_id,
                        file_path=cmake_file,
                        content=updated_cmake,
                        commit_message="AI-CICD: 更新 CMakeLists.txt 添加测试",
                        branch=source_branch,
                    )

                    result.commits_created.append(cmake_file)
                    logger.info("cmake_updated")
                else:
                    logger.warning("cmake_file_not_found", file_path=cmake_file)

            logger.info(
                "commit_generated_files_completed",
                files_count=len(result.commits_created),
            )

        except Exception as e:
            logger.error("commit_files_failed", error=str(e), exc_info=True)
            result.errors.append(f"提交文件失败: {e}")

    def _merge_cmake_updates(
        self, current_cmake: str, updates: List[str]
    ) -> str:
        """合并 CMake 更新到现有 CMakeLists.txt"""
        # 简单实现：将更新内容追加到文件末尾
        # 在生产环境中，应该更智能地解析和合并 CMakeLists.txt
        separator = "\n# === AI-CICD 生成的测试配置 ===\n"
        updates_block = separator + "\n".join(updates) + "\n"

        # 检查是否已经存在 AI-CICD 部分
        if separator in current_cmake:
            # 替换现有部分
            parts = current_cmake.split(separator)
            return parts[0] + updates_block
        else:
            # 追加到文件末尾
            return current_cmake + "\n" + updates_block

    async def _post_review_comments(
        self,
        project_id: int,
        mr_iid: int,
        result: CppMRProcessingResult,
    ) -> None:
        """发布审查评论"""
        try:
            # 生成审查摘要
            summary = self._generate_review_summary(result)

            if summary:
                # 发布 MR 级别评论
                await self.mr_operations.create_mr_note(
                    project_id=project_id,
                    mr_iid=mr_iid,
                    body=summary,
                )
                result.comments_posted.append("review_summary")

            # 为每个文件发布具体评论
            for review_result in result.review_results:
                if review_result.critical_issues:
                    comment = self._generate_file_review_comment(review_result)
                    await self.mr_operations.create_mr_note(
                        project_id=project_id,
                        mr_iid=mr_iid,
                        body=comment,
                    )
                    result.comments_posted.append(f"file_review_{review_result.file_path}")

        except Exception as e:
            logger.error("post_comments_failed", error=str(e))
            result.errors.append(f"发布评论失败: {e}")

    def _format_diffs(self, diffs: List[Dict[str, Any]]) -> str:
        """格式化 diffs"""
        diff_lines = []

        for diff in diffs:
            diff_lines.append(f"diff --git a/{diff['old_path']} b/{diff['new_path']}")
            diff_lines.append(f"{'new file' if diff.get('new_file') else '---'} a/{diff['old_path']}")
            diff_lines.append(f"+++ b/{diff['new_path']}")
            diff_lines.append(diff.get('diff', ''))

        return "\n".join(diff_lines)

    def _generate_review_summary(self, result: CppMRProcessingResult) -> str:
        """生成审查摘要"""
        lines = [
            "## 🤖 AI-CICD C++ 代码审查报告\n",
            f"**MR**: {result.mr_title}",
            f"**状态**: {result.status.value}",
            f"**变更文件**: {len(result.changed_files)} 个 C++ 文件",
            "",
        ]

        # 测试生成
        if result.total_tests_generated > 0:
            lines.extend([
                "### ✅ 测试生成",
                f"- 生成了 **{result.total_tests_generated}** 个测试用例",
                f"- 测试文件: {', '.join(Path(f).name for f in result.generated_test_files[:5])}",
                "",
            ])

        # 代码审查
        if result.total_reviews_done > 0:
            lines.extend([
                "### 📊 代码审查",
                f"- 审查了 **{result.total_reviews_done}** 个文件",
            ])

            # 计算平均分
            scores = [r.overall_score for r in result.review_results if r.overall_score > 0]
            if scores:
                avg_score = sum(scores) / len(scores)
                grade = "A" if avg_score >= 90 else "B" if avg_score >= 80 else "C" if avg_score >= 70 else "D"
                lines.extend([
                    f"- **平均分数**: {avg_score:.1f}/100 (等级: {grade})",
                ])

            # 统计问题
            total_issues = sum(len(r.static_analysis.issues) for r in result.review_results if r.static_analysis)
            critical = sum(len(r.critical_issues) for r in result.review_results)

            lines.extend([
                f"- **发现问题**: {total_issues} 个 (严重: {critical})",
                "",
            ])

        # 建议
        recommendations = []
        for r in result.review_results:
            recommendations.extend(r.recommendations[:3])

        if recommendations:
            lines.extend([
                "### 💡 改进建议",
            ])
            for i, rec in enumerate(recommendations[:5], 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        lines.append(f"⏱️ 处理时间: {result.duration_seconds:.1f} 秒")

        return "\n".join(lines)

    def _generate_file_review_comment(self, review_result: CppCodeReviewResult) -> str:
        """生成文件级审查评论"""
        lines = [
            f"## 📄 文件审查: `{review_result.file_path}`\n",
            f"**质量分数**: {review_result.overall_score:.1f}/100",
            f"**风险等级**: {review_result.risk_level.value.upper()}",
            "",
        ]

        if review_result.critical_issues:
            lines.extend([
                "### ⚠️ 严重问题\n",
                *review_result.critical_issues[:5],
                "",
            ])

        if review_result.high_priority_issues:
            lines.extend([
                "### 📌 高优先级问题\n",
                *review_result.high_priority_issues[:5],
                "",
            ])

        if review_result.recommendations:
            lines.extend([
                "### 💡 建议\n",
                *review_result.recommendations[:3],
                "",
            ])

        if review_result.ai_review:
            lines.extend([
                "### 🤖 AI 审查意见\n",
                review_result.ai_review[:500],
                "...",
                "",
            ])

        return "\n".join(lines)


# 全局实例
_cpp_gitlab_service: Optional[CppGitLabService] = None


def get_cpp_gitlab_service() -> CppGitLabService:
    """获取 C++ GitLab 服务实例（单例）"""
    global _cpp_gitlab_service
    if _cpp_gitlab_service is None:
        from src.integrations.gitlab import get_gitlab_client

        gitlab_client = get_gitlab_client()
        if gitlab_client:
            mr_ops = MROperations(client=gitlab_client)
            file_ops = FileOperations(client=gitlab_client)
        else:
            mr_ops = None
            file_ops = None

        _cpp_gitlab_service = CppGitLabService(
            mr_operations=mr_ops,
            file_operations=file_ops,
        )
    return _cpp_gitlab_service
