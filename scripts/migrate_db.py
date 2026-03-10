#!/usr/bin/env python3
"""
Database migration utility script

Usage:
    python scripts/migrate_db.py [command]

Commands:
    init        Initialize alembic (creates alembic directory)
    current     Show current revision
    history     Show migration history
    upgrade     Upgrade to latest migration
    downgrade   Downgrade one migration
    heads       Show head revisions
    branches    Show branch points
    create      Create a new migration
    revision    Create a new revision file
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic import command
from alembic.config import Config
from src.utils.config import settings


def get_alembic_config() -> Config:
    """Get Alembic configuration"""
    alembic_ini = Path(__file__).parent.parent / "alembic.ini"

    if not alembic_ini.exists():
        print(f"Error: alembic.ini not found at {alembic_ini}")
        sys.exit(1)

    config = Config(str(alembic_ini))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    return config


def cmd_init(args):
    """Initialize Alembic"""
    print("Initializing Alembic...")
    # Already initialized, skip
    print("Alembic already initialized in /alembic directory")


def cmd_current(args):
    """Show current revision"""
    config = get_alembic_config()
    command.current(config, verbose=args.verbose)


def cmd_history(args):
    """Show migration history"""
    config = get_alembic_config()
    command.history(config, verbose=args.verbose)


def cmd_upgrade(args):
    """Upgrade to latest migration"""
    config = get_alembic_config()

    # Determine revision
    revision = args.revision if args.revision else "head"

    print(f"Upgrading database to {revision}...")
    command.upgrade(config, revision)
    print(f"Database upgraded to {revision}")


def cmd_downgrade(args):
    """Downgrade one migration"""
    config = get_alembic_config()

    # Determine revision
    revision = args.revision if args.revision else "-1"

    print(f"Downgrading database by {revision}...")
    command.downgrade(config, revision)
    print(f"Database downgraded by {revision}")


def cmd_heads(args):
    """Show head revisions"""
    config = get_alembic_config()
    command.heads(config, verbose=args.verbose)


def cmd_branches(args):
    """Show branch points"""
    config = get_alembic_config()
    command.branches(config, verbose=args.verbose)


def cmd_create(args):
    """Create a new migration"""
    config = get_alembic_config()

    message = args.message
    if not message:
        print("Error: -m/--message is required for create")
        sys.exit(1)

    print(f"Creating new migration: {message}")
    command.revision(config, message=message, autogenerate=args.autogenerate)


def cmd_revision(args):
    """Create a new revision file"""
    config = get_alembic_config()

    message = args.message
    if not message:
        print("Error: -m/--message is required for revision")
        sys.exit(1)

    print(f"Creating revision: {message}")
    command.revision(config, message=message)


def cmd_show(args):
    """Show current database version"""
    from src.db.session import get_async_engine
    from sqlalchemy import text

    async def show_version():
        engine = get_async_engine()
        async with engine.connect() as conn:
            try:
                result = await conn.execute(text("SELECT version_num FROM alembic_version"))
                version = result.scalar()
                print(f"Current database version: {version}")
            except Exception as e:
                print(f"Database not initialized or no migrations applied: {e}")

    asyncio.run(show_version())


def main():
    parser = argparse.ArgumentParser(
        description="Database migration utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Init command
    subparsers.add_parser("init", help="Initialize alembic")

    # Current command
    subparsers.add_parser("current", help="Show current revision")

    # History command
    subparsers.add_parser("history", help="Show migration history")

    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade to latest migration")
    upgrade_parser.add_argument("revision", nargs="?", help="Target revision (default: head)")

    # Downgrade command
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade one migration")
    downgrade_parser.add_argument("revision", nargs="?", help="Target revision (default: -1)")

    # Heads command
    subparsers.add_parser("heads", help="Show head revisions")

    # Branches command
    subparsers.add_parser("branches", help="Show branch points")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("-m", "--message", required=True, help="Migration message")
    create_parser.add_argument("--autogenerate", action="store_true", help="Autogenerate migration from models")

    # Revision command
    revision_parser = subparsers.add_parser("revision", help="Create a new revision file")
    revision_parser.add_argument("-m", "--message", required=True, help="Revision message")

    # Show command
    subparsers.add_parser("show", help="Show current database version")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Dispatch to command handlers
    commands = {
        "init": cmd_init,
        "current": cmd_current,
        "history": cmd_history,
        "upgrade": cmd_upgrade,
        "downgrade": cmd_downgrade,
        "heads": cmd_heads,
        "branches": cmd_branches,
        "create": cmd_create,
        "revision": cmd_revision,
        "show": cmd_show,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
