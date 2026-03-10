"""
测试调度器集成测试

验证TestScheduler与数据库、Celery的集成
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.test.scheduler import test_scheduler, TestScheduler
from src.db.models import Job, JobStatus, Project, Pipeline


@pytest.mark.asyncio
class TestSchedulerIntegration:
    """测试调度器集成测试套件"""

    async def test_submit_test_creates_job_record(
        self,
        db_session: AsyncSession,
        test_project: Project,
        test_pipeline: Pipeline,
        mock_celery_task,
    ):
        """测试提交测试任务创建Job记录"""
        job_id = "test-job-submit-1"
        test_config = {
            "build_dir": "/path/to/build",
            "source_dir": "/path/to/source",
            "test_type": "qttest",
            "enable_coverage": True,
        }

        # Mock Celery任务
        with patch('src.services.test.scheduler.execute_test.delay', return_value=mock_celery_task):
            celery_task_id = test_scheduler.submit_test(
                db=db_session,
                project_id=test_project.id,
                pipeline_id=test_pipeline.id,
                job_id=job_id,
                gitlab_job_id=100,
                job_name="integration-test",
                job_stage="test",
                test_config=test_config,
                project_path="/path/to/project",
            )

        # 验证Celery任务ID返回
        assert celery_task_id == mock_celery_task.id

        # 验证Job记录已创建
        job = await db_session.get(Job, job_id)
        assert job is not None
        assert job.id == job_id
        assert job.pipeline_id == test_pipeline.id
        assert job.gitlab_project_id == test_project.id
        assert job.name == "integration-test"
        assert job.stage == "test"
        assert job.status == JobStatus.PENDING
        assert job.celery_task_id == mock_celery_task.id
        assert job.started_at is not None

    async def test_submit_test_updates_existing_job(
        self,
        db_session: AsyncSession,
        test_job: Job,
        mock_celery_task,
    ):
        """测试提交测试任务更新已存在的Job"""
        # 更新job状态为失败
        test_job.status = JobStatus.FAILED
        await db_session.commit()

        # 重新提交
        with patch('src.services.test.scheduler.execute_test.delay', return_value=mock_celery_task):
            celery_task_id = test_scheduler.submit_test(
                db=db_session,
                project_id=test_job.gitlab_project_id,
                pipeline_id=test_job.pipeline_id,
                job_id=test_job.id,
                gitlab_job_id=test_job.gitlab_job_id,
                job_name=test_job.name,
                job_stage="test",
                test_config={},
                project_path="/path",
            )

        # 验证Job已更新为PENDING
        await db_session.refresh(test_job)
        assert test_job.status == JobStatus.PENDING
        assert test_job.celery_task_id == celery_task_id

    async def test_update_test_status(
        self,
        db_session: AsyncSession,
        test_job: Job,
    ):
        """测试更新测试状态"""
        result = {
            "total_tests": 10,
            "passed_tests": 8,
            "failed_tests": 2,
            "skipped_tests": 0,
            "coverage_percent": 85.5,
            "duration": 120,
            "stdout": "Test output...",
            "stderr": "",
        }

        # 更新为成功状态
        success = test_scheduler.update_test_status(
            db=db_session,
            job_id=test_job.id,
            status=JobStatus.SUCCESS,
            result=result,
        )

        assert success is True

        # 验证数据库更新
        await db_session.refresh(test_job)
        assert test_job.status == JobStatus.SUCCESS
        assert test_job.finished_at is not None
        assert test_job.duration_seconds > 0

        # 验证日志包含测试结果
        import json
        log_data = json.loads(test_job.log)
        assert log_data["total_tests"] == 10
        assert log_data["passed_tests"] == 8
        assert log_data["coverage_percent"] == 85.5

    async def test_update_test_status_running(
        self,
        db_session: AsyncSession,
        test_job: Job,
    ):
        """测试更新测试状态为RUNNING"""
        success = test_scheduler.update_test_status(
            db=db_session,
            job_id=test_job.id,
            status=JobStatus.RUNNING,
        )

        assert success is True

        await db_session.refresh(test_job)
        assert test_job.status == JobStatus.RUNNING
        assert test_job.started_at is not None

    async def test_get_test_status(
        self,
        db_session: AsyncSession,
        test_job: Job,
    ):
        """测试获取测试状态"""
        # 设置一些状态
        test_job.status = JobStatus.SUCCESS
        test_job.duration_seconds = 300
        test_job.log = '{"total_tests": 5, "passed_tests": 5}'
        await db_session.commit()

        status = test_scheduler.get_test_status(db_session, test_job.id)

        assert status is not None
        assert status["job_id"] == test_job.id
        assert status["status"] == "success"
        assert status["duration_seconds"] == 300
        assert status["total_tests"] == 5
        assert status["passed_tests"] == 5

    async def test_get_test_status_not_found(
        self,
        db_session: AsyncSession,
    ):
        """测试获取不存在的测试状态"""
        status = test_scheduler.get_test_status(db_session, "non-existent-job")
        assert status is None

    async def test_cancel_test(
        self,
        db_session: AsyncSession,
        test_job: Job,
    ):
        """测试取消测试任务"""
        # 设置为RUNNING状态
        test_job.status = JobStatus.RUNNING
        test_job.started_at = datetime.now()
        await db_session.commit()

        # 添加到活跃任务
        test_scheduler.active_tasks[test_job.id] = "celery-task-123"

        # 取消任务
        success = test_scheduler.cancel_test(db_session, test_job.id)

        assert success is True

        # 验证状态更新
        await db_session.refresh(test_job)
        assert test_job.status == JobStatus.CANCELLED
        assert test_job.finished_at is not None

        # 验证从活跃任务中移除
        assert test_job.id not in test_scheduler.active_tasks

    async def test_cancel_test_invalid_status(
        self,
        db_session: AsyncSession,
        test_job: Job,
    ):
        """测试取消已完成的任务（应该失败）"""
        test_job.status = JobStatus.SUCCESS
        test_job.finished_at = datetime.now()
        await db_session.commit()

        success = test_scheduler.cancel_test(db_session, test_job.id)

        assert success is False

    async def test_list_active_tests(
        self,
        db_session: AsyncSession,
        test_pipeline: Pipeline,
    ):
        """测试列出活跃测试"""
        # 创建多个测试任务
        jobs = []
        for i in range(3):
            job = Job(
                id=f"test-job-active-{i}",
                pipeline_id=test_pipeline.id,
                gitlab_job_id=100 + i,
                gitlab_project_id=test_pipeline.gitlab_project_id,
                name=f"test-job-{i}",
                stage="test",
                status=JobStatus.RUNNING,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(job)
            jobs.append(job)

        await db_session.commit()

        # 列出活跃测试
        active_tests = test_scheduler.list_active_tests(
            db=db_session,
            project_id=test_pipeline.gitlab_project_id,
            pipeline_id=test_pipeline.id,
        )

        # 应该包含我们的3个测试
        assert len(active_tests) >= 3
        job_ids = [t["job_id"] for t in active_tests]
        for i in range(3):
            assert f"test-job-active-{i}" in job_ids

    async def test_list_active_tests_filters_by_stage(
        self,
        db_session: AsyncSession,
        test_pipeline: Pipeline,
    ):
        """测试列出活跃测试按stage过滤"""
        # 创建构建任务（不同stage）
        build_job = Job(
            id="build-job-1",
            pipeline_id=test_pipeline.id,
            gitlab_job_id=200,
            gitlab_project_id=test_pipeline.gitlab_project_id,
            name="build-job",
            stage="build",  # 不是test
            status=JobStatus.RUNNING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(build_job)
        await db_session.commit()

        # 列出活跃测试（应该只返回test stage）
        active_tests = test_scheduler.list_active_tests(db=db_session)

        # 验证build任务不在列表中
        job_ids = [t["job_id"] for t in active_tests]
        assert "build-job-1" not in job_ids

    async def test_get_test_statistics(
        self,
        db_session: AsyncSession,
        test_pipeline: Pipeline,
    ):
        """测试获取测试统计信息"""
        # 创建一些测试任务
        for i in range(5):
            job = Job(
                id=f"test-job-stats-{i}",
                pipeline_id=test_pipeline.id,
                gitlab_job_id=300 + i,
                gitlab_project_id=test_pipeline.gitlab_project_id,
                name=f"test-job-{i}",
                stage="test",
                status=JobStatus.SUCCESS if i < 4 else JobStatus.FAILED,
                duration_seconds=100 + i * 10,
                log=f'{{"total_tests": 10, "passed_tests": {10-i}, "failed_tests": {i}}}',
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(job)

        await db_session.commit()

        # 获取统计
        stats = test_scheduler.get_test_statistics(
            db=db_session,
            project_id=test_pipeline.gitlab_project_id,
            pipeline_id=test_pipeline.id,
        )

        assert stats["total_jobs"] == 5
        assert stats["success_jobs"] == 4
        assert stats["failed_jobs"] == 1
        assert stats["total_tests"] == 50
        assert stats["avg_duration_seconds"] > 0

    async def test_submit_tests_batch(
        self,
        db_session: AsyncSession,
        test_project: Project,
        test_pipeline: Pipeline,
        mock_celery_task,
    ):
        """测试批量提交测试任务"""
        jobs = [
            {
                "job_id": f"batch-job-{i}",
                "gitlab_job_id": 400 + i,
                "job_name": f"batch-test-{i}",
                "job_stage": "test",
                "test_config": {"test_type": "qttest"},
                "project_path": "/path",
            }
            for i in range(3)
        ]

        with patch('src.services.test.scheduler.execute_test.delay', return_value=mock_celery_task):
            task_ids = test_scheduler.submit_tests_batch(
                db=db_session,
                project_id=test_project.id,
                pipeline_id=test_pipeline.id,
                jobs=jobs,
            )

        # 验证所有任务都已提交
        assert len(task_ids) == 3
        for i in range(3):
            assert f"batch-job-{i}" in task_ids

        # 验证所有Job都已创建
        for i in range(3):
            job = await db_session.get(Job, f"batch-job-{i}")
            assert job is not None
            assert job.status == JobStatus.PENDING


@pytest.mark.asyncio
async def test_scheduler_persistence_across_operations(
    db_session: AsyncSession,
    test_project: Project,
    test_pipeline: Pipeline,
    mock_celery_task,
):
    """测试调度器在多个操作间的数据持久化"""
    job_id = "persist-test-job"

    # 1. 提交任务
    with patch('src.services.test.scheduler.execute_test.delay', return_value=mock_celery_task):
        celery_id = test_scheduler.submit_test(
            db=db_session,
            project_id=test_project.id,
            pipeline_id=test_pipeline.id,
            job_id=job_id,
            gitlab_job_id=500,
            job_name="persist-test",
            job_stage="test",
            test_config={},
            project_path="/path",
        )

    # 2. 更新为运行中
    test_scheduler.update_test_status(
        db=db_session,
        job_id=job_id,
        status=JobStatus.RUNNING,
    )

    # 3. 更新为成功
    result = {
        "total_tests": 5,
        "passed_tests": 5,
        "failed_tests": 0,
        "skipped_tests": 0,
        "duration": 60,
    }
    test_scheduler.update_test_status(
        db=db_session,
        job_id=job_id,
        status=JobStatus.SUCCESS,
        result=result,
    )

    # 4. 验证最终状态
    job = await db_session.get(Job, job_id)
    assert job.status == JobStatus.SUCCESS
    assert job.celery_task_id == celery_id

    log_data = __import__('json').loads(job.log)
    assert log_data["total_tests"] == 5
    assert log_data["passed_tests"] == 5
