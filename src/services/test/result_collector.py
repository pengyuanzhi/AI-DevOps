"""
测试结果收集器

收集、聚合和分析测试结果
"""

import json
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict

from .base import TestResult, TestStatus, TestSuite, TestCase
from .registry import TestRegistry, test_registry_manager
from ....core.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TestRunSummary:
    """测试运行摘要"""
    run_id: str
    project_id: int
    pipeline_id: str
    job_id: str

    # 时间
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    # 统计
    total_suites: int = 0
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0

    # 状态
    status: TestStatus = TestStatus.PENDING

    # 失败详情
    failed_tests: List[Dict[str, Any]] = field(default_factory=list)

    # 覆盖率
    coverage_percent: Optional[float] = None

    # 输出
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['started_at'] = self.started_at.isoformat()
        if self.finished_at:
            data['finished_at'] = self.finished_at.isoformat()
        if self.status:
            data['status'] = self.status.value
        return data


class TestResultCollector:
    """
    测试结果收集器

    收集测试结果并更新测试注册中心。
    """

    def __init__(self):
        self.summaries: Dict[str, TestRunSummary] = {}

    async def collect_result(
        self,
        result: TestResult,
        registry: TestRegistry,
        run_id: str,
    ) -> TestRunSummary:
        """
        收集测试结果

        Args:
            result: 测试结果
            registry: 测试注册中心
            run_id: 运行ID

        Returns:
            测试运行摘要
        """
        summary = TestRunSummary(
            run_id=run_id,
            project_id=registry.project_id,
            pipeline_id=result.suites[0].name if result.suites else "",
            job_id=run_id.split("_")[-1] if "_" in run_id else run_id,
            started_at=result.started_at or datetime.now(),
            finished_at=result.finished_at,
            duration_seconds=result.duration_seconds,
            total_suites=len(result.suites),
            total_tests=result.total_tests,
            passed_tests=result.passed_tests,
            failed_tests=result.failed_tests,
            skipped_tests=result.skipped_tests,
            status=result.status,
            coverage_percent=result.coverage_percent,
            stdout=result.stdout,
            stderr=result.stderr,
        )

        # 更新测试注册中心
        for suite in result.suites:
            for test in suite.tests:
                # 更新测试结果
                registry.update_test_result(
                    test_id=f"{test.suite}:{test.name}",
                    status=test.status,
                    duration_ms=test.duration_ms,
                    timestamp=datetime.now(),
                )

                # 收集失败的测试
                if test.status == TestStatus.FAILED:
                    summary.failed_tests.append({
                        "name": test.name,
                        "suite": test.suite,
                        "file": test.file,
                        "line": test.line,
                        "error": test.error_message,
                    })

        # 保存摘要
        self.summaries[run_id] = summary

        logger.info(
            "test_result_collected",
            run_id=run_id,
            total_tests=result.total_tests,
            passed_tests=result.passed_tests,
            failed_tests=result.failed_tests,
            duration=result.duration_seconds,
        )

        return summary

    def get_summary(self, run_id: str) -> Optional[TestRunSummary]:
        """获取测试运行摘要"""
        return self.summaries.get(run_id)

    def get_all_summaries(self) -> List[TestRunSummary]:
        """获取所有测试运行摘要"""
        return list(self.summaries.values())

    def save_summary(self, run_id: str, output_dir: str):
        """
        保存测试摘要到文件

        Args:
            run_id: 运行ID
            output_dir: 输出目录
        """
        summary = self.summaries.get(run_id)
        if not summary:
            logger.warning("summary_not_found", run_id=run_id)
            return

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 保存JSON
        json_file = output_path / f"{run_id}_summary.json"
        with open(json_file, 'w') as f:
            json.dump(summary.to_dict(), f, indent=2)

        # 保存文本报告
        report_file = output_path / f"{run_id}_report.txt"
        with open(report_file, 'w') as f:
            f.write(self._generate_text_report(summary))

        logger.info(
            "summary_saved",
            run_id=run_id,
            json_file=str(json_file),
            report_file=str(report_file),
        )

    def _generate_text_report(self, summary: TestRunSummary) -> str:
        """生成文本报告"""
        lines = [
            "=" * 80,
            f"Test Run Report: {summary.run_id}",
            "=" * 80,
            "",
            f"Project: {summary.project_id}",
            f"Pipeline: {summary.pipeline_id}",
            f"Job: {summary.job_id}",
            "",
            f"Started: {summary.started_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Finished: {summary.finished_at.strftime('%Y-%m-%d %H:%M:%S') if summary.finished_at else 'N/A'}",
            f"Duration: {summary.duration_seconds:.2f} seconds",
            "",
            "-" * 80,
            "Summary",
            "-" * 80,
            f"Total Test Suites: {summary.total_suites}",
            f"Total Tests: {summary.total_tests}",
            f"Passed: {summary.passed_tests}",
            f"Failed: {summary.failed_tests}",
            f"Skipped: {summary.skipped_tests}",
            "",
        ]

        if summary.coverage_percent is not None:
            lines.extend([
                f"Code Coverage: {summary.coverage_percent:.2f}%",
                "",
            ])

        if summary.failed_tests:
            lines.extend([
                "-" * 80,
                "Failed Tests",
                "-" * 80,
            ])
            for test in summary.failed_tests:
                lines.extend([
                    f"  - {test['name']}",
                    f"    Suite: {test['suite']}",
                    f"    File: {test['file']}:{test['line']}",
                    f"    Error: {test['error']}",
                    "",
                ])

        lines.extend([
            "=" * 80,
        ])

        return "\n".join(lines)

    async def compare_runs(
        self,
        run_id1: str,
        run_id2: str,
    ) -> Optional[Dict[str, Any]]:
        """
        比较两次测试运行

        Args:
            run_id1: 第一次运行ID
            run_id2: 第二次运行ID

        Returns:
            比较结果
        """
        summary1 = self.summaries.get(run_id1)
        summary2 = self.summaries.get(run_id2)

        if not summary1 or not summary2:
            logger.warning("summary_not_found_for_comparison", run_id1=run_id1, run_id2=run_id2)
            return None

        # 比较统计数据
        comparison = {
            "run_id1": run_id1,
            "run_id2": run_id2,
            "timestamp1": summary1.started_at.isoformat(),
            "timestamp2": summary2.started_at.isoformat(),
            "tests": {
                "total": {
                    "run1": summary1.total_tests,
                    "run2": summary2.total_tests,
                    "diff": summary2.total_tests - summary1.total_tests,
                },
                "passed": {
                    "run1": summary1.passed_tests,
                    "run2": summary2.passed_tests,
                    "diff": summary2.passed_tests - summary1.passed_tests,
                },
                "failed": {
                    "run1": summary1.failed_tests,
                    "run2": summary2.failed_tests,
                    "diff": summary2.failed_tests - summary1.failed_tests,
                },
                "skipped": {
                    "run1": summary1.skipped_tests,
                    "run2": summary2.skipped_tests,
                    "diff": summary2.skipped_tests - summary1.skipped_tests,
                },
            },
            "duration": {
                "run1": summary1.duration_seconds,
                "run2": summary2.duration_seconds,
                "diff": summary2.duration_seconds - summary1.duration_seconds,
            },
        }

        # 比较覆盖率
        if summary1.coverage_percent is not None and summary2.coverage_percent is not None:
            comparison["coverage"] = {
                "run1": summary1.coverage_percent,
                "run2": summary2.coverage_percent,
                "diff": summary2.coverage_percent - summary1.coverage_percent,
            }

        # 比较失败的测试
        failed1 = set(t['name'] for t in summary1.failed_tests)
        failed2 = set(t['name'] for t in summary2.failed_tests)

        comparison["failed_tests"] = {
            "both": list(failed1 & failed2),
            "fixed": list(failed1 - failed2),  # 在run1失败但在run2通过
            "regressed": list(failed2 - failed1),  # 在run1通过但在run2失败
        }

        return comparison

    def get_statistics(
        self,
        project_id: Optional[int] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        获取测试统计信息

        Args:
            project_id: 项目ID（可选）
            limit: 返回数量限制

        Returns:
            统计信息
        """
        summaries = list(self.summaries.values())

        # 按项目过滤
        if project_id:
            summaries = [s for s in summaries if s.project_id == project_id]

        # 按时间排序（最新的在前）
        summaries = sorted(summaries, key=lambda s: s.started_at, reverse=True)

        # 限制数量
        summaries = summaries[:limit]

        if not summaries:
            return {
                "total_runs": 0,
                "recent_runs": [],
            }

        # 计算总体统计
        total_runs = len(summaries)
        total_tests = sum(s.total_tests for s in summaries)
        total_passed = sum(s.passed_tests for s in summaries)
        total_failed = sum(s.failed_tests for s in summaries)

        avg_duration = sum(s.duration_seconds for s in summaries) / total_runs

        # 计算平均通过率
        pass_rates = [
            s.passed_tests / s.total_tests if s.total_tests > 0 else 0
            for s in summaries
        ]
        avg_pass_rate = sum(pass_rates) / len(pass_rates) * 100

        # 最近运行
        recent_runs = [s.to_dict() for s in summaries]

        return {
            "total_runs": total_runs,
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "avg_pass_rate": round(avg_pass_rate, 2),
            "avg_duration": round(avg_duration, 2),
            "recent_runs": recent_runs,
        }


# 全局单例
test_result_collector = TestResultCollector()
