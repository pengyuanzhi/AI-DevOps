"""add cached and cache_key to jobs table

Revision ID: 003_add_cache_fields
Revises: 002_add_celery_task_id
Create Date: 2026-03-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_cache_fields'
down_revision: Union[str, None] = '002_add_celery_task_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 cached 字段到 jobs 表（标识是否来自缓存）
    op.add_column(
        'jobs',
        sa.Column('cached', sa.Boolean(), nullable=False, server_default='false')
    )

    # 添加 cache_key 字段到 jobs 表（存储缓存键）
    op.add_column(
        'jobs',
        sa.Column('cache_key', sa.String(length=255), nullable=True)
    )

    # 为 cache_key 创建索引
    op.create_index('ix_jobs_cache_key', 'jobs', ['cache_key'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_jobs_cache_key', table_name='jobs')

    # 删除字段
    op.drop_column('jobs', 'cache_key')
    op.drop_column('jobs', 'cached')
