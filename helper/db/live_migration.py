"""
Apply incremental database changes to an existing AGB2B database.

This module is intentionally additive and idempotent. It must not drop,
rename, truncate, or rebuild existing tables because production data already
exists in the current schema.

Usage:
    python helper/db/live_migration.py
    python helper/db/live_migration.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import DB_CONN_STRING

if TYPE_CHECKING:
    import pyodbc


@dataclass(frozen=True)
class Migration:
    name: str
    apply: Callable[[pyodbc.Connection, pyodbc.Cursor, bool], None]


def quote_identifier(identifier: str) -> str:
    return f"[{identifier.replace(']', ']]')}]"


def get_table_schema(cursor: pyodbc.Cursor, table_name: str) -> str:
    cursor.execute(
        """
        SELECT TABLE_SCHEMA
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME = ? AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY CASE WHEN TABLE_SCHEMA = 'dbo' THEN 0 ELSE 1 END
        """,
        table_name,
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Required table '{table_name}' does not exist.")
    return row.TABLE_SCHEMA


def column_exists(cursor: pyodbc.Cursor, schema_name: str, table_name: str, column_name: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND COLUMN_NAME = ?
        """,
        schema_name,
        table_name,
        column_name,
    )
    return cursor.fetchone() is not None


def ensure_migration_log_table(conn: pyodbc.Connection, cursor: pyodbc.Cursor, dry_run: bool) -> None:
    sql = """
    IF OBJECT_ID(N'[dbo].[schema_migrations]', N'U') IS NULL
    BEGIN
        CREATE TABLE [dbo].[schema_migrations] (
            [name] NVARCHAR(255) NOT NULL PRIMARY KEY,
            [applied_at] DATETIME NOT NULL DEFAULT GETDATE()
        )
    END
    """
    if dry_run:
        print("DRY RUN: ensure [dbo].[schema_migrations] exists")
        return
    cursor.execute(sql)
    conn.commit()


def migration_ocon_logo(conn: pyodbc.Connection, cursor: pyodbc.Cursor, dry_run: bool) -> None:
    try:
        table_name = "ocon"
        schema_name = get_table_schema(cursor, table_name)
    except RuntimeError:
        table_name = "wCon"
        schema_name = get_table_schema(cursor, table_name)

    column_name = "logo"

    if column_exists(cursor, schema_name, table_name, column_name):
        print(f"SKIP: {schema_name}.{table_name}.{column_name} already exists")
        return

    table_ref = f"{quote_identifier(schema_name)}.{quote_identifier(table_name)}"
    sql = f"ALTER TABLE {table_ref} ADD {quote_identifier(column_name)} VARCHAR(MAX) NULL"

    if dry_run:
        print(f"DRY RUN: {sql}")
        return

    cursor.execute(sql)
    conn.commit()
    print(f"APPLIED: added {schema_name}.{table_name}.{column_name}")


MIGRATIONS: tuple[Migration, ...] = (
    Migration("2026_08_10_add_ocon_logo", migration_ocon_logo),
)


def is_migration_applied(cursor: pyodbc.Cursor, migration_name: str) -> bool:
    cursor.execute("SELECT 1 FROM [dbo].[schema_migrations] WHERE [name] = ?", migration_name)
    return cursor.fetchone() is not None


def mark_migration_applied(conn: pyodbc.Connection, cursor: pyodbc.Cursor, migration_name: str, dry_run: bool) -> None:
    if dry_run:
        print(f"DRY RUN: mark migration '{migration_name}' as applied")
        return
    cursor.execute("INSERT INTO [dbo].[schema_migrations] ([name]) VALUES (?)", migration_name)
    conn.commit()


def run_migrations(dry_run: bool = False) -> None:
    try:
        import pyodbc
    except ModuleNotFoundError as exc:
        raise RuntimeError("pyodbc is required to run live database migrations.") from exc

    conn = pyodbc.connect(DB_CONN_STRING)
    cursor = conn.cursor()
    try:
        ensure_migration_log_table(conn, cursor, dry_run)
        for migration in MIGRATIONS:
            if not dry_run and is_migration_applied(cursor, migration.name):
                print(f"SKIP: migration '{migration.name}' already applied")
                continue

            print(f"RUN: {migration.name}")
            migration.apply(conn, cursor, dry_run)
            mark_migration_applied(conn, cursor, migration.name, dry_run)

        print("Live migrations finished successfully.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply safe live database migrations.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without applying them.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_migrations(dry_run=args.dry_run)
