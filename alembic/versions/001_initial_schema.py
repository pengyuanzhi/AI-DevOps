"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2024-03-08 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建枚举类型
    op.execute("CREATE TYPE pipeline_status AS ENUM ('pending', 'running', 'success', 'failed', 'cancelled', 'timeout')")
    op.execute("CREATE TYPE job_status AS ENUM ('pending', 'running', 'success', 'failed', 'cancelled', 'timeout')")
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'developer', 'viewer')")

    # 创建用户表
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('gitlab_user_id', sa.Integer(), unique=True, nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('role', user_role, nullable=False, server_default='developer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_users_gitlab_user_id', 'gitlab_user_id'),
        sa.Index('ix_users_username', 'username'),
        sa.Index('ix_users_email', 'email'),
    )
    op.create_index('users', 'ix_users_email', ['email'], unique=True)
    op.create_index('users', 'ix_users_username', ['username'], unique=True)

    # 创建项目表
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('gitlab_project_id', sa.Integer(), unique=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('gitlab_url', sa.String(length=500), nullable=False),
        sa.Column('default_branch', sa.String(length=100), nullable=False, server_default='main'),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_projects_gitlab_project_id', 'gitlab_project_id'),
    )

    # 创建流水线表
    op.create_table(
        'pipelines',
        sa.Column('id', sa.String(length=100), primary_key=True),
        sa.Column('gitlab_pipeline_id', sa.Integer(), nullable=False),
        sa.Column('gitlab_project_id', sa.Integer(), nullable=False),
        sa.Column('gitlab_mr_iid', sa.Integer(), nullable=True),
        sa.Column('status', pipeline_status, nullable=False),
        sa.Column('ref', sa.String(length=255), nullable=False),
        sa.Column('sha', sa.String(length=100), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['gitlab_project_id'], ['projects'], name='fk_pipelines_project'),
        sa.Index('ix_pipelines_gitlab_pipeline_id', 'gitlab_pipeline_id'),
        sa.Index('ix_pipelines_gitlab_project_id', 'gitlab_project_id'),
        sa.Index('ix_pipelines_status', 'status'),
        sa.Index('ix_pipelines_created_at', 'created_at'),
    )

    # 创建作业表
    op.create_table(
        'jobs',
        sa.Column('id', sa.String(length=100), primary_key=True),
        sa.Column('pipeline_id', sa.String(length=100), nullable=False),
        sa.Column('gitlab_job_id', sa.Integer(), nullable=False),
        sa.Column('gitlab_project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('stage', sa.String(length=100), nullable=False),
        sa.Column('status', job_status, nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('log', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['pipeline_id'], ['pipelines'], name='fk_jobs_pipeline'),
        sa.ForeignKeyConstraint(['gitlab_project_id'], ['projects'], name='fk_jobs_project'),
        sa.Index('ix_jobs_gitlab_job_id', 'gitlab_job_id'),
        sa.Index('ix_jobs_pipeline_id', 'pipeline_id'),
        sa.Index('ix_jobs_status', 'status'),
    )

    # 创建构建配置表
    op.create_table(
        'build_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('build_type', sa.String(length=50), server_default='RelWithDebInfo'),
        sa.Column('cmake_options', sa.JSON(), nullable=True),
        sa.Column('qmake_options', sa.JSON(), nullable=True),
        sa.Column('env_vars', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects'], name='fk_build_configs_project'),
        sa.Index('ix_build_configs_project_id', 'project_id'),
    )

    # 创建测试套件表
    op.create_table(
        'test_suites',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('test_type', sa.String(length=50), server_default='qttest'),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects'], name='fk_test_suites_project'),
        sa.Index('ix_test_suites_project_id', 'project_id'),
    )

    # 创建测试执行记录表
    op.create_table(
        'test_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('pipeline_id', sa.String(length=100), nullable=False),
        sa.Column('test_suite_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('total_tests', sa.Integer(), nullable=False),
        sa.Column('passed_tests', sa.Integer(), server_default='0'),
        sa.Column('failed_tests', sa.Integer(), server_default='0'),
        sa.Column('skipped_tests', sa.Integer(), server_default='0'),
        sa.Column('coverage_percent', sa.Float(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('log', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['pipeline_id'], ['pipelines'], name='fk_test_runs_pipeline'),
        sa.ForeignKeyConstraint(['test_suite_id'], ['test_suites'], name='fk_test_runs_suite'),
        sa.Index('ix_test_runs_pipeline_id', 'pipeline_id'),
        sa.Index('ix_test_runs_status', 'status'),
    )

    # 创建代码审查记录表
    op.create_table(
        'code_reviews',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('mr_id', sa.Integer(), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('memory_safety', sa.Float()),
        sa.Column('performance', sa.Float()),
        sa.Column('modern_cpp', sa.Float()),
        sa.Column('thread_safety', sa.Float()),
        sa.Column('code_style', sa.Float()),
        sa.Column('total_issues', sa.Integer(), server_default='0'),
        sa.Column('critical_issues', sa.Integer(), server_default='0'),
        sa.Column('warning_issues', sa.Integer(), server_default='0'),
        sa.Column('info_issues', sa.Integer(), server_default='0'),
        sa.Column('filtered_issues', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects'], name='fk_code_reviews_project'),
        sa.Index('ix_code_reviews_project_id', 'project_id'),
        sa.Index('ix_code_reviews_mr_id', 'mr_id'),
    )

    # 创建代码问题表
    op.create_table(
        'code_issues',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('review_id', sa.Integer(), nullable=False),
        sa.Column('tool', sa.String(length=50), nullable=False),  # clang-tidy, cppcheck
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('line', sa.Integer(), nullable=False),
        sa.Column('column', sa.Integer(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('rule_id', sa.String(length=100), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('suggestion', sa.Text(), nullable=True),
        sa.Column('is_false_positive', sa.Boolean(), server_default='false'),
        sa.Column('confidence', sa.Float(), server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['review_id'], ['code_reviews'], name='fk_code_issues_review'),
        sa.Index('ix_code_issues_review_id', 'review_id'),
        sa.Index('ix_code_issues_file_path', 'file_path'),
        sa.Index('ix_code_issues_severity', 'severity'),
    )

    # 创建AI功能使用记录表（用于成本追踪）
    op.create_table(
        'ai_usage_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('feature', sa.String(length=50), nullable=False),  # test_selection, code_review, etc.
        sa.Column('model_provider', sa.String(length=50), nullable=False),  # zhipu, qwen
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=False),
        sa.Column('cost_estimate', sa.Float(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects'], name='fk_ai_usage_logs_project'),
        sa.Index('ix_ai_usage_logs_project_id', 'project_id'),
        sa.Index('ix_ai_usage_logs_feature', 'feature'),
        sa.Index('ix_ai_usage_logs_created_at', 'created_at'),
    )


def downgrade() -> None:
    # 删除表（按照依赖关系逆序）
    op.drop_table('ai_usage_logs')
    op.drop_table('code_issues')
    op.drop_table('code_reviews')
    op.drop_table('test_runs')
    op.drop_table('test_suites')
    op.drop_table('build_configs')
    op.drop_table('jobs')
    op.drop_table('pipelines')
    op.drop_table('projects')
    op.drop_table('users')

    # 删除枚举类型
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP TYPE IF EXISTS job_status")
    op.execute("DROP TYPE IF EXISTS pipeline_status")
