"""
Celery构建任务

提供异步构建执行的Celery任务。
"""

import os
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from celery import current_task

from .celery_app import celery_app
from ..services.build.executor import BuildExecutorService, BuildRequest, BuildResult, BuildStatus
from ..services.build.log_streamer import build_log_stream_manager
from ..services.build.status_tracker import build_status_tracker_manager, BuildStage
from ..services.build.service import build_service
from ..core.logging.logger import get_logger

logger = get_logger(__name__)


# 全局构建执行器服务实例
build_executor_service = BuildExecutorService()


@celery_app.task(bind=True, max_retries=3, name="src.tasks.build_tasks.execute_build")
def execute_build(
    self,
    project_id: str,
    pipeline_id: str,
    job_id: str,
    build_config: Dict[str, Any],
    project_path: str,
) -> Dict[str, Any]:
    """
    执行构建任务的Celery任务

    Args:
        project_id: 项目ID
        pipeline_id: 流水线ID
        job_id: 作业ID
        build_config: 构建配置字典
        project_path: 项目路径

    Returns:
        构建结果字典
    """
    try:
        logger.info(
            "build_task_started",
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
                "message": "Initializing build environment..."
            }
        )

        # 创建构建请求
        request = BuildRequest(
            project_id=project_id,
            pipeline_id=pipeline_id,
            job_id=job_id,
            build_type=build_config.get("build_type", "Release"),
            parallel_jobs=build_config.get("parallel_jobs", 4),
            enable_ccache=build_config.get("enable_ccache", True),
            cmake_generator=build_config.get("cmake_generator", "Unix Makefiles"),
            environment=build_config.get("environment", {}),
        )

        # 更新进度
        self.update_state(
            state="PROGRESS",
            meta={
                "status": "detecting",
                "progress": 10,
                "message": "Detecting build system..."
            }
        )

        # 在新的事件循环中执行异步构建
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                _execute_build_async(
                    request=request,
                    project_path=project_path,
                    task=self
                )
            )
        finally:
            loop.close()

        logger.info(
            "build_task_completed",
            project_id=project_id,
            pipeline_id=pipeline_id,
            job_id=job_id,
            status=result["status"],
            duration=result["duration"],
        )

        return result

    except Exception as e:
        logger.error(
            "build_task_failed",
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
                "build_task_retrying",
                retry_count=self.request.retries + 1,
                max_retries=self.max_retries,
                countdown=countdown,
            )
            raise self.retry(exc=e, countdown=countdown)

        # 最终失败
        return {
            "status": "failed",
            "error": str(e),
            "exit_code": -1,
            "duration": 0,
            "artifacts": [],
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "job_id": job_id,
        }


