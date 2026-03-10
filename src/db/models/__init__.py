"""
数据库模型

定义所有数据库表的SQLAlchemy模型。
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from ...utils.config import settings


class Base(DeclarativeBase):
    """所有模型的基类"""

    pass


class TimestampMixin:
    """时间戳混入类"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class User(Base, TimestampMixin):
    """用户表"""

    __tablename__ = "users"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # GitLab用户信息
    gitlab_user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)

    # 认证信息
    gitlab_access_token: Mapped[Optional[str]] = mapped_column(String(255))  # 加密存储

    # 用户角色
    role: Mapped[str] = mapped_column(
        Enum("admin", "maintainer", "developer", "viewer", name="user_role"),
        default="developer",
        nullable=False,
    )

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 关系
    projects = relationship("Project", back_populates="owner", lazy="dynamic")
    created_pipelines = relationship("Pipeline", back_populates="creator", foreign_keys="Pipeline.creator_id", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"


class Project(Base, TimestampMixin):
    """项目表"""

    __tablename__ = "projects"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # GitLab项目信息
    gitlab_project_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    gitlab_path: Mapped[str] = mapped_column(String(255), nullable=False)  # namespace/project_name
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    web_url: Mapped[str] = mapped_column(String(512), nullable=False)

    # 项目所有者
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="projects", foreign_keys=[owner_id])

    # 项目配置
    config: Mapped[dict] = mapped_column(JSON, default={})

    # 项目状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # GitLab配置
    gitlab_webhook_secret: Mapped[Optional[str]] = mapped_column(String(255))  # 加密存储
    gitlab_webhook_id: Mapped[Optional[int]] = mapped_column(Integer)

    # 关系
    pipelines = relationship("Pipeline", back_populates="project", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name}, gitlab_project_id={self.gitlab_project_id})>"


