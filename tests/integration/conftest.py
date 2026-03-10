"""
集成测试配置和共享fixtures

提供测试所需的数据库、Celery、WebSocket等共享资源
"""

import asyncio
import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock, patch
from enum import Enum
import pytest
import pytest_asyncio
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime

from src.services.websocket.manager import manager as ws_manager

# 定义简化的模型用于测试（避免复杂的导入问题）
class Base(DeclarativeBase):
    pass

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gitlab_url: Mapped[str] = mapped_column(String(500), nullable=True)
    gitlab_project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class Pipeline(Base):
    __tablename__ = "pipelines"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    gitlab_project_id: Mapped[int] = mapped_column(Integer, nullable=False)
    gitlab_pipeline_id: Mapped[int] = mapped_column(Integer, nullable=True)
    ref: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    pipeline_id: Mapped[str] = mapped_column(String(100), ForeignKey("pipelines.id"), nullable=False)
    gitlab_job_id: Mapped[int] = mapped_column(Integer, nullable=False)
    gitlab_project_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    stage: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[JobStatus] = mapped_column(SQLEnum(JobStatus), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    log: Mapped[str] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[str] = mapped_column(String(255), nullable=True)
    cached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cache_key: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    pipeline = relationship("Pipeline", backref="jobs")

    __table_args__ = (
        Index("ix_jobs_gitlab_job_id", "gitlab_job_id"),
        Index("ix_jobs_pipeline_id", "pipeline_id"),
    )

    def __repr__(self) -> str:
        return f"<Job(id='{self.id}', name='{self.name}', status='{self.status.value}')>"


# =============================================================================
# 测试数据库配置
# =============================================================================

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """创建测试数据库引擎"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # 清理：删除所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator:
    """创建测试数据库会话"""
    async_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    session = async_maker()
    try:
        yield session
    finally:
        await session.rollback()
        await session.close()


# =============================================================================
# 项目数据fixtures
# =============================================================================

@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession) -> Project:
    """创建测试项目"""
    now = datetime.now()
    project = Project(
        id=1,
        name="Test Project",
        gitlab_url="https://gitlab.example.com/test/project",
        gitlab_project_id=123,
        description="Integration test project",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_pipeline(db_session: AsyncSession, test_project: Project) -> Pipeline:
    """创建测试流水线"""
    pipeline = Pipeline(
        id="test-pipeline-1",
        gitlab_project_id=test_project.id,
        gitlab_pipeline_id=456,
        ref="main",
        status="running",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)
    return pipeline


@pytest_asyncio.fixture
async def test_job(db_session: AsyncSession, test_pipeline: Pipeline) -> Job:
    """创建测试作业"""
    job = Job(
        id="test-job-1",
        pipeline_id=test_pipeline.id,
        gitlab_job_id=789,
        gitlab_project_id=test_pipeline.gitlab_project_id,
        name="test-job",
        stage="test",
        status=JobStatus.PENDING,
        duration_seconds=0,
        retry_count=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


# =============================================================================
# Celery fixtures
# =============================================================================

@pytest.fixture(scope="session")
def celery_config():
    """Celery测试配置"""
    return {
        'broker_url': 'memory://',
        'result_backend': 'cache+memory://',
        'task_always_eager': True,  # 同步执行任务用于测试
        'task_eager_propagates': True,
    }


@pytest.fixture
def mock_celery_task():
    """Mock Celery任务"""
    task = Mock()
    task.id = "test-task-id-123"
    task.delay = Mock(return_value=task)
    task.apply_async = Mock(return_value=task)
    return task


# =============================================================================
# WebSocket fixtures
# =============================================================================

@pytest.fixture
def websocket_manager():
    """获取WebSocket管理器"""
    return ws_manager


@pytest.fixture
async def mock_websocket():
    """Mock WebSocket连接"""
    ws = Mock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.send = AsyncMock()
    ws.close = AsyncMock()
    return ws


# =============================================================================
# 测试数据fixtures
# =============================================================================

@pytest.fixture
def sample_build_log():
    """示例构建日志"""
    return """
[ 25%] Building CXX object CMakeFiles/app.dir/main.cpp.o
[ 50%] Building CXX object CMakeFiles/app.dir/utils.cpp.o
[ 75%] Building CXX object CMakeFiles/app.dir/calculator.cpp.o
[100%] Linking CXX executable app
[100%] Built target app
"""


@pytest.fixture
def sample_test_log():
    """示例测试日志"""
    return """
********* Start testing of CalculatorTest *********
Config: Using QtTest library 6.4.0
PASS   : CalculatorTest::initTestCase()
PASS   : CalculatorTest::testAddition()
PASS   : CalculatorTest::testSubtraction()
PASS   : CalculatorTest::cleanupTestCase()
Totals: 4 passed, 0 failed, 0 skipped
********* Finished testing of CalculatorTest *********
"""


@pytest.fixture
def sample_failure_log():
    """示例失败日志"""
    return """
********* Start testing of CalculatorTest *********
FAIL!  : CalculatorTest::testAddition() Compared values are not the same
   Actual   (calc.add(2, 3)): 5
   Expected (6.0)             : 6
   Loc: [../tests/tst_calculator.cpp(19)]
Totals: 1 passed, 1 failed, 0 skipped
********* Finished testing of CalculatorTest *********
"""


# =============================================================================
# Git仓库fixtures
# =============================================================================

@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """创建临时Git仓库"""
    import subprocess

    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # 初始化Git仓库
    subprocess.run(["git", "init"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)

    # 创建初始提交
    (repo_path / "README.md").write_text("# Test Repository")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True)

    yield repo_path

    # 清理
    shutil.rmtree(repo_path, ignore_errors=True)


# =============================================================================
# 测试工具函数
# =============================================================================

@pytest.fixture
def make_test_log():
    """创建测试日志的工厂函数"""
    def _make_log(status: str, message: str = "") -> str:
        timestamp = datetime.now().isoformat()
        return f"[{timestamp}] {status}: {message}"
    return _make_log


# =============================================================================
# 测试标记
# =============================================================================

def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line(
        "markers", "integration: 集成测试标记"
    )
    config.addinivalue_line(
        "markers", "slow: 慢速测试标记（需要外部服务）"
    )
    config.addinivalue_line(
        "markers", "requires_celery: 需要Celery worker"
    )
    config.addinivalue_line(
        "markers", "requires_db: 需要数据库"
    )


# =============================================================================
# 测试清理钩子
# =============================================================================

@pytest.fixture(autouse=True)
async def cleanup_websocket():
    """每个测试后清理WebSocket连接"""
    yield

    # 清理所有活动连接
    for conn_id in list(ws_manager.active_connections.keys()):
        await ws_manager.disconnect(conn_id)
