"""Alembic Environment Configuration"""

import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# this is the Alembic Config object
from alembic.config import Config

# add your model's MetaData object here for 'autogenerate' support
from src.db.models import Base
from src.utils.config import settings
from src.db.session import get_async_engine

# this is the MetaData object for your database
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """Run migrations in 'online' mode using async engine.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = settings.database_url
    
    # Convert postgresql:// to postgresql+asyncpg:// for async
    if configuration.startswith("postgresql://"):
        configuration = configuration.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif configuration.startswith("sqlite://"):
        configuration = configuration.replace("sqlite://", "sqlite+aiosqlite://", 1)

    connectable = async_engine_from_config(
        {"sqlalchemy.url": configuration},
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using async engine.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    asyncio.run(run_async_migrations())


if __name__ == "__main__":
    from logging.config import fileConfig
    from alembic.config import Config

    fileConfig("alembic.ini")
    alembic_config = Config()
    run_migrations_online()
