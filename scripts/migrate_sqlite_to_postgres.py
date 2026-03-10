#!/usr/bin/env python3
"""
SQLite to PostgreSQL migration script

Migrates data from SQLite database to PostgreSQL.

Usage:
    python scripts/migrate_sqlite_to_postgres.py [--sqlite-path PATH]

Options:
    --sqlite-path PATH    Path to SQLite database file (default: ./data/ai_cicd.db)
"""

import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.db.models import (
    Base, User, Project, Pipeline, Job, BuildConfig, TestSuite,
    TestRun, CodeReview, CodeIssue, AIUsageLog,
    PipelineStatus, JobStatus, UserRole
)
from src.utils.config import settings


def get_sqlite_connection(db_path: str):
    """Get SQLite connection"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(cursor, table_name: str) -> bool:
    """Check if table exists in SQLite"""
    cursor.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
    )
    return cursor.fetchone() is not None


def migrate_users(sqlite_conn, postgres_session: AsyncSession) -> int:
    """Migrate users table"""
    cursor = sqlite_conn.cursor()

    if not table_exists(cursor, "users"):
        print("  - users table not found, skipping")
        return 0

    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()

    count = 0
    for row in rows:
        user = User(
            id=row["id"],
            gitlab_user_id=row["gitlab_user_id"],
            username=row["username"],
            email=row["email"],
            name=row["name"],
            avatar_url=row["avatar_url"],
            role=UserRole(row["role"]),
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
        postgres_session.add(user)
        count += 1

    print(f"  - Migrated {count} users")
    return count


def migrate_projects(sqlite_conn, postgres_session: AsyncSession) -> int:
    """Migrate projects table"""
    cursor = sqlite_conn.cursor()

    if not table_exists(cursor, "projects"):
        print("  - projects table not found, skipping")
        return 0

    cursor.execute("SELECT * FROM projects")
    rows = cursor.fetchall()

    count = 0
    for row in rows:
        # Parse JSON config
        config = None
        if row["config"]:
            try:
                config = json.loads(row["config"])
            except:
                config = {}

        project = Project(
            id=row["id"],
            gitlab_project_id=row["gitlab_project_id"],
            name=row["name"],
            description=row["description"],
            gitlab_url=row["gitlab_url"],
            default_branch=row["default_branch"],
            config=config,
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
        postgres_session.add(project)
        count += 1

    print(f"  - Migrated {count} projects")
    return count


def migrate_pipelines(sqlite_conn, postgres_session: AsyncSession) -> int:
    """Migrate pipelines table"""
    cursor = sqlite_conn.cursor()

    if not table_exists(cursor, "pipelines"):
        print("  - pipelines table not found, skipping")
        return 0

    cursor.execute("SELECT * FROM pipelines")
    rows = cursor.fetchall()

    count = 0
    for row in rows:
        pipeline = Pipeline(
            id=row["id"],
            gitlab_pipeline_id=row["gitlab_pipeline_id"],
            gitlab_project_id=row["gitlab_project_id"],
            gitlab_mr_iid=row["gitlab_mr_iid"],
            status=PipelineStatus(row["status"]),
            ref=row["ref"],
            sha=row["sha"],
            source=row["source"],
            duration_seconds=row["duration_seconds"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
        )
        postgres_session.add(pipeline)
        count += 1

    print(f"  - Migrated {count} pipelines")
    return count


def migrate_jobs(sqlite_conn, postgres_session: AsyncSession) -> int:
    """Migrate jobs table"""
    cursor = sqlite_conn.cursor()

    if not table_exists(cursor, "jobs"):
        print("  - jobs table not found, skipping")
        return 0

    cursor.execute("SELECT * FROM jobs")
    rows = cursor.fetchall()

    count = 0
    for row in rows:
        job = Job(
            id=row["id"],
            pipeline_id=row["pipeline_id"],
            gitlab_job_id=row["gitlab_job_id"],
            gitlab_project_id=row["gitlab_project_id"],
            name=row["name"],
            stage=row["stage"],
            status=JobStatus(row["status"]),
            duration_seconds=row["duration_seconds"],
            retry_count=row["retry_count"],
            log=row["log"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
        )
        postgres_session.add(job)
        count += 1

    print(f"  - Migrated {count} jobs")
    return count


def migrate_build_configs(sqlite_conn, postgres_session: AsyncSession) -> int:
    """Migrate build_configs table"""
    cursor = sqlite_conn.cursor()

    if not table_exists(cursor, "build_configs"):
        print("  - build_configs table not found, skipping")
        return 0

    cursor.execute("SELECT * FROM build_configs")
    rows = cursor.fetchall()

    count = 0
    for row in rows:
        build_config = BuildConfig(
            id=row["id"],
            project_id=row["project_id"],
            name=row["name"],
            build_type=row["build_type"],
            cmake_options=json.loads(row["cmake_options"]) if row["cmake_options"] else None,
            qmake_options=json.loads(row["qmake_options"]) if row["qmake_options"] else None,
            env_vars=json.loads(row["env_vars"]) if row["env_vars"] else None,
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
        postgres_session.add(build_config)
        count += 1

    print(f"  - Migrated {count} build configs")
    return count


def migrate_test_suites(sqlite_conn, postgres_session: AsyncSession) -> int:
    """Migrate test_suites table"""
    cursor = sqlite_conn.cursor()

    if not table_exists(cursor, "test_suites"):
        print("  - test_suites table not found, skipping")
        return 0

    cursor.execute("SELECT * FROM test_suites")
    rows = cursor.fetchall()

    count = 0
    for row in rows:
        test_suite = TestSuite(
            id=row["id"],
            project_id=row["project_id"],
            name=row["name"],
            test_type=row["test_type"],
            config=json.loads(row["config"]) if row["config"] else None,
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
        postgres_session.add(test_suite)
        count += 1

    print(f"  - Migrated {count} test suites")
    return count


def migrate_test_runs(sqlite_conn, postgres_session: AsyncSession) -> int:
    """Migrate test_runs table"""
    cursor = sqlite_conn.cursor()

    if not table_exists(cursor, "test_runs"):
        print("  - test_runs table not found, skipping")
        return 0

    cursor.execute("SELECT * FROM test_runs")
    rows = cursor.fetchall()

    count = 0
    for row in rows:
        test_run = TestRun(
            id=row["id"],
            pipeline_id=row["pipeline_id"],
            test_suite_id=row["test_suite_id"],
            status=row["status"],
            total_tests=row["total_tests"],
            passed_tests=row["passed_tests"],
            failed_tests=row["failed_tests"],
            skipped_tests=row["skipped_tests"],
            coverage_percent=row["coverage_percent"],
            duration_seconds=row["duration_seconds"],
            log=row["log"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
        postgres_session.add(test_run)
        count += 1

    print(f"  - Migrated {count} test runs")
    return count


def migrate_code_reviews(sqlite_conn, postgres_session: AsyncSession) -> int:
    """Migrate code_reviews table"""
    cursor = sqlite_conn.cursor()

    if not table_exists(cursor, "code_reviews"):
        print("  - code_reviews table not found, skipping")
        return 0

    cursor.execute("SELECT * FROM code_reviews")
    rows = cursor.fetchall()

    count = 0
    for row in rows:
        code_review = CodeReview(
            id=row["id"],
            project_id=row["project_id"],
            mr_id=row["mr_id"],
            overall_score=row["overall_score"],
            memory_safety=row["memory_safety"],
            performance=row["performance"],
            modern_cpp=row["modern_cpp"],
            thread_safety=row["thread_safety"],
            code_style=row["code_style"],
            total_issues=row["total_issues"],
            critical_issues=row["critical_issues"],
            warning_issues=row["warning_issues"],
            info_issues=row["info_issues"],
            filtered_issues=row["filtered_issues"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
        postgres_session.add(code_review)
        count += 1

    print(f"  - Migrated {count} code reviews")
    return count


def migrate_code_issues(sqlite_conn, postgres_session: AsyncSession) -> int:
    """Migrate code_issues table"""
    cursor = sqlite_conn.cursor()

    if not table_exists(cursor, "code_issues"):
        print("  - code_issues table not found, skipping")
        return 0

    cursor.execute("SELECT * FROM code_issues")
    rows = cursor.fetchall()

    count = 0
    for row in rows:
        code_issue = CodeIssue(
            id=row["id"],
            review_id=row["review_id"],
            tool=row["tool"],
            file_path=row["file_path"],
            line=row["line"],
            column=row["column"],
            severity=row["severity"],
            category=row["category"],
            rule_id=row["rule_id"],
            message=row["message"],
            suggestion=row["suggestion"],
            is_false_positive=bool(row["is_false_positive"]),
            confidence=row["confidence"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
        postgres_session.add(code_issue)
        count += 1

    print(f"  - Migrated {count} code issues")
    return count


def migrate_ai_usage_logs(sqlite_conn, postgres_session: AsyncSession) -> int:
    """Migrate ai_usage_logs table"""
    cursor = sqlite_conn.cursor()

    if not table_exists(cursor, "ai_usage_logs"):
        print("  - ai_usage_logs table not found, skipping")
        return 0

    cursor.execute("SELECT * FROM ai_usage_logs")
    rows = cursor.fetchall()

    count = 0
    for row in rows:
        ai_usage_log = AIUsageLog(
            id=row["id"],
            project_id=row["project_id"],
            feature=row["feature"],
            model_provider=row["model_provider"],
            model_name=row["model_name"],
            tokens_used=row["tokens_used"],
            cost_estimate=row["cost_estimate"],
            duration_ms=row["duration_ms"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
        postgres_session.add(ai_usage_log)
        count += 1

    print(f"  - Migrated {count} AI usage logs")
    return count


async def migrate_data(sqlite_path: str):
    """Migrate all data from SQLite to PostgreSQL"""
    print(f"\nMigrating data from SQLite to PostgreSQL...")
    print(f"SQLite path: {sqlite_path}")
    print(f"PostgreSQL URL: {settings.database_url}\n")

    # Connect to SQLite
    sqlite_conn = get_sqlite_connection(sqlite_path)

    # Create PostgreSQL engine and session
    pg_engine = create_async_engine(settings.database_url, echo=True)
    async_session_maker = sessionmaker(
        pg_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        # Migrate all tables in order of dependencies
        await migrate_users(sqlite_conn, session)
        await migrate_projects(sqlite_conn, session)
        await migrate_pipelines(sqlite_conn, session)
        await migrate_jobs(sqlite_conn, session)
        await migrate_build_configs(sqlite_conn, session)
        await migrate_test_suites(sqlite_conn, session)
        await migrate_test_runs(sqlite_conn, session)
        await migrate_code_reviews(sqlite_conn, session)
        await migrate_code_issues(sqlite_conn, session)
        await migrate_ai_usage_logs(sqlite_conn, session)

        # Commit all changes
        await session.commit()
        print("\n✓ Data migration completed successfully!")

    sqlite_conn.close()
    await pg_engine.dispose()


def main():
    parser = argparse.ArgumentParser(
        description="Migrate data from SQLite to PostgreSQL"
    )
    parser.add_argument(
        "--sqlite-path",
        default="./data/ai_cicd.db",
        help="Path to SQLite database file (default: ./data/ai_cicd.db)"
    )

    args = parser.parse_args()

    # Check if SQLite file exists
    if not Path(args.sqlite_path).exists():
        print(f"Error: SQLite database not found at {args.sqlite_path}")
        sys.exit(1)

    # Run migration
    asyncio.run(migrate_data(args.sqlite_path))


if __name__ == "__main__":
    main()
