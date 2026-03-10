"""
GitLab服务层

处理GitLab相关的业务逻辑。
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from ..integrations.gitlab.client import gitlab_client
from ..db.session import get_db_session
from ..db.models import Project, Pipeline, Job, User
from ..utils.logger import get_logger

logger = get_logger(__name__)


class GitLabService:
    """GitLab服务"""

    def __init__(self):
        self.client = gitlab_client

    async def sync_projects(self, db: Session) -> List[Project]:
        """从GitLab同步项目列表"""
        gitlab_projects = await self.client.get_projects()
        
        synced_projects = []
        for gp in gitlab_projects:
            project = db.query(Project).filter(
                Project.gitlab_project_id == gp["id"]
            ).first()
            
            if not project:
                # 创建新项目
                project = Project(
                    gitlab_project_id=gp["id"],
                    name=gp["name"],
                    description=gp.get("description"),
                    gitlab_url=gp["web_url"],
                    default_branch=gp.get("default_branch", "main"),
                    config={
                        "ci_config_path": gp.get("ci_config_path", ".gitlab-ci.yml"),
                        "default_branch": gp.get("default_branch", "main"),
                    },
                )
                db.add(project)
                logger.info("project_created", id=project.id, name=project.name)
            else:
                # 更新现有项目
                project.name = gp["name"]
                project.description = gp.get("description")
                project.gitlab_url = gp["web_url"]
                project.default_branch = gp.get("default_branch", "main")
                project.config["ci_config_path"] = gp.get("ci_config_path", ".gitlab-ci.yml")
                project.updated_at = datetime.utcnow()
                logger.info("project_updated", id=project.id, name=project.name)
            
            db.commit()
            db.refresh(project)
            synced_projects.append(project)
        
        return synced_projects

    async def sync_project(self, db: Session, gitlab_project_id: int) -> Optional[Project]:
        """同步单个项目"""
        gp = await self.client.get_project(gitlab_project_id)
        if not gp:
            return None
        
        project = db.query(Project).filter(
            Project.gitlab_project_id == gp["id"]
        ).first()
        
        if not project:
            project = Project(
                gitlab_project_id=gp["id"],
                name=gp["name"],
                description=gp.get("description"),
                gitlab_url=gp["web_url"],
                default_branch=gp.get("default_branch", "main"),
                config={},
            )
            db.add(project)
        else:
            project.name = gp["name"]
            project.description = gp.get("description")
            project.gitlab_url = gp["web_url"]
            project.default_branch = gp.get("default_branch", "main")
            project.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(project)
        return project

    async def sync_pipelines(self, db: Session, gitlab_project_id: int) -> List[Pipeline]:
        """同步项目的流水线列表"""
        gitlab_pipelines = await self.client.get_pipelines(gitlab_project_id)
        
        synced_pipelines = []
        for gp in gitlab_pipelines:
            pipeline = db.query(Pipeline).filter(
                Pipeline.gitlab_pipeline_id == gp["id"]
            ).first()
            
            if not pipeline:
                # 创建新流水线
                pipeline = Pipeline(
                    gitlab_pipeline_id=gp["id"],
                    gitlab_project_id=gitlab_project_id,
                    gitlab_mr_iid=gp.get("merge_request"),
                    status=gp["status"],
                    ref=gp["ref"],
                    sha=gp["sha"],
                    source=gp["source"],
                    duration_seconds=gp.get("duration"),
                    created_at=datetime.fromisoformat(gp["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(gp["updated_at"].replace("Z", "+00:00")),
                    started_at=datetime.fromisoformat(gp["started_at"]) if gp.get("started_at") else None,
                    finished_at=datetime.fromisoformat(gp["finished_at"]) if gp.get("finished_at") else None,
                )
                db.add(pipeline)
                logger.info("pipeline_created", id=pipeline.id, status=pipeline.status)
            else:
                # 更新现有流水线
                pipeline.status = gp["status"]
                pipeline.duration_seconds = gp.get("duration")
                pipeline.updated_at = datetime.fromisoformat(gp["updated_at"].replace("Z", "+00:00"))
                pipeline.started_at = datetime.fromisoformat(gp["started_at"]) if gp.get("started_at") else None
                pipeline.finished_at = datetime.fromisoformat(gp["finished_at"]) if gp.get("finished_at") else None
                logger.info("pipeline_updated", id=pipeline.id, status=pipeline.status)
            
            db.commit()
            db.refresh(pipeline)
            synced_pipelines.append(pipeline)
        
        return synced_pipelines

    async def sync_pipeline_jobs(self, db: Session, pipeline: Pipeline) -> List[Job]:
        """同步流水线的作业列表"""
        gitlab_jobs = await self.client.get_pipeline_jobs(
            pipeline.gitlab_project_id,
            pipeline.gitlab_pipeline_id,
        )
        
        synced_jobs = []
        for gj in gitlab_jobs:
            job = db.query(Job).filter(
                Job.gitlab_job_id == gj["id"]
            ).first()
            
            if not job:
                # 创建新作业
                job = Job(
                    gitlab_job_id=gj["id"],
                    pipeline_id=pipeline.id,
                    gitlab_project_id=pipeline.gitlab_project_id,
                    name=gj["name"],
                    stage=gj["stage"],
                    status=gj["status"],
                    duration_seconds=gj.get("duration"),
                    retry_count=gj.get("retry_count", 0),
                    created_at=datetime.fromisoformat(gj["created_at"].replace("Z", "+00:00")),
                    started_at=datetime.fromisoformat(gj["started_at"]) if gj.get("started_at") else None,
                    finished_at=datetime.fromisoformat(gj["finished_at"]) if gj.get("finished_at") else None,
                )
                db.add(job)
                logger.info("job_created", id=job.id, name=job.name, status=job.status)
            else:
                # 更新现有作业
                job.status = gj["status"]
                job.duration_seconds = gj.get("duration")
                job.retry_count = gj.get("retry_count", 0)
                job.updated_at = datetime.fromisoformat(gj["updated_at"].replace("Z", "+00:00"))
                job.started_at = datetime.fromisoformat(gj["started_at"]) if gj.get("started_at") else None
                job.finished_at = datetime.fromisoformat(gj["finished_at"]) if gj.get("finished_at") else None
                logger.info("job_updated", id=job.id, name=job.name, status=job.status)
            
            db.commit()
            db.refresh(job)
            synced_jobs.append(job)
        
        return synced_jobs

    async def sync_user(self, db: Session, gitlab_user_id: int) -> Optional[User]:
        """同步GitLab用户"""
        gitlab_user = await self.client.get_user(gitlab_user_id)
        if not gitlab_user:
            return None
        
        user = db.query(User).filter(
            User.gitlab_user_id == gitlab_user_id
        ).first()
        
        if not user:
            # 创建新用户
            user = User(
                gitlab_user_id=gitlab_user["id"],
                username=gitlab_user["username"],
                email=gitlab_user["email"],
                role="developer",  # 默认角色
            )
            db.add(user)
            logger.info("user_created", id=user.id, username=user.username)
        else:
            # 更新现有用户
            user.username = gitlab_user["username"]
            user.email = gitlab_user["email"]
            logger.info("user_updated", id=user.id, username=user.username)
        
        db.commit()
        db.refresh(user)
        return user


# 全局单例
gitlab_service = GitLabService()
