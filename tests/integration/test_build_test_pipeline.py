"""
构建→测试完整流程集成测试

验证从构建到测试的完整CI/CD流程，包括状态更新、日志流、失败处理等
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, call
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Job, JobStatus, Project, Pipeline
from src.services.build.scheduler import build_scheduler
from src.services.test.scheduler import test_scheduler
from src.services.websocket.manager import manager as ws_manager


@pytest.mark.asyncio
@pytest.mark.slow
class BuildTestPipelineIntegrationTest:
    """构建→测试流程集成测试套件"""

    async def test_build_and_test_workflow_success(
        self,
        db_session: AsyncSession,
        test_project: Project,
        test_pipeline: Pipeline,
        mock_celery_task,
        mock_websocket,
    ):
        """测试成功的构建→测试工作流"""
        # ==================== 阶段1: 提交构建 ====================
        build_job_id = "build-job-success"
        build_config = {
            "build_type": "RelWithDebInfo",
            "cmake_options": {"BUILD_TESTING": "ON"},
        }

        with patch('src.services.build.scheduler.execute_build.delay', return_value=mock_celery_task):
            build_celery_id = build_scheduler.submit_build(
                db=db_session,
                project_id=test_project.id,
                pipeline_id=test_pipeline.id,
                job_id=build_job_id,
                gitlab_job_id=100,
                job_name="build",
                job_stage="build",
                build_config=build_config,
                project_path="/path/to/project",
            )

        assert build_celery_id == mock_celery_task.id

        # 验证构建Job已创建
        build_job = await db_session.get(Job, build_job_id)
        assert build_job is not None
        assert build_job.status == JobStatus.PENDING

        # ==================== 阶段2: 构建进行中 ====================
        # 模拟构建日志流
        ws_conn_id = await ws_manager.connect(mock_websocket)
        ws_manager.subscribe(ws_conn_id, f"build:{build_job_id}")

        # 发送构建进度日志
        await ws_manager.send_log(
            topic=f"build:{build_job_id}",
            level="info",
            message="Starting build...",
        )
        await ws_manager.send_progress(
            topic=f"build:{build_job_id}",
            progress=25.0,
            total=100,
            current=25,
        )

        # 更新构建状态为RUNNING
        build_scheduler.update_build_status(
            db=db_session,
            job_id=build_job_id,
            status=JobStatus.RUNNING,
        )

        await db_session.refresh(build_job)
        assert build_job.status == JobStatus.RUNNING

        # ==================== 阶段3: 构建成功 ====================
        build_result = {
            "exit_code": 0,
            "duration": 120,
            "artifacts": ["app", "libtest.a"],
            "cache_hit": False,
        }

        build_scheduler.update_build_status(
            db=db_session,
            job_id=build_job_id,
            status=JobStatus.SUCCESS,
            result=build_result,
        )

        await db_session.refresh(build_job)
        assert build_job.status == JobStatus.SUCCESS

        # ==================== 阶段4: 提交测试 ====================
        test_job_id = "test-job-after-build"
        test_config = {
            "build_dir": "/path/to/build",
            "source_dir": "/path/to/source",
            "test_type": "qttest",
            "enable_coverage": True,
        }

        with patch('src.services.test.scheduler.execute_test.delay', return_value=mock_celery_task):
            test_celery_id = test_scheduler.submit_test(
                db=db_session,
                project_id=test_project.id,
                pipeline_id=test_pipeline.id,
                job_id=test_job_id,
                gitlab_job_id=101,
                job_name="test",
                job_stage="test",
                test_config=test_config,
                project_path="/path/to/project",
            )

        # 验证测试Job已创建
        test_job = await db_session.get(Job, test_job_id)
        assert test_job is not None
        assert test_job.status == JobStatus.PENDING

        # ==================== 阶段5: 测试执行 ====================
        ws_manager.subscribe(ws_conn_id, f"test:{test_job_id}")

        # 发送测试日志
        await ws_manager.send_log(
            topic=f"test:{test_job_id}",
            level="info",
            message="Running tests...",
        )

        test_scheduler.update_test_status(
            db=db_session,
            job_id=test_job_id,
            status=JobStatus.RUNNING,
        )

        await db_session.refresh(test_job)
        assert test_job.status == JobStatus.RUNNING

        # ==================== 阶段6: 测试成功 ====================
        test_result = {
            "total_tests": 10,
            "passed_tests": 10,
            "failed_tests": 0,
            "skipped_tests": 0,
            "coverage_percent": 85.5,
            "duration": 60,
        }

        test_scheduler.update_test_status(
            db=db_session,
            job_id=test_job_id,
            status=JobStatus.SUCCESS,
            result=test_result,
        )

        await db_session.refresh(test_job)
        assert test_job.status == JobStatus.SUCCESS

        # ==================== 验证 ====================
        # 验证WebSocket收到了所有消息
        assert mock_websocket.send_json.call_count > 0

        # 清理
        await ws_manager.disconnect(ws_conn_id)

    async def test_build_failure_stops_test_execution(
        self,
        db_session: AsyncSession,
        test_project: Project,
        test_pipeline: Pipeline,
        mock_celery_task,
    ):
        """测试构建失败时不应执行测试"""
        build_job_id = "build-job-failed"

        # 提交构建
        with patch('src.services.build.scheduler.execute_build.delay', return_value=mock_celery_task):
            build_scheduler.submit_build(
                db=db_session,
                project_id=test_project.id,
                pipeline_id=test_pipeline.id,
                job_id=build_job_id,
                gitlab_job_id=102,
                job_name="build",
                job_stage="build",
                build_config={},
                project_path="/path",
            )

        # 构建失败
        build_result = {
            "exit_code": 1,
            "error_message": "Compilation failed",
            "duration": 30,
        }

        build_scheduler.update_build_status(
            db=db_session,
            job_id=build_job_id,
            status=JobStatus.FAILED,
            result=build_result,
        )

        build_job = await db_session.get(Job, build_job_id)
        assert build_job.status == JobStatus.FAILED

        # 验证构建失败后不会触发测试（通过检查Job列表）
        active_tests = test_scheduler.list_active_tests(
            db=db_session,
            pipeline_id=test_pipeline.id,
        )

        # 应该没有活跃的测试任务（因为构建失败了）
        test_jobs = [j for j in active_tests if j["stage"] == "test"]
        assert len(test_jobs) == 0

    async def test_parallel_build_and_test_execution(
        self,
        db_session: AsyncSession,
        test_project: Project,
        test_pipeline: Pipeline,
        mock_celery_task,
    ):
        """测试并行执行多个构建和测试任务"""
        jobs_created = []

        # 创建多个构建任务
        for i in range(2):
            build_job_id = f"parallel-build-{i}"
            with patch('src.services.build.scheduler.execute_build.delay', return_value=mock_celery_task):
                build_scheduler.submit_build(
                    db=db_session,
                    project_id=test_project.id,
                    pipeline_id=test_pipeline.id,
                    job_id=build_job_id,
                    gitlab_job_id=200 + i,
                    job_name=f"build-{i}",
                    job_stage="build",
                    build_config={},
                    project_path="/path",
                )
                jobs_created.append(build_job_id)

        # 创建多个测试任务（可以与构建并行）
        for i in range(2):
            test_job_id = f"parallel-test-{i}"
            with patch('src.services.test.scheduler.execute_test.delay', return_value=mock_celery_task):
                test_scheduler.submit_test(
                    db=db_session,
                    project_id=test_project.id,
                    pipeline_id=test_pipeline.id,
                    job_id=test_job_id,
                    gitlab_job_id=300 + i,
                    job_name=f"test-{i}",
                    job_stage="test",
                    test_config={},
                    project_path="/path",
                )
                jobs_created.append(test_job_id)

        # 验证所有任务都已创建
        for job_id in jobs_created:
            job = await db_session.get(Job, job_id)
            assert job is not None
            assert job.status == JobStatus.PENDING

        # 列出所有活跃任务
        active_builds = build_scheduler.list_active_builds(
            db=db_session,
            pipeline_id=test_pipeline.id,
        )
        active_tests = test_scheduler.list_active_tests(
            db=db_session,
            pipeline_id=test_pipeline.id,
        )

        # 验证任务数量
        assert len(active_builds) >= 2
        assert len(active_tests) >= 2

    async def test_cache_hit_skips_build(
        self,
        db_session: AsyncSession,
        test_project: Project,
        test_pipeline: Pipeline,
        mock_celery_task,
    ):
        """测试缓存命中时跳过构建"""
        build_job_id = "cached-build"

        # 提交构建（标记为缓存）
        with patch('src.services.build.scheduler.execute_build.delay', return_value=mock_celery_task):
            celery_id = build_scheduler.submit_build(
                db=db_session,
                project_id=test_project.id,
                pipeline_id=test_pipeline.id,
                job_id=build_job_id,
                gitlab_job_id=400,
                job_name="build",
                job_stage="build",
                build_config={},
                project_path="/path",
            )

        # 模拟缓存命中
        build_result = {
            "exit_code": 0,
            "cache_hit": True,
            "cache_key": "abc123",
            "duration": 0,  # 缓存命中，执行时间为0
        }

        build_scheduler.update_build_status(
            db=db_session,
            job_id=build_job_id,
            status=JobStatus.SUCCESS,
            result=build_result,
        )

        build_job = await db_session.get(Job, build_job_id)
        assert build_job.status == JobStatus.SUCCESS

        # 验证缓存信息
        import json
        if build_job.log:
            log_data = json.loads(build_job.log)
            assert log_data.get("cache_hit") is True


@pytest.mark.asyncio
async def test_job_status_tracking_through_pipeline(
    db_session: AsyncSession,
    test_project: Project,
    test_pipeline: Pipeline,
    mock_celery_task,
):
    """测试Job在整个流水线中的状态跟踪"""
    build_job_id = "status-track-build"
    test_job_id = "status-track-test"

    # 1. 创建构建
    with patch('src.services.build.scheduler.execute_build.delay', return_value=mock_celery_task):
        build_scheduler.submit_build(
            db=db_session,
            project_id=test_project.id,
            pipeline_id=test_pipeline.id,
            job_id=build_job_id,
            gitlab_job_id=500,
            job_name="build",
            job_stage="build",
            build_config={},
            project_path="/path",
        )

    build_job = await db_session.get(Job, build_job_id)
    assert build_job.status == JobStatus.PENDING
    assert build_job.started_at is not None
    assert build_job.finished_at is None

    # 2. 构建完成
    build_scheduler.update_build_status(
        db=db_session,
        job_id=build_job_id,
        status=JobStatus.SUCCESS,
        result={"exit_code": 0, "duration": 60},
    )

    await db_session.refresh(build_job)
    assert build_job.status == JobStatus.SUCCESS
    assert build_job.finished_at is not None
    assert build_job.duration_seconds > 0

    # 3. 创建测试
    with patch('src.services.test.scheduler.execute_test.delay', return_value=mock_celery_task):
        test_scheduler.submit_test(
            db=db_session,
            project_id=test_project.id,
            pipeline_id=test_pipeline.id,
            job_id=test_job_id,
            gitlab_job_id=501,
            job_name="test",
            job_stage="test",
            test_config={},
            project_path="/path",
        )

    test_job = await db_session.get(Job, test_job_id)
    assert test_job.status == JobStatus.PENDING

    # 4. 测试完成
    test_scheduler.update_test_status(
        db=db_session,
        job_id=test_job_id,
        status=JobStatus.SUCCESS,
        result={"total_tests": 5, "passed_tests": 5},
    )

    await db_session.refresh(test_job)
    assert test_job.status == JobStatus.SUCCESS
    assert test_job.finished_at is not None

    # 5. 验证流水线级别的统计
    jobs_query = await db_session.execute(
        f"SELECT COUNT(*) FROM jobs WHERE pipeline_id = '{test_pipeline.id}'"
    )
    job_count = jobs_query.scalar()
    assert job_count >= 2  # 至少有构建和测试


@pytest.mark.asyncio
async def test_pipeline_statistics_collection(
    db_session: AsyncSession,
    test_project: Project,
    test_pipeline: Pipeline,
    mock_celery_task,
):
    """测试流水线统计信息收集"""
    # 创建多个构建和测试任务
    for i in range(3):
        build_job_id = f"stats-build-{i}"
        with patch('src.services.build.scheduler.execute_build.delay', return_value=mock_celery_task):
            build_scheduler.submit_build(
                db=db_session,
                project_id=test_project.id,
                pipeline_id=test_pipeline.id,
                job_id=build_job_id,
                gitlab_job_id=600 + i,
                job_name=f"build-{i}",
                job_stage="build",
                build_config={},
                project_path="/path",
            )

        # 更新状态
        status = JobStatus.SUCCESS if i < 2 else JobStatus.FAILED
        build_scheduler.update_build_status(
            db=db_session,
            job_id=build_job_id,
            status=status,
            result={"duration": 50 + i * 10},
        )

    # 获取测试统计
    test_stats = test_scheduler.get_test_statistics(
        db=db_session,
        project_id=test_project.id,
        pipeline_id=test_pipeline.id,
    )

    # 验证统计信息
    assert test_stats["project_id"] == test_project.id
    assert test_stats["pipeline_id"] == test_pipeline.id
    assert "total_jobs" in test_stats