class Pipeline(Base, TimestampMixin):
    """Pipeline表"""

    __tablename__ = "pipelines"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # GitLab Pipeline信息
    gitlab_pipeline_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    gitlab_project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    ref: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("pending", "running", "success", "failed", "canceled", "skipped", name="pipeline_status"),
        default="pending",
        nullable=False,
        index=True,
    )

    # 关联信息
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    project = relationship("Project", back_populates="pipelines")

    creator_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"))
    creator = relationship("User", back_populates="created_pipelines", foreign_keys=[creator_id])

    # Pipeline元数据
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # push, merge_request, etc.
    variables: Mapped[dict] = mapped_column(JSON, default={})

    # 时间统计
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration: Mapped[Optional[int]] = mapped_column(Integer)  # 秒

    # 关系
    jobs = relationship("Job", back_populates="pipeline", lazy="dynamic", cascade="all, delete-orphan")
    test_results = relationship("TestResult", back_populates="pipeline", lazy="dynamic")
    code_reviews = relationship("CodeReview", back_populates="pipeline", lazy="dynamic")
    build_artifacts = relationship("BuildArtifact", back_populates="pipeline", lazy="dynamic", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index("ix_pipelines_project_created", "project_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Pipeline(id={self.id}, gitlab_pipeline_id={self.gitlab_pipeline_id}, status={self.status})>"


class Job(Base, TimestampMixin):
    """Job表"""

    __tablename__ = "jobs"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # GitLab Job信息
    gitlab_job_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    stage: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("pending", "running", "success", "failed", "canceled", "skipped", name="job_status"),
        default="pending",
        nullable=False,
    )

    # 关联Pipeline
    pipeline_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipelines.id"), nullable=False)
    pipeline = relationship("Pipeline", back_populates="jobs")

    # Job配置
    image: Mapped[Optional[str]] = mapped_column(String(255))
    script: Mapped[list] = mapped_column(JSON, default=list)
    variables: Mapped[dict] = mapped_column(JSON, default={})

    # 资源使用
    cpu_usage: Mapped[Optional[float]] = mapped_column(Float)  # 核心使用率
    memory_usage: Mapped[Optional[int]] = mapped_column(Integer)  # 内存使用（字节）

    # 时间统计
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration: Mapped[Optional[int]] = mapped_column(Integer)  # 秒

    # 日志
    log_file_path: Mapped[Optional[str]] = mapped_column(String(512))
    log_size: Mapped[Optional[int]] = mapped_column(Integer)  # 字节

    # 重试信息
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text)

    # 索引
    __table_args__ = (
        Index("ix_jobs_pipeline_stage", "pipeline_id", "stage"),
        Index("ix_jobs_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, name={self.name}, stage={self.stage}, status={self.status})>"


class TestCase(Base, TimestampMixin):
    """测试用例表"""

    __tablename__ = "test_cases"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # GitLab项目
    gitlab_project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # 测试用例信息
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    suite: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # 测试元数据
    test_type: Mapped[str] = mapped_column(
        Enum("unit", "integration", "ui", name="test_type"),
        default="unit",
        nullable=False,
    )
    dependencies: Mapped[list] = mapped_column(JSON, default=list)  # 依赖的其他测试用例

    # 统计信息
    total_runs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_runs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_runs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    flaky_runs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 不稳定的次数
    avg_duration: Mapped[Optional[float]] = mapped_column(Float)  # 平均执行时间（秒）

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 关系
    test_results = relationship("TestResult", back_populates="test_case", lazy="dynamic")

    # 索引
    __table_args__ = (
        Index("ix_test_cases_project_suite", "gitlab_project_id", "suite"),
        Index("ix_test_cases_file_line", "file_path", "line_number"),
        UniqueConstraint("gitlab_project_id", "suite", "name", name="uq_test_case"),
    )

    def __repr__(self) -> str:
        return f"<TestCase(id={self.id}, name={self.name}, suite={self.suite})>"


class TestResult(Base, TimestampMixin):
    """测试结果表"""

    __tablename__ = "test_results"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # 关联Pipeline和TestCase
    pipeline_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipelines.id"), nullable=False)
    pipeline = relationship("Pipeline", back_populates="test_results")

    test_case_id: Mapped[str] = mapped_column(String(36), ForeignKey("test_cases.id"), nullable=False)
    test_case = relationship("TestCase", back_populates="test_results")

    # Job关联
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), nullable=False)

    # 测试结果
    status: Mapped[str] = mapped_column(
        Enum("passed", "failed", "skipped", name="test_status"),
        nullable=False,
    )
    duration: Mapped[float] = mapped_column(Float, nullable=False)  # 秒

    # 输出
    output: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text)

    # 覆盖率信息
    coverage_lines: Mapped[Optional[float]] = mapped_column(Float)  # 行覆盖率
    coverage_functions: Mapped[Optional[float]] = mapped_column(Float)  # 函数覆盖率
    coverage_branches: Mapped[Optional[float]] = mapped_column(Float)  # 分支覆盖率

    # 智能测试选择
    is_selected_by_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    selection_reason: Mapped[Optional[str]] = mapped_column(Text)  # AI选择原因

    # 重试信息
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_flaky: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 索引
    __table_args__ = (
        Index("ix_test_results_pipeline_status", "pipeline_id", "status"),
        Index("ix_test_results_test_case_created", "test_case_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<TestResult(id={self.id}, status={self.status}, duration={self.duration})>"


class CodeReview(Base, TimestampMixin):
    """代码审查结果表"""

    __tablename__ = "code_reviews"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # 关联Pipeline
    pipeline_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipelines.id"), nullable=False)
    pipeline = relationship("Pipeline", back_populates="code_reviews")

    # 文件信息
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)  # cpp, python, etc.

    # 审查结果统计
    total_issues: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    critical_issues: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    high_issues: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    medium_issues: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    low_issues: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 质量评分（0-100）
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    memory_safety_score: Mapped[Optional[float]] = mapped_column(Float)
    performance_score: Mapped[Optional[float]] = mapped_column(Float)
    modern_cpp_score: Mapped[Optional[float]] = mapped_column(Float)
    thread_safety_score: Mapped[Optional[float]] = mapped_column(Float)
    code_style_score: Mapped[Optional[float]] = mapped_column(Float)

    # AI分析
    ai_filtered_issues: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # AI过滤的误报数
    ai_summary: Mapped[Optional[str]] = mapped_column(Text)
    ai_suggestions: Mapped[list] = mapped_column(JSON, default=list)

    # 详细问题列表
    issues: Mapped[list] = mapped_column(JSON, default=list)  # 详细问题列表

    # 工具来源
    tool_source: Mapped[str] = mapped_column(
        Enum("clang_tidy", "cppcheck", "combined", name="tool_source"),
        nullable=False,
    )

    # 状态
    is_incremental: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 是否增量审查

    # 索引
    __table_args__ = (
        Index("ix_code_reviews_pipeline_file", "pipeline_id", "file_path"),
        Index("ix_code_reviews_score", "overall_score"),
    )

    def __repr__(self) -> str:
        return f"<CodeReview(id={self.id}, file_path={self.file_path}, overall_score={self.overall_score})>"


class QualityMetric(Base, TimestampMixin):
    """质量指标表"""

    __tablename__ = "quality_metrics"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # 关联Project
    gitlab_project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # 指标类型
    metric_type: Mapped[str] = mapped_column(
        Enum("code_coverage", "test_pass_rate", "code_quality", "build_success_rate", "test_duration", name="metric_type"),
        nullable=False,
    )

    # 时间维度（用于趋势分析）
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # 指标值
    value: Mapped[float] = mapped_column(Float, nullable=False)

    # 额外信息
    meta_data: Mapped[dict] = mapped_column(JSON, default={})

    # 索引
    __table_args__ = (
        Index("ix_quality_metrics_project_type_date", "gitlab_project_id", "metric_type", "date"),
    )

    def __repr__(self) -> str:
        return f"<QualityMetric(id={self.id}, metric_type={self.metric_type}, value={self.value})>"


class MemoryReport(Base, TimestampMixin):
    """内存安全报告表"""

    __tablename__ = "memory_reports"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # 关联Pipeline
    pipeline_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipelines.id"), nullable=False)

    # 文件信息
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    function_name: Mapped[Optional[str]] = mapped_column(String(255))

    # 内存问题类型
    issue_type: Mapped[str] = mapped_column(
        Enum("memory_leak", "buffer_overflow", "use_after_free", "dangling_pointer", "invalid_access", name="issue_type"),
        nullable=False,
    )

    # 严重程度
    severity: Mapped[str] = mapped_column(
        Enum("critical", "high", "medium", "low", name="severity"),
        nullable=False,
    )

    # 问题详情
    description: Mapped[str] = mapped_column(Text, nullable=False)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text)

    # Valgrind原始信息
    valgrind_output: Mapped[Optional[str]] = mapped_column(Text)

    # AI分析
    ai_analysis: Mapped[Optional[str]] = mapped_column(Text)
    ai_fix_suggestion: Mapped[Optional[str]] = mapped_column(Text)
    ai_generated_code: Mapped[Optional[str]] = mapped_column(Text)  # 建议的修复代码

    # 状态
    is_false_positive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # AI判断为误报
    is_auto_fixable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 索引
    __table_args__ = (
        Index("ix_memory_reports_pipeline_severity", "pipeline_id", "severity"),
        Index("ix_memory_reports_type_severity", "issue_type", "severity"),
    )

    def __repr__(self) -> str:
        return f"<MemoryReport(id={self.id}, issue_type={self.issue_type}, severity={self.severity})>"


