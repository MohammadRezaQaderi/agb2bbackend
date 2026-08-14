"""
Move an existing AGB2B database toward the current db_creator.py schema.

The migration is intentionally additive and idempotent. It does not drop
production data. Risky constraints are added only when current data is clean;
otherwise the script prints a warning so the data can be fixed first.

Usage:
    python3 helper/db/architecture_migration.py --dry-run
    python3 helper/db/architecture_migration.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import DB_CONN_STRING


def quote_name(name: str) -> str:
    return f"[{name.replace(']', ']]')}]"


def table_exists(cursor: Any, table_name: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ? AND TABLE_TYPE = 'BASE TABLE'
        """,
        table_name,
    )
    return cursor.fetchone() is not None


def column_exists(cursor: Any, table_name: str, column_name: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ? AND COLUMN_NAME = ?
        """,
        table_name,
        column_name,
    )
    return cursor.fetchone() is not None


def object_exists(cursor: Any, object_name: str) -> bool:
    cursor.execute("SELECT 1 FROM sys.objects WHERE name = ?", object_name)
    return cursor.fetchone() is not None


def index_exists(cursor: Any, table_name: str, index_name: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM sys.indexes i
        INNER JOIN sys.tables t ON i.object_id = t.object_id
        WHERE t.name = ? AND i.name = ?
        """,
        table_name,
        index_name,
    )
    return cursor.fetchone() is not None


def run_sql(conn: Any, cursor: Any, sql: str, dry_run: bool, label: str) -> None:
    if dry_run:
        print(f"DRY RUN: {label}")
        print(sql.strip())
        return
    cursor.execute(sql)
    conn.commit()
    print(f"APPLIED: {label}")


def scalar(cursor: Any, sql: str, params: tuple[Any, ...] = ()) -> int:
    cursor.execute(sql, *params)
    row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def ensure_column(conn: Any, cursor: Any, table_name: str, column_name: str, definition: str, dry_run: bool) -> None:
    if column_exists(cursor, table_name, column_name):
        print(f"SKIP: {table_name}.{column_name} already exists")
        return
    run_sql(
        conn,
        cursor,
        f"ALTER TABLE {quote_name(table_name)} ADD {quote_name(column_name)} {definition}",
        dry_run,
        f"add {table_name}.{column_name}",
    )


def ensure_index_if_clean(
    conn: Any,
    cursor: Any,
    table_name: str,
    index_name: str,
    columns_sql: str,
    duplicate_sql: str | None,
    dry_run: bool,
    unique: bool = True,
    where_sql: str | None = None,
) -> None:
    if index_exists(cursor, table_name, index_name):
        print(f"SKIP: index {index_name} already exists")
        return

    if duplicate_sql and scalar(cursor, duplicate_sql) > 0:
        print(f"WARN: skipped {index_name}; duplicate data exists")
        return

    unique_sql = "UNIQUE " if unique else ""
    where_clause = f" WHERE {where_sql}" if where_sql else ""
    sql = f"CREATE {unique_sql}INDEX {quote_name(index_name)} ON {quote_name(table_name)} ({columns_sql}){where_clause}"
    run_sql(conn, cursor, sql, dry_run, f"create index {index_name}")


def ensure_fk_if_clean(
    conn: Any,
    cursor: Any,
    constraint_name: str,
    table_name: str,
    column_name: str,
    ref_table: str,
    ref_column: str,
    orphan_sql: str,
    dry_run: bool,
) -> None:
    if object_exists(cursor, constraint_name):
        print(f"SKIP: FK {constraint_name} already exists")
        return

    if scalar(cursor, orphan_sql) > 0:
        print(f"WARN: skipped {constraint_name}; orphan data exists")
        return

    sql = (
        f"ALTER TABLE {quote_name(table_name)} WITH CHECK ADD CONSTRAINT {quote_name(constraint_name)} "
        f"FOREIGN KEY ({quote_name(column_name)}) REFERENCES {quote_name(ref_table)}({quote_name(ref_column)})"
    )
    run_sql(conn, cursor, sql, dry_run, f"add FK {constraint_name}")


def ensure_student_package_access(conn: Any, cursor: Any, dry_run: bool) -> None:
    if table_exists(cursor, "student_package_access"):
        print("SKIP: student_package_access already exists")
        return

    sql = """
    CREATE TABLE [student_package_access] (
        [id] INT IDENTITY(1, 1) PRIMARY KEY,
        [stu_user_id] INT NOT NULL,
        [owner_user_id] INT NULL,
        [consultant_user_id] INT NULL,
        [package_name] NVARCHAR(50) NOT NULL,
        [permission] BIT NOT NULL DEFAULT 0,
        [limit] BIT NOT NULL DEFAULT 0,
        [created_time] DATETIME DEFAULT GETDATE(),
        [edited_time] DATETIME DEFAULT GETDATE(),
        CONSTRAINT [uq_student_package_access] UNIQUE ([stu_user_id], [package_name])
    )
    """
    run_sql(conn, cursor, sql, dry_run, "create student_package_access")


