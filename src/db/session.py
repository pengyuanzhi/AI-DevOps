"""
数据库会话管理

提供同步和异步的数据库会话。
"""

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from ..utils.config import settings
from .models import Base

# 同步数据库引擎
_sync_engine: Optional[create_engine] = None
_sync_session_factory: Optional[sessionmaker] = None


def get_sync_engine():
    """获取同步数据库引擎"""
    global _sync_engine, _sync_session_factory

    if _sync_engine is None:
        database_url = settings.database_url
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")

        _sync_engine = create_engine(
            database_url,
            echo=settings.db_echo,
            pool_pre_ping=True,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
        )
        _sync_session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_sync_engine,
        )

    return _sync_engine


def get_db() -> Generator[Session, None, None]:
    """获取同步数据库会话（用于FastAPI依赖注入）"""
    engine = get_sync_engine()
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# 异步数据库引擎
_async_engine: Optional[create_async_engine] = None
_async_session_factory: Optional[async_sessionmaker] = None


def get_async_engine():
    """获取异步数据库引擎"""
    global _async_engine, _async_session_factory

    if _async_engine is None:
        database_url = settings.database_url
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")

        # 将postgresql://转换为postgresql+asyncpg://
        if database_url.startswith("postgresql://"):
            async_database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("sqlite://"):
            async_database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        else:
            async_database_url = database_url

        _async_engine = create_async_engine(
            async_database_url,
            echo=settings.db_echo,
            pool_pre_ping=True,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
        )
        _async_session_factory = async_sessionmaker(
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            bind=_async_engine,
        )

    return _async_engine


async def get_async_db() -> Generator[AsyncSession, None, None]:
    """获取异步数据库会话（用于FastAPI依赖注入）"""
    engine = get_async_engine()
    factory = async_sessionmaker(
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def init_db():
    """初始化数据库"""
    engine = get_sync_engine()
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    获取数据库会话的上下文管理器

    用于脚本或手动管理会话的场景。
    """
    engine = get_sync_engine()
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def get_async_db_session() -> Generator[AsyncSession, None, None]:
    """
    获取异步数据库会话的上下文管理器

    用于异步脚本或手动管理会话的场景。
    """
    engine = get_async_engine()
    factory = async_sessionmaker(
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
