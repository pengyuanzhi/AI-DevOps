"""
Celery测试任务

提供异步测试执行的Celery任务。
"""

import os
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from celery import current_task

from .celery_app import celery_app
from ..services.test.base import TestConfig, TestStatus
from ..services.test.qttest_executor import QtTestExecutor
from ..services.test.gtest_executor import GTestExecutor
from ..services.test.catch2_executor import Catch2Executor
from ..services.test.discovery import test_discovery_service, TestFramework
from ..services.test.registry import test_registry_manager, TestPriority
from ..services.test.result_collector import test_result_collector
from ..services.test.coverage import coverage_collector
from ..services.test.log_streamer import build_log_stream_manager
from ..core.logging.logger import get_logger

logger = get_logger(__name__)


# 全局测试执行器实例
TEST_EXECUTORS = {
    "qttest": QtTestExecutor(),
    "googletest": GTestExecutor(),
    "catch2": Catch2Executor(),
}


@celery_app.task(bind=True, max_retries=3, name="src.tasks.test_tasks.execute_test")
def execute_test(
    self,
    project_id: int,
    pipeline_id: str,
    job_id: str,
    test_config: Dict[str, Any],
    project_path: str,
) -> Dict[str, Any]:
    """
    执行测试任务的Celery任务

    Args:
        project_id: 项目ID
        pipeline_id: 流水线ID
        job_id: 作业ID
        test_config: 测试配置字典
        project_path: 项目路径

    Returns:
        测试结果字典
    """
    try:
        logger.info(
            "test_task_started",
            project_id=project_id,
            pipeline_id=pipeline_id,
            job_id=job_id,
            task_id=self.request.id,
        )

        # 更新任务状态
        self.update_state(
            state="PROGRESS",
            meta={
                "status": "starting",
                "progress": 0,
                "message": "Initializing test environment..."
            }
        )

        # 创建测试配置
        config = TestConfig(
            project_id=project_id,
            pipeline_id=pipeline_id,
            job_id=job_id,
            build_dir=test_config.get("build_dir", f"{project_path}/build"),
            source_dir=test_config.get("source_dir", project_path),
            test_filter=test_config.get("test_filter"),
            parallel_jobs=test_config.get("parallel_jobs", 4),
            timeout=test_config.get("timeout", 300),
            enable_coverage=test_config.get("enable_coverage", True),
            env_vars=test_config.get("environment", {}),
        )

        # 更新进度
        self.update_state(
            state="PROGRESS",
            meta={
                "status": "discovering",
                "progress": 10,
                "message": "Discovering tests..."
            }
        )

        # 在新的事件循环中执行异步测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                _execute_test_async(
                    config=config,
                    test_type=test_config.get("test_type", "qttest"),
                    task=self
                )
            )
        finally:
            loop.close()

        logger.info(
            "test_task_completed",
            project_id=project_id,
            pipeline_id=pipeline_id,
            job_id=job_id,
            status=result["status"],
            duration=result["duration"],
        )

        return result

    except Exception as e:
        logger.error(
            "test_task_failed",
            project_id=project_id,
            pipeline_id=pipeline_id,
            job_id=job_id,
            error=str(e),
            exc_info=True,
        )

        # 重试逻辑
        if self.request.retries < self.max_retries:
            # 计算退避时间（指数退避）
            countdown = 60 * (2 ** self.request.retries)
            logger.info(
                "test_task_retrying",
                retry_count=self.request.retries + 1,
                max_retries=self.max_retries,
                countdown=countdown,
            )
            raise self.retry(exc=e, countdown=countdown)

        # 最终失败
        return {
            "status": "failed",
            "error": str(e),
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0,
            "duration": 0,
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "job_id": job_id,
        }


