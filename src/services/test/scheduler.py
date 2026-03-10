"""
测试任务调度器

负责创建测试任务记录、提交Celery任务、跟踪任务状态。
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ...tasks.test_tasks import execute_test
from ...db.models import Job, JobStatus, Pipeline, Project
from ....core.logging.logger import get_logger

logger = get_logger(__name__)


class TestScheduler:
    """
    测试任务调度器

    负责调度和管理测试任务：
    - 创建Job记录
    - 提交Celery任务
    - 关联Celery任务ID
    - 更新测试状态
    - 收集测试结果
    """

    def __init__(self):
        self.active_tasks: Dict[str, str] = {}  # {job_id: celery_task_id}

    def submit_test(
        self,
        db: Session,
        project_id: int,
        pipeline_id: str,
        job_id: str,
        gitlab_job_id: int,
        job_name: str,
        job_stage: str,
        test_config: Dict[str, Any],
        project_path: str,
    ) -> str:
        """
        提交测试任务到Celery队列

        Args:
            db: 数据库会话
            project_id: 项目ID
            pipeline_id: 流水线ID
            job_id: 作业ID
            gitlab_job_id: GitLab作业ID
            job_name: 作业名称
            job_stage: 作业阶段
            test_config: 测试配置
                - build_dir: 构建目录
                - source_dir: 源代码目录
                - test_type: 测试类型 (qttest, googletest, catch2)
                - test_filter: 测试过滤器
                - parallel_jobs: 并行作业数
                - timeout: 超时时间
                - enable_coverage: 是否启用覆盖率
                - environment: 环境变量
            project_path: 项目路径

        Returns:
            Celery任务ID
        """
        try:
            # 1. 创建或更新Job记录
            job = db.query(Job).filter(Job.id == job_id).first()

            if not job:
                job = Job(
                    id=job_id,
                    pipeline_id=pipeline_id,
                    gitlab_job_id=gitlab_job_id,
                    gitlab_project_id=project_id,
                    name=job_name,
                    stage=job_stage,
                    status=JobStatus.PENDING,
                    retry_count=0,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                db.add(job)
            else:
                # 更新现有作业
                job.status = JobStatus.PENDING
                job.updated_at = datetime.now()

            db.commit()
            db.refresh(job)

            logger.info(
                "test_job_created",
                job_id=job_id,
                pipeline_id=pipeline_id,
                project_id=project_id,
                test_type=test_config.get("test_type", "qttest"),
            )

            # 2. 提交Celery任务
            celery_task = execute_test.delay(
                project_id=project_id,
                pipeline_id=pipeline_id,
                job_id=job_id,
                test_config=test_config,
                project_path=project_path,
            )

            celery_task_id = celery_task.id

            # 3. 更新Job记录
            job.celery_task_id = celery_task_id
            job.started_at = datetime.now()
            db.commit()

            # 4. 记录活跃任务
            self.active_tasks[job_id] = celery_task_id

            logger.info(
                "test_task_submitted",
                job_id=job_id,
                celery_task_id=celery_task_id,
                pipeline_id=pipeline_id,
                test_type=test_config.get("test_type", "qttest"),
            )

            return celery_task_id

        except Exception as e:
            logger.error(
                "test_task_submission_failed",
                job_id=job_id,
                error=str(e),
                exc_info=True,
            )
            db.rollback()
            raise

    def submit_tests_batch(
        self,
        db: Session,
        project_id: int,
        pipeline_id: str,
        jobs: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        """
        批量提交测试任务

        Args:
            db: 数据库会话
            project_id: 项目ID
            pipeline_id: 流水线ID
            jobs: 作业列表，每个作业包含:
                - job_id: 作业ID
                - gitlab_job_id: GitLab作业ID
                - job_name: 作业名称
                - job_stage: 作业阶段
                - test_config: 测试配置
                - project_path: 项目路径

        Returns:
            {job_id: celery_task_id} 字典
        """
        task_ids = {}

        for job_spec in jobs:
            try:
                celery_task_id = self.submit_test(
                    db=db,
                    project_id=project_id,
                    pipeline_id=pipeline_id,
                    job_id=job_spec["job_id"],
                    gitlab_job_id=job_spec["gitlab_job_id"],
                    job_name=job_spec["job_name"],
                    job_stage=job_spec.get("job_stage", "test"),
                    test_config=job_spec["test_config"],
                    project_path=job_spec["project_path"],
                )
                task_ids[job_spec["job_id"]] = celery_task_id

            except Exception as e:
                logger.error(
                    "batch_test_submission_failed",
                    job_id=job_spec.get("job_id"),
                    error=str(e),
                )
                # 继续提交其他任务，不中断批处理

        return task_ids

    def update_test_status(
        self,
        db: Session,
        job_id: str,
        status: JobStatus,
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        更新测试状态

        Args:
            db: 数据库会话
            job_id: 作业ID
            status: 新状态
            result: 测试结果（可选）
                - status: 测试状态
                - total_tests: 总测试数
                - passed_tests: 通过测试数
                - failed_tests: 失败测试数
                - skipped_tests: 跳过测试数
                - coverage_percent: 覆盖率百分比
                - duration: 执行时间
                - stdout: 标准输出
                - stderr: 标准错误输出

        Returns:
            是否更新成功
        """
        try:
            job = db.query(Job).filter(Job.id == job_id).first()

            if not job:
                logger.warning("test_job_not_found", job_id=job_id)
                return False

            # 更新状态
            job.status = status
            job.updated_at = datetime.now()

            # 根据状态设置时间戳
            if status == JobStatus.RUNNING:
                if not job.started_at:
                    job.started_at = datetime.now()

            elif status in [JobStatus.SUCCESS, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.TIMEOUT]:
                if not job.finished_at:
                    job.finished_at = datetime.now()

                # 计算持续时间
                if job.started_at:
                    duration = (job.finished_at - job.started_at).total_seconds()
                    job.duration_seconds = int(duration)

            # 如果有结果，更新日志和附加信息
            if result:
                # 保存测试日志
                log_data = {
                    "status": status.value,
                    "total_tests": result.get("total_tests", 0),
                    "passed_tests": result.get("passed_tests", 0),
                    "failed_tests": result.get("failed_tests", 0),
                    "skipped_tests": result.get("skipped_tests", 0),
                    "coverage_percent": result.get("coverage_percent"),
                    "duration": result.get("duration"),
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                }

                # 合并现有日志（如果有celery_task_id等）
                if job.log:
                    try:
                        existing_log = json.loads(job.log)
                        if isinstance(existing_log, dict):
                            existing_log.update(log_data)
                            log_data = existing_log
                    except (json.JSONDecodeError, TypeError):
                        pass

                job.log = json.dumps(log_data)

            db.commit()
            db.refresh(job)

            # 清理活跃任务记录
            if job_id in self.active_tasks and status in [
                JobStatus.SUCCESS,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
                JobStatus.TIMEOUT,
            ]:
                del self.active_tasks[job_id]

            logger.info(
                "test_job_status_updated",
                job_id=job_id,
                status=status.value,
                total_tests=log_data.get("total_tests") if result else None,
                passed_tests=log_data.get("passed_tests") if result else None,
                failed_tests=log_data.get("failed_tests") if result else None,
                duration=job.duration_seconds,
            )

            return True

        except Exception as e:
            logger.error(
                "test_status_update_failed",
                job_id=job_id,
                error=str(e),
                exc_info=True,
            )
            db.rollback()
            return False

    def get_test_status(
        self,
        db: Session,
        job_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        获取测试状态

        Args:
            db: 数据库会话
            job_id: 作业ID

        Returns:
            测试状态信息或None
        """
        try:
            job = db.query(Job).filter(Job.id == job_id).first()

            if not job:
                return None

            status_info = {
                "job_id": job.id,
                "pipeline_id": job.pipeline_id,
                "status": job.status.value,
                "stage": job.stage,
                "name": job.name,
                "duration_seconds": job.duration_seconds,
                "retry_count": job.retry_count,
                "celery_task_id": job.celery_task_id,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            }

            # 解析日志中的附加信息（如果有）
            if job.log:
                try:
                    log_data = json.loads(job.log)
                    if isinstance(log_data, dict):
                        status_info["details"] = log_data
                        # 提取常用字段到顶层
                        if "total_tests" in log_data:
                            status_info["total_tests"] = log_data["total_tests"]
                        if "passed_tests" in log_data:
                            status_info["passed_tests"] = log_data["passed_tests"]
                        if "failed_tests" in log_data:
                            status_info["failed_tests"] = log_data["failed_tests"]
                        if "coverage_percent" in log_data:
                            status_info["coverage_percent"] = log_data["coverage_percent"]
                except (json.JSONDecodeError, TypeError):
                    pass

            return status_info

        except Exception as e:
            logger.error(
                "get_test_status_failed",
                job_id=job_id,
                error=str(e),
                exc_info=True,
            )
            return None

    def cancel_test(
        self,
        db: Session,
        job_id: str,
    ) -> bool:
        """
        取消测试任务

        Args:
            db: 数据库会话
            job_id: 作业ID

        Returns:
            是否成功取消
        """
        try:
            job = db.query(Job).filter(Job.id == job_id).first()

            if not job:
                logger.warning("cancel_test_job_not_found", job_id=job_id)
                return False

            # 只能取消pending或running的任务
            if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
                logger.warning(
                    "cancel_test_invalid_status",
                    job_id=job_id,
                    status=job.status.value,
                )
                return False

            # 获取Celery任务ID
            celery_task_id = job.celery_task_id

            if not celery_task_id and job_id in self.active_tasks:
                celery_task_id = self.active_tasks[job_id]

            # 更新状态
            job.status = JobStatus.CANCELLED
            job.finished_at = datetime.now()
            if job.started_at:
                job.duration_seconds = int((job.finished_at - job.started_at).total_seconds())
            db.commit()

            # 清理活跃任务
            if job_id in self.active_tasks:
                del self.active_tasks[job_id]

            # TODO: 实际取消Celery任务
            # from ...tasks.test_tasks import cancel_test as cancel_test_task
            # if celery_task_id:
            #     cancel_test_task.delay(job_id)

            logger.info("test_job_cancelled", job_id=job_id)

            return True

        except Exception as e:
            logger.error(
                "cancel_test_failed",
                job_id=job_id,
                error=str(e),
                exc_info=True,
            )
            db.rollback()
            return False

    def list_active_tests(
        self,
        db: Session,
        project_id: Optional[int] = None,
        pipeline_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        列出活跃的测试任务

        Args:
            db: 数据库会话
            project_id: 项目ID（可选）
            pipeline_id: 流水线ID（可选）

        Returns:
            活跃测试列表
        """
        try:
            query = db.query(Job).filter(
                Job.status.in_([JobStatus.PENDING, JobStatus.RUNNING]),
                Job.stage == "test",  # 只返回测试任务
            )

            if project_id:
                query = query.filter(Job.gitlab_project_id == project_id)

            if pipeline_id:
                query = query.filter(Job.pipeline_id == pipeline_id)

            jobs = query.order_by(Job.created_at.desc()).all()

            return [
                {
                    "job_id": job.id,
                    "pipeline_id": job.pipeline_id,
                    "status": job.status.value,
                    "stage": job.stage,
                    "name": job.name,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                }
                for job in jobs
            ]

        except Exception as e:
            logger.error(
                "list_active_tests_failed",
                project_id=project_id,
                pipeline_id=pipeline_id,
                error=str(e),
                exc_info=True,
            )
            return []

    def get_test_statistics(
        self,
        db: Session,
        project_id: int,
        pipeline_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取测试统计信息

        Args:
            db: 数据库会话
            project_id: 项目ID
            pipeline_id: 流水线ID（可选）

        Returns:
            测试统计信息
        """
        try:
            query = db.query(Job).filter(
                Job.gitlab_project_id == project_id,
                Job.stage == "test",
            )

            if pipeline_id:
                query = query.filter(Job.pipeline_id == pipeline_id)

            jobs = query.all()

            total_jobs = len(jobs)
            success_jobs = sum(1 for j in jobs if j.status == JobStatus.SUCCESS)
            failed_jobs = sum(1 for j in jobs if j.status == JobStatus.FAILED)
            running_jobs = sum(1 for j in jobs if j.status == JobStatus.RUNNING)
            pending_jobs = sum(1 for j in jobs if j.status == JobStatus.PENDING)

            # 计算平均通过率等（从日志中提取）
            total_tests = 0
            total_passed = 0
            total_failed = 0
            total_skipped = 0
            jobs_with_results = 0

            for job in jobs:
                if job.log:
                    try:
                        log_data = json.loads(job.log)
                        if isinstance(log_data, dict) and "total_tests" in log_data:
                            total_tests += log_data.get("total_tests", 0)
                            total_passed += log_data.get("passed_tests", 0)
                            total_failed += log_data.get("failed_tests", 0)
                            total_skipped += log_data.get("skipped_tests", 0)
                            jobs_with_results += 1
                    except (json.JSONDecodeError, TypeError):
                        pass

            pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
            avg_duration = (
                sum(j.duration_seconds for j in jobs if j.duration_seconds)
                / total_jobs
                if total_jobs > 0
                else 0
            )

            return {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "total_jobs": total_jobs,
                "success_jobs": success_jobs,
                "failed_jobs": failed_jobs,
                "running_jobs": running_jobs,
                "pending_jobs": pending_jobs,
                "total_tests": total_tests,
                "total_passed": total_passed,
                "total_failed": total_failed,
                "total_skipped": total_skipped,
                "pass_rate": round(pass_rate, 2),
                "avg_duration_seconds": round(avg_duration, 2),
                "jobs_with_results": jobs_with_results,
            }

        except Exception as e:
            logger.error(
                "get_test_statistics_failed",
                project_id=project_id,
                pipeline_id=pipeline_id,
                error=str(e),
                exc_info=True,
            )
            return {}


# 全局单例
test_scheduler = TestScheduler()