def backfill_student_package_access(conn: Any, cursor: Any, dry_run: bool) -> None:
    if not table_exists(cursor, "student_package_access"):
        print("WARN: student_package_access does not exist; cannot backfill")
        return

    cursor.execute("SELECT user_id, ins_id, con_id, access FROM stu WHERE access IS NOT NULL")
    rows = cursor.fetchall()
    inserts = 0
    updates = 0

    for row in rows:
        raw_access = getattr(row, "access", None) or "{}"
        try:
            access_data = json.loads(raw_access) if isinstance(raw_access, str) else raw_access
        except (TypeError, json.JSONDecodeError):
            print(f"WARN: invalid access JSON for stu.user_id={row.user_id}; skipped")
            continue

        if not isinstance(access_data, dict):
            continue

        for package_name, package_info in access_data.items():
            if isinstance(package_info, dict):
                permission = 1 if int(package_info.get("permission") or 0) else 0
                limit = 1 if int(package_info.get("limit") or 0) else 0
            elif isinstance(package_info, bool):
                permission = 1 if package_info else 0
                limit = 0
            else:
                try:
                    permission = 1 if int(package_info or 0) else 0
                except (TypeError, ValueError):
                    permission = 0
                limit = 0

            cursor.execute(
                """
                SELECT id, permission, [limit]
                FROM student_package_access
                WHERE stu_user_id = ? AND package_name = ?
                """,
                row.user_id,
                str(package_name).upper(),
            )
            existing = cursor.fetchone()

            if dry_run:
                if existing:
                    updates += 1
                else:
                    inserts += 1
                continue

            if existing:
                cursor.execute(
                    """
                    UPDATE student_package_access
                    SET owner_user_id = ?, consultant_user_id = ?, permission = ?, [limit] = ?, edited_time = GETDATE()
                    WHERE id = ?
                    """,
                    row.ins_id,
                    row.con_id,
                    permission,
                    limit,
                    existing.id,
                )
                updates += 1
            else:
                cursor.execute(
                    """
                    INSERT INTO student_package_access
                        (stu_user_id, owner_user_id, consultant_user_id, package_name, permission, [limit])
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    row.user_id,
                    row.ins_id,
                    row.con_id,
                    str(package_name).upper(),
                    permission,
                    limit,
                )
                inserts += 1

    if dry_run:
        print(f"DRY RUN: backfill student_package_access inserts={inserts}, updates={updates}")
        return

    conn.commit()
    print(f"APPLIED: backfill student_package_access inserts={inserts}, updates={updates}")


def migrate_passwords_to_hash(conn: Any, cursor: Any, dry_run: bool) -> None:
    from helper.func_helper import decrypt_password, hash_password, is_password_hash

    cursor.execute("SELECT user_id, password FROM users WHERE password IS NOT NULL")
    rows = cursor.fetchall()
    changed = 0

    for row in rows:
        stored_password = row.password
        if is_password_hash(stored_password):
            continue

        plain_password = decrypt_password(stored_password)
        if plain_password is None:
            plain_password = stored_password

        new_password = hash_password(plain_password)
        changed += 1
        if not dry_run:
            cursor.execute(
                "UPDATE users SET password = ?, edited_time = GETDATE() WHERE user_id = ?",
                new_password,
                row.user_id,
            )

    if dry_run:
        print(f"DRY RUN: migrate users.password to hash for {changed} users")
        return

    conn.commit()
    print(f"APPLIED: migrated users.password to hash for {changed} users")


def alter_text_columns(conn: Any, cursor: Any, dry_run: bool) -> None:
    changes = (
        ("notifications", "roles", "NVARCHAR(100) NULL"),
        ("notifications", "priority", "NVARCHAR(100) NULL"),
        ("api_logs", "end_point", "NVARCHAR(100) NULL"),
        ("api_logs", "func_name", "NVARCHAR(100) NULL"),
        ("stu", "access", "NVARCHAR(MAX) NULL"),
    )
    for table_name, column_name, definition in changes:
        if table_exists(cursor, table_name) and column_exists(cursor, table_name, column_name):
            try:
                run_sql(
                    conn,
                    cursor,
                    f"ALTER TABLE {quote_name(table_name)} ALTER COLUMN {quote_name(column_name)} {definition}",
                    dry_run,
                    f"alter {table_name}.{column_name}",
                )
            except Exception as exc:
                conn.rollback()
                print(f"WARN: skipped alter {table_name}.{column_name}: {exc}")


def run_migration(dry_run: bool) -> None:
    try:
        import pyodbc
    except ModuleNotFoundError as exc:
        raise RuntimeError("pyodbc is required to run database migrations.") from exc

    conn = pyodbc.connect(DB_CONN_STRING)
    cursor = conn.cursor()

    try:
        ensure_column(conn, cursor, "capacity_package", "total_allowed", "INT NULL", dry_run)
        if column_exists(cursor, "capacity_package", "total_allowed"):
            run_sql(
                conn,
                cursor,
                """
                UPDATE capacity_package
                SET total_allowed = ISNULL(allowed, 0) + ISNULL(used, 0), edited_time = GETDATE()
                WHERE total_allowed IS NULL
                   OR (total_allowed = 0 AND (ISNULL(allowed, 0) > 0 OR ISNULL(used, 0) > 0))
                """,
                dry_run,
                "backfill capacity_package.total_allowed",
            )

        ensure_student_package_access(conn, cursor, dry_run)
        backfill_student_package_access(conn, cursor, dry_run)
        alter_text_columns(conn, cursor, dry_run)
        migrate_passwords_to_hash(conn, cursor, dry_run)

        ensure_index_if_clean(
            conn,
            cursor,
            "users",
            "ux_users_phone",
            "phone",
            "SELECT COUNT(*) FROM (SELECT phone FROM users WHERE phone IS NOT NULL GROUP BY phone HAVING COUNT(*) > 1) d",
            dry_run,
            unique=True,
            where_sql="phone IS NOT NULL",
        )
        ensure_index_if_clean(
            conn,
            cursor,
            "capacity",
            "ux_capacity_user_id",
            "user_id",
            "SELECT COUNT(*) FROM (SELECT user_id FROM capacity WHERE user_id IS NOT NULL GROUP BY user_id HAVING COUNT(*) > 1) d",
            dry_run,
            unique=True,
            where_sql="user_id IS NOT NULL",
        )
        ensure_index_if_clean(
            conn,
            cursor,
            "capacity_package",
            "ux_capacity_package_user_package",
            "user_id, package_name",
            """
            SELECT COUNT(*) FROM (
                SELECT user_id, package_name
                FROM capacity_package
                WHERE user_id IS NOT NULL AND package_name IS NOT NULL
                GROUP BY user_id, package_name
                HAVING COUNT(*) > 1
            ) d
            """,
            dry_run,
        )
        ensure_index_if_clean(
            conn,
            cursor,
            "quiz_answer",
            "ux_quiz_answer_user_kind_quiz",
            "user_id, quiz_kind, quiz_id",
            """
            SELECT COUNT(*) FROM (
                SELECT user_id, quiz_kind, quiz_id
                FROM quiz_answer
                WHERE user_id IS NOT NULL AND quiz_kind IS NOT NULL AND quiz_id IS NOT NULL
                GROUP BY user_id, quiz_kind, quiz_id
                HAVING COUNT(*) > 1
            ) d
            """,
            dry_run,
        )
        ensure_index_if_clean(
            conn,
            cursor,
            "scores",
            "ux_scores_user_id",
            "user_id",
            "SELECT COUNT(*) FROM (SELECT user_id FROM scores WHERE user_id IS NOT NULL GROUP BY user_id HAVING COUNT(*) > 1) d",
            dry_run,
            where_sql="user_id IS NOT NULL",
        )
        ensure_index_if_clean(
            conn,
            cursor,
            "scl_scores",
            "ux_scl_scores_user_id",
            "user_id",
            "SELECT COUNT(*) FROM (SELECT user_id FROM scl_scores WHERE user_id IS NOT NULL GROUP BY user_id HAVING COUNT(*) > 1) d",
            dry_run,
            where_sql="user_id IS NOT NULL",
        )

        ensure_index_if_clean(conn, cursor, "stu", "ix_stu_ins_id", "ins_id", None, dry_run, unique=False)
        ensure_index_if_clean(conn, cursor, "stu", "ix_stu_con_id", "con_id", None, dry_run, unique=False)
        ensure_index_if_clean(conn, cursor, "con", "ix_con_ins_id", "ins_id", None, dry_run, unique=False)
        ensure_index_if_clean(
            conn,
            cursor,
            "quiz_answer",
            "ix_quiz_answer_dashboard",
            "ins_id, con_id, quiz_kind, state, quiz_id",
            None,
            dry_run,
            unique=False,
        )
        ensure_index_if_clean(
            conn,
            cursor,
            "redis_log",
            "ix_redis_log_user_kind",
            "user_id, kind",
            None,
            dry_run,
            unique=False,
        )

        ensure_fk_if_clean(
            conn,
            cursor,
            "fk_capacity_user",
            "capacity",
            "user_id",
            "users",
            "user_id",
            "SELECT COUNT(*) FROM capacity c LEFT JOIN users u ON c.user_id = u.user_id WHERE c.user_id IS NOT NULL AND u.user_id IS NULL",
            dry_run,
        )
        ensure_fk_if_clean(
            conn,
            cursor,
            "fk_capacity_package_user",
            "capacity_package",
            "user_id",
            "users",
            "user_id",
            "SELECT COUNT(*) FROM capacity_package cp LEFT JOIN users u ON cp.user_id = u.user_id WHERE cp.user_id IS NOT NULL AND u.user_id IS NULL",
            dry_run,
        )
        ensure_fk_if_clean(
            conn,
            cursor,
            "fk_quiz_answer_user",
            "quiz_answer",
            "user_id",
            "users",
            "user_id",
            "SELECT COUNT(*) FROM quiz_answer q LEFT JOIN users u ON q.user_id = u.user_id WHERE q.user_id IS NOT NULL AND u.user_id IS NULL",
            dry_run,
        )

        print("Architecture migration finished.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply additive architecture migrations to AGB2B.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without applying them.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_migration(dry_run=args.dry_run)
