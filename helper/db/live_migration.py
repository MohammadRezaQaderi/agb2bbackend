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
from quiz_packages.psy.generated_manifest import PACKAGE_NAMES as PSY_PACKAGE_NAMES

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


def migration_student_education(conn: pyodbc.Connection, cursor: pyodbc.Cursor, dry_run: bool) -> None:
    schema_name = get_table_schema(cursor, "stu")
    table_ref = f"{quote_identifier(schema_name)}.[stu]"
    for column_name, sql_type in (("education_level", "NVARCHAR(10)"), ("education_field", "NVARCHAR(30)")):
        if column_exists(cursor, schema_name, "stu", column_name):
            print(f"SKIP: {schema_name}.stu.{column_name} already exists")
            continue
        sql = f"ALTER TABLE {table_ref} ADD {quote_identifier(column_name)} {sql_type} NULL"
        if dry_run:
            print(f"DRY RUN: {sql}")
        else:
            cursor.execute(sql)

    # Historical rows are assigned by the birth year cutoff. The field cannot
    # be inferred from birth_date and intentionally remains NULL for existing rows.
    cutoff = int(os.getenv("AG_STUDENT_SECOND_PERIOD_MAX_BIRTH_YEAR", "1390"))
    if dry_run:
        print(f"DRY RUN: backfill dbo.stu.education_level using birth_date cutoff {cutoff}")
        return

    cursor.execute(f"SELECT [user_id], [birth_date] FROM {table_ref} WHERE [education_level] IS NULL")
    persian_digits = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    updates = []
    for row in cursor.fetchall():
        try:
            birth_year = int(str(row.birth_date).translate(persian_digits))
        except (TypeError, ValueError):
            continue
        if 1000 <= birth_year <= 9999:
            updates.append(("second" if birth_year <= cutoff else "first", row.user_id))
    if updates:
        cursor.executemany(
            f"UPDATE {table_ref} SET [education_level] = ? WHERE [user_id] = ? AND [education_level] IS NULL",
            updates,
        )
    conn.commit()
    print(f"APPLIED: added education columns and backfilled {len(updates)} student rows")


def migration_psy_capacity_packages(conn: pyodbc.Connection, cursor: pyodbc.Cursor, dry_run: bool) -> None:
    capacity_schema = get_table_schema(cursor, "capacity")
    package_schema = get_table_schema(cursor, "capacity_package")
    capacity_ref = f"{quote_identifier(capacity_schema)}.[capacity]"
    package_ref = f"{quote_identifier(package_schema)}.[capacity_package]"
    has_total_allowed = column_exists(
        cursor,
        package_schema,
        "capacity_package",
        "total_allowed",
    )
    package_values = ", ".join("(?)" for _ in PSY_PACKAGE_NAMES)
    columns = "[capacity_id], [package_name], [user_id], [allowed], [used], [created_time], [edited_time]"
    values = "c.[capacity_id], p.[package_name], c.[user_id], 0, 0, GETDATE(), GETDATE()"
    if has_total_allowed:
        columns = columns.replace("[allowed]", "[total_allowed], [allowed]")
        values = values.replace("c.[user_id], 0", "c.[user_id], 0, 0", 1)

    sql = f"""
        INSERT INTO {package_ref} ({columns})
        SELECT {values}
        FROM (
            SELECT [user_id], MIN([capacity_id]) AS [capacity_id]
            FROM {capacity_ref}
            WHERE [user_id] IS NOT NULL
            GROUP BY [user_id]
        ) AS c
        CROSS JOIN (VALUES {package_values}) AS p([package_name])
        WHERE NOT EXISTS (
              SELECT 1
              FROM {package_ref} AS existing
              WHERE existing.[user_id] = c.[user_id]
                AND existing.[package_name] = p.[package_name]
          )
    """

    if dry_run:
        print(
            f"DRY RUN: add missing zero-capacity rows for {len(PSY_PACKAGE_NAMES)} PSY packages"
        )
        return

    cursor.execute(sql, *PSY_PACKAGE_NAMES)
    inserted_rows = cursor.rowcount
    conn.commit()
    print(f"APPLIED: added {inserted_rows} missing PSY capacity rows")


MIGRATIONS: tuple[Migration, ...] = (
    Migration("2026_08_10_add_ocon_logo", migration_ocon_logo),
    Migration("2026_11_03_add_student_education", migration_student_education),
    Migration("2026_11_06_add_psy_capacity_packages", migration_psy_capacity_packages),
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