class DependencyGraph(Base, TimestampMixin):
    """依赖图表"""

    __tablename__ = "dependency_graphs"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # GitLab项目
    gitlab_project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)

    # 依赖图数据（JSON格式）
    # 结构：{nodes: [{id, name, type}], edges: [{from, to, type}]}
    graph_data: Mapped[dict] = mapped_column(JSON, nullable=False)

    # 统计信息
    total_nodes: Mapped[int] = mapped_column(Integer, nullable=False)
    total_edges: Mapped[int] = mapped_column(Integer, nullable=False)

    # 元数据
    build_time: Mapped[Optional[int]] = mapped_column(Integer)  # 构建依赖图耗时（毫秒）

    # 状态
    is_cached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 索引
    __table_args__ = (
        Index("ix_dependency_graphs_project_commit", "gitlab_project_id", "commit_sha"),
    )

    def __repr__(self) -> str:
        return f"<DependencyGraph(id={self.id}, nodes={self.total_nodes}, edges={self.total_edges})>"


class TestSelectionHistory(Base, TimestampMixin):
    """测试选择历史表"""

    __tablename__ = "test_selection_history"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # 关联Pipeline
    pipeline_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipelines.id"), nullable=False)

    # 选择统计
    total_tests: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_tests: Mapped[int] = mapped_column(Integer, nullable=False)
    skipped_tests: Mapped[int] = mapped_column(Integer, nullable=False)

    # 节省的时间估算
    estimated_time_saved: Mapped[int] = mapped_column(Integer, nullable=False)  # 秒

    # 选择原因
    selection_criteria: Mapped[dict] = mapped_column(JSON, nullable=False)
    # {
    #   "changed_files": ["file1.cpp", "file2.cpp"],
    #   "affected_tests": ["test1", "test2"],
    #   "impact_score": 0.85
    # }

    # 选择的测试列表
    selected_test_ids: Mapped[list] = mapped_column(JSON, nullable=False)

    # 跳过的测试列表
    skipped_test_ids: Mapped[list] = mapped_column(JSON, nullable=False)

    # 性能指标
    selection_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)  # 选择耗时（毫秒）

    def __repr__(self) -> str:
        return f"<TestSelectionHistory(id={self.id}, selected={self.selected_tests}/{self.total_tests})>"


