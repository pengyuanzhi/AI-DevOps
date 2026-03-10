"""
SQLAlchemy database models
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float, Text,
    ForeignKey, Index, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class PipelineStatus(str, enum.Enum):
    """Pipeline status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class JobStatus(str, enum.Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class UserRole(str, enum.Enum):
    """User role enumeration"""
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class User(Base):
    """User model"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gitlab_user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role", create_constraint=True),
        nullable=False,
        default=UserRole.DEVELOPER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role.value}')>"


class Project(Base):
    """Project model"""
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gitlab_project_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gitlab_url: Mapped[str] = mapped_column(String(500), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(100), nullable=False, default="main", server_default="main")
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    pipelines: Mapped[List["Pipeline"]] = relationship(
        "Pipeline",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    build_configs: Mapped[List["BuildConfig"]] = relationship(
        "BuildConfig",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    test_suites: Mapped[List["TestSuite"]] = relationship(
        "TestSuite",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    code_reviews: Mapped[List["CodeReview"]] = relationship(
        "CodeReview",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    ai_usage_logs: Mapped[List["AIUsageLog"]] = relationship(
        "AIUsageLog",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}', gitlab_project_id={self.gitlab_project_id})>"


class Pipeline(Base):
    """Pipeline model"""
    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    gitlab_pipeline_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    gitlab_project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    gitlab_mr_iid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[PipelineStatus] = mapped_column(
        SQLEnum(PipelineStatus, name="pipeline_status", create_constraint=True),
        nullable=False,
        index=True
    )
    ref: Mapped[str] = mapped_column(String(255), nullable=False)
    sha: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="pipelines")
    jobs: Mapped[List["Job"]] = relationship(
        "Job",
        back_populates="pipeline",
        cascade="all, delete-orphan"
    )
    test_runs: Mapped[List["TestRun"]] = relationship(
        "TestRun",
        back_populates="pipeline",
        cascade="all, delete-orphan"
    )

    # Foreign key constraint
    __table_args__ = (
        Index("ix_pipelines_gitlab_project_id", "gitlab_project_id"),
        Index("ix_pipelines_status", "status"),
        Index("ix_pipelines_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Pipeline(id='{self.id}', status='{self.status.value}', ref='{self.ref}')>"


class Job(Base):
    """Job model"""
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    pipeline_id: Mapped[str] = mapped_column(String(100), ForeignKey("pipelines.id"), nullable=False, index=True)
    gitlab_job_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    gitlab_project_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    stage: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, name="job_status", create_constraint=True),
        nullable=False,
        index=True
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    cached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    cache_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="jobs")

    # Table arguments
    __table_args__ = (
        Index("ix_jobs_gitlab_job_id", "gitlab_job_id"),
        Index("ix_jobs_pipeline_id", "pipeline_id"),
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_celery_task_id", "celery_task_id"),
    )

    def __repr__(self) -> str:
        return f"<Job(id='{self.id}', name='{self.name}', status='{self.status.value}')>"


class BuildConfig(Base):
    """Build configuration model"""
    __tablename__ = "build_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    build_type: Mapped[str] = mapped_column(String(50), nullable=False, default="RelWithDebInfo", server_default="RelWithDebInfo")
    cmake_options: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    qmake_options: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    env_vars: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="build_configs")

    # Table arguments
    __table_args__ = (
        Index("ix_build_configs_project_id", "project_id"),
    )

    def __repr__(self) -> str:
        return f"<BuildConfig(id={self.id}, name='{self.name}', build_type='{self.build_type}')>"


class TestSuite(Base):
    """Test suite model"""
    __tablename__ = "test_suites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    test_type: Mapped[str] = mapped_column(String(50), nullable=False, default="qttest", server_default="qttest")
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="test_suites")
    test_runs: Mapped[List["TestRun"]] = relationship(
        "TestRun",
        back_populates="test_suite",
        cascade="all, delete-orphan"
    )

    # Table arguments
    __table_args__ = (
        Index("ix_test_suites_project_id", "project_id"),
    )

    def __repr__(self) -> str:
        return f"<TestSuite(id={self.id}, name='{self.name}', test_type='{self.test_type}')>"


class TestRun(Base):
    """Test run model"""
    __tablename__ = "test_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_id: Mapped[str] = mapped_column(String(100), ForeignKey("pipelines.id"), nullable=False, index=True)
    test_suite_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_suites.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    total_tests: Mapped[int] = mapped_column(Integer, nullable=False)
    passed_tests: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    failed_tests: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    skipped_tests: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    coverage_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    # Relationships
    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="test_runs")
    test_suite: Mapped["TestSuite"] = relationship("TestSuite", back_populates="test_runs")

    # Table arguments
    __table_args__ = (
        Index("ix_test_runs_pipeline_id", "pipeline_id"),
        Index("ix_test_runs_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<TestRun(id={self.id}, status='{self.status}', passed={self.passed_tests}/{self.total_tests})>"


class CodeReview(Base):
    """Code review model"""
    __tablename__ = "code_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    mr_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    memory_safety: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    performance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    modern_cpp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    thread_safety: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    code_style: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_issues: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    critical_issues: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    warning_issues: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    info_issues: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    filtered_issues: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="code_reviews")
    code_issues: Mapped[List["CodeIssue"]] = relationship(
        "CodeIssue",
        back_populates="review",
        cascade="all, delete-orphan"
    )

    # Table arguments
    __table_args__ = (
        Index("ix_code_reviews_project_id", "project_id"),
        Index("ix_code_reviews_mr_id", "mr_id"),
    )

    def __repr__(self) -> str:
        return f"<CodeReview(id={self.id}, overall_score={self.overall_score}, total_issues={self.total_issues})>"


class CodeIssue(Base):
    """Code issue model"""
    __tablename__ = "code_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(Integer, ForeignKey("code_reviews.id"), nullable=False, index=True)
    tool: Mapped[str] = mapped_column(String(50), nullable=False)  # clang-tidy, cppcheck
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    line: Mapped[int] = mapped_column(Integer, nullable=False)
    column: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rule_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_false_positive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    # Relationships
    review: Mapped["CodeReview"] = relationship("CodeReview", back_populates="code_issues")

    # Table arguments
    __table_args__ = (
        Index("ix_code_issues_review_id", "review_id"),
        Index("ix_code_issues_file_path", "file_path"),
        Index("ix_code_issues_severity", "severity"),
    )

    def __repr__(self) -> str:
        return f"<CodeIssue(id={self.id}, tool='{self.tool}', severity='{self.severity}', file_path='{self.file_path}')>"


class AIUsageLog(Base):
    """AI usage log model for cost tracking"""
    __tablename__ = "ai_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    feature: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # test_selection, code_review, etc.
    model_provider: Mapped[str] = mapped_column(String(50), nullable=False)  # zhipu, qwen
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_estimate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="ai_usage_logs")

    # Table arguments
    __table_args__ = (
        Index("ix_ai_usage_logs_project_id", "project_id"),
        Index("ix_ai_usage_logs_feature", "feature"),
        Index("ix_ai_usage_logs_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AIUsageLog(id={self.id}, feature='{self.feature}', model='{self.model_name}', tokens={self.tokens_used})>"