async def _execute_test_async(
    config: TestConfig,
    test_type: str,
    task: current_task
) -> Dict[str, Any]:
    """
    异步执行测试

    Args:
        config: 测试配置
        test_type: 测试类型
        task: Celery任务实例

    Returns:
        测试结果字典
    """
    # 创建日志流处理器
    log_streamer = build_log_stream_manager.create_streamer(
        job_id=config.job_id,
        project_id=config.project_id,
        pipeline_id=config.pipeline_id
    )

    # 获取测试注册中心
    registry = test_registry_manager.get_registry(config.project_id)

    # 发送测试开始状态
    await log_streamer.send_status_update("running", message="Test started")
    await log_streamer.stream_info(f"Starting test run for {config.job_id}")

    # 进入发现阶段
    task.update_state(
        state="PROGRESS",
        meta={
            "status": "discovering",
            "progress": 20,
            "message": "Discovering tests..."
        }
    )
    await log_streamer.stream_info("Discovering tests...")

    # 发现测试用例
    executor = TEST_EXECUTORS.get(test_type)
    if not executor:
        error_msg = f"Unsupported test type: {test_type}"
        await log_streamer.stream_error(error_msg)

        return {
            "status": "failed",
            "error": error_msg,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0,
            "duration": 0,
            "project_id": config.project_id,
            "pipeline_id": config.pipeline_id,
            "job_id": config.job_id,
        }

    # 配置执行器
    executor.config = config

    # 发现测试
    try:
        test_suites = await test_discovery_service.discover_tests(
            build_dir=config.build_dir,
            source_dir=config.source_dir,
        )

        # 注册测试到注册中心
        for suite in test_suites:
            registry.register_suite(suite)

        await log_streamer.stream_info(f"Discovered {sum(len(s.tests) for s in test_suites)} tests")

    except Exception as e:
        logger.warning("test_discovery_failed", error=str(e))
        # 继续执行，即使发现失败

    # 进入执行阶段
    task.update_state(
        state="PROGRESS",
        meta={
            "status": "running",
            "progress": 50,
            "message": "Running tests..."
        }
    )
    await log_streamer.stream_info("Running tests...")

    start_time = datetime.now()

    try:
        # 运行测试
        result = await executor.run(config)

        duration = (datetime.now() - start_time).total_seconds()

        # 收集结果
        run_id = f"{config.project_id}_{config.pipeline_id}_{config.job_id}"
        summary = await test_result_collector.collect_result(
            result=result,
            registry=registry,
            run_id=run_id,
        )

        # 发送结果状态
        if result.status == TestStatus.PASSED:
            await log_streamer.send_status_update("success", message="Tests passed")
            await log_streamer.stream_info(f"All tests passed! ({result.passed_tests}/{result.total_tests})")
        else:
            await log_streamer.send_status_update("failed", message="Tests failed")
            await log_streamer.stream_error(f"Tests failed: {result.failed_tests}/{result.total_tests} failed")

        # 覆盖率信息
        if result.coverage_percent is not None:
            await log_streamer.stream_info(f"Code coverage: {result.coverage_percent:.2f}%")

        # 转换为字典格式
        result_dict = {
            "status": result.status.value,
            "total_tests": result.total_tests,
            "passed_tests": result.passed_tests,
            "failed_tests": result.failed_tests,
            "skipped_tests": result.skipped_tests,
            "coverage_percent": result.coverage_percent,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "finished_at": result.finished_at.isoformat() if result.finished_at else None,
            "project_id": config.project_id,
            "pipeline_id": config.pipeline_id,
            "job_id": config.job_id,
            "run_id": run_id,
        }

        return result_dict

    except Exception as e:
        logger.error("test_execution_exception", job_id=config.job_id, error=str(e), exc_info=True)

        # 发送错误状态
        await log_streamer.send_status_update("failed", message=f"Test error: {str(e)}")
        await log_streamer.stream_error(f"Test execution error: {str(e)}")

        raise


