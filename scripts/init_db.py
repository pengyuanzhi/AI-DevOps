#!/usr/bin/env python3
"""
Database initialization script

Creates initial database schema and seeds data.

Usage:
    python scripts/init_db.py [--seed] [--drop-existing]

Options:
    --seed           Seed initial data (admin user, demo project)
    --drop-existing  Drop existing tables before creating (DESTRUCTIVE)
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from src.db.session import get_async_engine
from src.db.models import Base, User, Project, UserRole
from src.utils.config import settings


async def create_tables(drop_existing: bool = False):
    """Create database tables"""
    engine = get_async_engine()

    if drop_existing:
        print("Dropping existing tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        print("Dropped existing tables")

    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created")

    await engine.dispose()


async def seed_data():
    """Seed initial data"""
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.db.session import get_async_engine
    from sqlalchemy.orm import sessionmaker

    engine = get_async_engine()
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        # Check if admin user already exists
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        admin_user = result.scalar_one_or_none()

        if admin_user:
            print("Admin user already exists, skipping seed")
            return

        print("Seeding initial data...")

        # Create admin user
        admin_user = User(
            gitlab_user_id=1,
            username="admin",
            email="admin@example.com",
            name="System Administrator",
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin_user)

        # Create demo user
        demo_user = User(
            gitlab_user_id=2,
            username="demo",
            email="demo@example.com",
            name="Demo User",
            role=UserRole.DEVELOPER,
            is_active=True,
        )
        session.add(demo_user)

        # Create demo project
        demo_project = Project(
            gitlab_project_id=1,
            name="demo-project",
            description="Demo CI/CD Project",
            gitlab_url="https://gitlab.example.com/demo/project",
            default_branch="main",
            config={
                "build_type": "RelWithDebInfo",
                "enable_ccache": True,
                "parallel_jobs": 4,
            },
            is_active=True,
        )
        session.add(demo_project)

        await session.commit()
        print("Initial data seeded successfully")

    await engine.dispose()


async def main():
    parser = argparse.ArgumentParser(description="Database initialization script")
    parser.add_argument("--seed", action="store_true", help="Seed initial data")
    parser.add_argument("--drop-existing", action="store_true", help="Drop existing tables (DESTRUCTIVE)")

    args = parser.parse_args()

    print(f"Database URL: {settings.database_url}")

    # Create tables
    await create_tables(drop_existing=args.drop_existing)

    # Seed data if requested
    if args.seed:
        await seed_data()

    print("\nDatabase initialization complete!")


if __name__ == "__main__":
    asyncio.run(main())