class AIUsageStats(Base, TimestampMixin):
    """AI使用统计表"""

    __tablename__ = "ai_usage_stats"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # GitLab项目
    gitlab_project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # AI功能
    ai_feature: Mapped[str] = mapped_column(
        Enum("test_selection", "code_review", "config_generation", "pipeline_maintenance", "memory_detection", name="ai_feature"),
        nullable=False,
    )

    # AI模型
    model_provider: Mapped[str] = mapped_column(
        Enum("anthropic", "zhipu", "openai", "local", name="model_provider"),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Token使用统计
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False)

    # 成本（美元）
    cost_usd: Mapped[Optional[float]] = mapped_column(Float)

    # 性能指标
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    # 额外信息
    meta_data: Mapped[dict] = mapped_column(JSON, default={})

    # 索引
    __table_args__ = (
        Index("ix_ai_usage_stats_project_feature_date", "gitlab_project_id", "ai_feature", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AIUsageStats(id={self.id}, feature={self.ai_feature}, tokens={self.total_tokens})>"


class AutoFixHistory(Base, TimestampMixin):
    """自动修复历史表"""

    __tablename__ = "auto_fix_history"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # 关联Pipeline
    pipeline_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipelines.id"), nullable=False)

    # 修复类型
    fix_type: Mapped[str] = mapped_column(
        Enum("pipeline_failure", "test_failure", "dependency_issue", "config_error", name="fix_type"),
        nullable=False,
    )

    # 修复前后的对比
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    fixed_content: Mapped[str] = mapped_column(Text, nullable=False)

    # 文件信息
    file_path: Mapped[Optional[str]] = mapped_column(String(512))

    # 修复结果
    status: Mapped[str] = mapped_column(
        Enum("success", "failed", "pending_review", name="fix_status"),
        nullable=False,
    )

    # AI相关信息
    ai_suggested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float)  # 0-1

    # 验证结果
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_result: Mapped[Optional[str]] = mapped_column(Text)

    # GitLab MR信息（如果自动创建了MR）
    gitlab_mr_iid: Mapped[Optional[int]] = mapped_column(Integer)
    gitlab_mr_url: Mapped[Optional[str]] = mapped_column(String(512))

    def __repr__(self) -> str:
        return f"<AutoFixHistory(id={self.id}, fix_type={self.fix_type}, status={self.status})>"


class BuildArtifact(Base, TimestampMixin):
    """构建产物表"""

    __tablename__ = "build_artifacts"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # 关联Pipeline和Job
    pipeline_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipelines.id"), nullable=False)
    pipeline = relationship("Pipeline", back_populates="build_artifacts")

    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), nullable=False)

    # 产物信息
    artifact_type: Mapped[str] = mapped_column(
        Enum("binary", "library", "docker_image", "package", "log", name="artifact_type"),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # 元数据
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256

    # 存储信息
    storage_type: Mapped[str] = mapped_column(
        Enum("local", "s3", "minio", name="storage_type"),
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)  # 完整存储路径
    download_url: Mapped[Optional[str]] = mapped_column(String(512))

    # 下载统计
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_downloaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # 索引
    __table_args__ = (
        Index("ix_build_artifacts_pipeline_type", "pipeline_id", "artifact_type"),
        Index("ix_build_artifacts_job", "job_id"),
    )

    def __repr__(self) -> str:
        return f"<BuildArtifact(id={self.id}, type={self.artifact_type}, file_name={self.file_name})>"