async def _execute_build_async(
    request: BuildRequest,
    project_path: str,
    task: current_task
) -> Dict[str, Any]:
    """
    异步执行构建

    Args:
        request: 构建请求
        project_path: 项目路径
        task: Celery任务实例

    Returns:
        构建结果字典
    """
    # 创建日志流处理器
    log_streamer = build_log_stream_manager.create_streamer(
        job_id=request.job_id,
        project_id=int(request.project_id),
        pipeline_id=request.pipeline_id
    )

    # 创建状态跟踪器
    status_tracker = build_status_tracker_manager.create_tracker(
        job_id=request.job_id,
        project_id=int(request.project_id),
        pipeline_id=request.pipeline_id
    )

    # 设置进度回调
    def on_progress_update(stage, progress, message):
        """进度更新回调"""
        loop = asyncio.get_event_loop()
        loop.create_task(
            log_streamer.send_progress(
                progress=progress,
                total=100,
                current=int(progress),
                message=message
            )
        )

    status_tracker.on_progress_update = on_progress_update

    # 开始跟踪
    status_tracker.start()

    # 发送构建开始状态
    await log_streamer.send_status_update("running", message="Build started")
    await log_streamer.stream_info(f"Starting build for {request.job_id}")
    await log_streamer.stream_info(f"Build type: {request.build_type}")
    await log_streamer.stream_info(f"Parallel jobs: {request.parallel_jobs}")

    # 进入准备阶段
    status_tracker.enter_stage(BuildStage.PREPARE, message="Preparing build environment")

    try:
        # 检测构建系统
        build_system = await build_service.auto_detect_build_system(project_path)
        await log_streamer.stream_info(f"Detected build system: {build_system}")
        status_tracker.update_statistics(build_system=build_system)

        # 完成准备阶段
        status_tracker.complete_stage(BuildStage.PREPARE, success=True)

        # 检查缓存
        status_tracker.enter_stage(BuildStage.CONFIGURE, total_steps=2, message="Checking cache")
        status_tracker.update_stage_progress(1, "Calculating cache key")

        cache_key = await build_executor_service._calculate_cache_key(request, project_path)
        cache_hit = await build_executor_service._check_cache(cache_key)

        if cache_hit:
            status_tracker.update_stage_progress(2, "Cache hit, restoring...")
            await log_streamer.stream_info("Cache hit! Restoring from cache...")
            status_tracker.update_statistics(cache_hit=True)

            result = await build_executor_service._restore_from_cache(cache_key, request)
            result.cache_hit = True
            result.duration = time.time() - status_tracker.started_at

            # 完成配置阶段
            status_tracker.complete_stage(BuildStage.CONFIGURE, success=True)

            # 完成跟踪
            status_tracker.finish("success")
            await log_streamer.send_status_update("success", message="Build completed from cache")

            return result.to_dict()

        # 缓存未命中，继续构建
        status_tracker.update_stage_progress(2, "Cache miss, starting build...")
        status_tracker.complete_stage(BuildStage.CONFIGURE, success=True)

        # 创建构建目录
        build_dir = Path(project_path) / "build"
        build_dir.mkdir(exist_ok=True)

        # 进入构建阶段
        status_tracker.enter_stage(
            BuildStage.BUILD,
            total_steps=3,
            message="Compiling source code"
        )

        # 获取执行器
        executor = build_executor_service.executors.get(build_system)
        if not executor:
            error_msg = f"Unsupported build system: {build_system}"
            status_tracker.complete_stage(BuildStage.BUILD, success=False, error=error_msg)
            status_tracker.finish("failed")
            await log_streamer.stream_error(error_msg)

            return {
                "status": "failed",
                "error": error_msg,
                "exit_code": -1,
                "duration": 0,
                "artifacts": [],
                "project_id": request.project_id,
                "pipeline_id": request.pipeline_id,
                "job_id": request.job_id,
            }

        # 执行构建
        status_tracker.update_stage_progress(1, "Executing build commands...")

        log_lines = []
        exit_code = await build_executor_service._run_build_with_streaming(
            executor=executor,
            project_path=project_path,
            build_dir=str(build_dir),
            build_type=request.build_type,
            parallel_jobs=request.parallel_jobs,
            websocket=None,
            log_lines=log_lines,
            log_streamer=log_streamer,
            status_tracker=status_tracker
        )

        status_tracker.update_stage_progress(2, "Build commands completed")
        status_tracker.update_stage_progress(3, "Collecting artifacts...")

        # 收集构建产物
        artifacts = await build_executor_service._collect_artifacts(build_dir)

        # 更新统计
        status_tracker.update_statistics(
            compiled_files=len(artifacts),
            parallel_jobs=request.parallel_jobs
        )

        # 保存日志
        log_file = await build_executor_service._save_build_log(
            f"{request.project_id}_{request.job_id}",
            log_lines
        )

        # 缓存成功的构建
        if exit_code == 0:
            cache_key = await build_executor_service._calculate_cache_key(request, project_path)
            await build_executor_service._save_to_cache(cache_key, build_dir, artifacts)

        status_tracker.update_stage_progress(3, "Build completed")

        # 构建结果
        result = BuildResult(
            status=BuildStatus.SUCCESS if exit_code == 0 else BuildStatus.FAILED,
            exit_code=exit_code,
            duration=time.time() - status_tracker.started_at,
            artifacts=artifacts,
            log_file=log_file,
            error_message=None if exit_code == 0 else f"Build failed with exit code {exit_code}",
            cache_hit=False,
            output_size=sum(art.stat().st_size for art in artifacts if art.exists())
        )

        # 转换为字典格式
        result_dict = {
            "status": result.status.value,
            "exit_code": result.exit_code,
            "duration": result.duration,
            "artifacts": result.artifacts,
            "log_file": result.log_file,
            "error_message": result.error_message,
            "cache_hit": result.cache_hit,
            "output_size": result.output_size,
            "project_id": request.project_id,
            "pipeline_id": request.pipeline_id,
            "job_id": request.job_id,
        }

        # 完成构建阶段
        status_tracker.complete_stage(BuildStage.BUILD, success=(exit_code == 0))

        # 发送构建完成状态和报告
        if result.status == BuildStatus.SUCCESS:
            status_tracker.finish("success")
            await log_streamer.send_status_update("success", message="Build completed successfully")
            await log_streamer.stream_info(f"Artifacts: {len(result.artifacts)} files")
        else:
            status_tracker.finish("failed")
            await log_streamer.send_status_update("failed", message=result.error_message or "Build failed")
            await log_streamer.stream_error(f"Build failed with exit code: {result.exit_code}")

        # 发送统计信息
        stats = status_tracker.get_build_report()
        await log_streamer.stream_info(f"Build statistics: {stats['statistics']}")

        return result_dict

    except Exception as e:
        logger.error("build_execution_exception", job_id=request.job_id, error=str(e), exc_info=True)

        # 完成跟踪
        if status_tracker.current_stage:
            status_tracker.complete_stage(
                status_tracker.current_stage,
                success=False,
                error=str(e)
            )
        status_tracker.finish("failed")

        # 发送错误状态
        await log_streamer.send_status_update("failed", message=f"Build error: {str(e)}")
        await log_streamer.stream_error(f"Build execution error: {str(e)}")

        raise

    finally:
        # 清理资源（保留跟踪器和日志流处理器一段时间以便查询）
        pass


