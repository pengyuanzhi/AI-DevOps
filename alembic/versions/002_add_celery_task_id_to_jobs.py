"""add celery_task_id to jobs table

Revision ID: 002_add_celery_task_id
Revises: 001_initial
Create Date: 2026-03-09 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_celery_task_id'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 celery_task_id 字段到 jobs 表
    op.add_column(
        'jobs',
        sa.Column('celery_task_id', sa.String(length=255), nullable=True)
    )

    # 为 celery_task_id 创建索引
    op.create_index('ix_jobs_celery_task_id', 'jobs', ['celery_task_id'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_jobs_celery_task_id', table_name='jobs')

    # 删除字段
    op.drop_column('jobs', 'celery_task_id')