@celery_app.task(name="src.tasks.test_tasks.discover_tests")
def discover_tests(
    project_id: int,
    build_dir: str,
    source_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    发现测试用例任务

    Args:
        project_id: 项目ID
        build_dir: 构建目录
        source_dir: 源代码目录（可选）

    Returns:
        发现的测试用例信息
    """
    try:
        logger.info(
            "test_discovery_task_started",
            project_id=project_id,
            build_dir=build_dir,
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            test_suites = loop.run_until_complete(
                test_discovery_service.discover_tests(
                    build_dir=build_dir,
                    source_dir=source_dir,
                )
            )
        finally:
            loop.close()

        # 注册测试
        registry = test_registry_manager.get_registry(project_id)
        all_tests = []
        for suite in test_suites:
            test_metas = registry.register_suite(suite)
            all_tests.extend([t.name for t in test_metas])

        logger.info(
            "test_discovery_completed",
            project_id=project_id,
            total_suites=len(test_suites),
            total_tests=len(all_tests),
        )

        return {
            "status": "success",
            "total_suites": len(test_suites),
            "total_tests": len(all_tests),
            "tests": all_tests,
            "project_id": project_id,
        }

    except Exception as e:
        logger.error(
            "test_discovery_failed",
            project_id=project_id,
            error=str(e),
            exc_info=True,
        )

        return {
            "status": "failed",
            "error": str(e),
            "project_id": project_id,
        }


@celery_app.task(name="src.tasks.test_tasks.collect_coverage")
def collect_coverage(
    project_id: int,
    build_dir: str,
    source_dirs: list,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    收集代码覆盖率任务

    Args:
        project_id: 项目ID
        build_dir: 构建目录
        source_dirs: 源代码目录列表
        output_dir: 输出目录（可选）

    Returns:
        覆盖率数据
    """
    try:
        logger.info(
            "coverage_collection_task_started",
            project_id=project_id,
            build_dir=build_dir,
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            report = loop.run_until_complete(
                coverage_collector.collect_coverage(
                    build_dir=build_dir,
                    source_dirs=source_dirs,
                    output_dir=output_dir,
                )
            )
        finally:
            loop.close()

        if not report:
            return {
                "status": "failed",
                "error": "No coverage data found",
                "project_id": project_id,
            }

        logger.info(
            "coverage_collection_completed",
            project_id=project_id,
            line_percent=report.line_percent,
        )

        return {
            "status": "success",
            "line_percent": report.line_percent,
            "line_covered": report.line_covered,
            "line_total": report.line_total,
            "branch_percent": report.branch_percent,
            "branch_covered": report.branch_covered,
            "branch_total": report.branch_total,
            "function_percent": report.function_percent,
            "function_covered": report.function_covered,
            "function_total": report.function_total,
            "files": {
                file_path: {
                    "line_percent": data.line_percent,
                    "line_covered": data.line_covered,
                    "line_total": data.line_total,
                }
                for file_path, data in report.files.items()
            },
            "project_id": project_id,
        }

    except Exception as e:
        logger.error(
            "coverage_collection_failed",
            project_id=project_id,
            error=str(e),
            exc_info=True,
        )

        return {
            "status": "failed",
            "error": str(e),
            "project_id": project_id,
        }


@celery_app.task(name="src.tasks.test_tasks.get_test_statistics")
def get_test_statistics(project_id: int) -> Dict[str, Any]:
    """
    获取测试统计信息

    Args:
        project_id: 项目ID

    Returns:
        测试统计信息
    """
    try:
        registry = test_registry_manager.get_registry(project_id, create=False)

        if not registry:
            return {
                "status": "not_found",
                "message": f"No test registry found for project {project_id}",
            }

        stats = registry.get_statistics()

        logger.info(
            "test_statistics_retrieved",
            project_id=project_id,
            total_tests=stats["total_tests"],
        )

        return {
            "status": "success",
            **stats,
            "project_id": project_id,
        }

    except Exception as e:
        logger.error(
            "test_statistics_error",
            project_id=project_id,
            error=str(e),
        )

        return {
            "status": "failed",
            "error": str(e),
            "project_id": project_id,
        }


# 导出任务列表
__all__ = [
    "execute_test",
    "discover_tests",
    "collect_coverage",
    "get_test_statistics",
]