@celery_app.task(name="src.tasks.build_tasks.cancel_build")
def cancel_build(build_id: str) -> Dict[str, Any]:
    """
    取消构建任务

    Args:
        build_id: 构建ID (格式: project_id_job_id)

    Returns:
        取消结果
    """
    try:
        logger.info("cancel_build_requested", build_id=build_id)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(
                build_executor_service.cancel_build(build_id)
            )
        finally:
            loop.close()

        return {
            "status": "success",
            "message": f"Build {build_id} cancelled successfully"
        }

    except Exception as e:
        logger.error("cancel_build_failed", build_id=build_id, error=str(e))
        return {
            "status": "failed",
            "message": str(e)
        }


@celery_app.task(name="src.tasks.build_tasks.cleanup_cache")
def cleanup_cache(max_age_hours: int = 24) -> Dict[str, Any]:
    """
    清理旧的构建缓存

    Args:
        max_age_hours: 缓存最大保留时间（小时）

    Returns:
        清理结果
    """
    try:
        logger.info("cache_cleanup_started", max_age_hours=max_age_hours)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(
                build_executor_service.cleanup_cache(max_age_hours)
            )
        finally:
            loop.close()

        logger.info("cache_cleanup_completed")
        return {
            "status": "success",
            "message": "Cache cleanup completed"
        }

    except Exception as e:
        logger.error("cache_cleanup_failed", error=str(e))
        return {
            "status": "failed",
            "message": str(e)
        }


@celery_app.task(name="src.tasks.build_tasks.get_build_status")
def get_build_status(build_id: str) -> Optional[Dict[str, Any]]:
    """
    获取构建状态

    Args:
        build_id: 构建ID

    Returns:
        构建状态信息或None
    """
    # 检查是否在活跃构建列表中
    if build_id in build_executor_service.active_builds:
        process = build_executor_service.active_builds[build_id]
        return {
            "build_id": build_id,
            "status": "running",
            "pid": process.pid if hasattr(process, 'pid') else None,
        }
    return None


# 导出任务列表
__all__ = [
    "execute_build",
    "cancel_build",
    "cleanup_cache",
    "get_build_status",
]
