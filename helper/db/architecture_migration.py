"""
Move an existing AGB2B database toward the current db_creator.py schema.

The migration is intentionally additive and idempotent. It does not drop
production data. Risky constraints are added only when current data is clean;
otherwise the script prints a warning so the data can be fixed first.

Usage:
    python3 helper/db/architecture_migration.py --dry-run
    python3 helper/db/architecture_migration.py --migrate-password-hash
    python3 helper/db/architecture_migration.py --drop-legacy-old-tables
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


def rename_table_if_needed(
    conn: Any,
    cursor: Any,
    old_name: str,
    new_name: str,
    dry_run: bool,
) -> None:
    old_exists = table_exists(cursor, old_name)
    new_exists = table_exists(cursor, new_name)

    if new_exists:
        if old_exists:
            print(f"WARN: both {old_name} and {new_name} exist; skipped automatic table merge")
        else:
            print(f"SKIP: table {new_name} already exists")
        return

    if not old_exists:
        print(f"SKIP: neither {old_name} nor {new_name} exists")
        return

    sql = f"EXEC sp_rename N'dbo.{old_name}', N'{new_name}'"
    run_sql(conn, cursor, sql, dry_run, f"rename table {old_name} to {new_name}")


def rename_column_if_needed(
    conn: Any,
    cursor: Any,
    table_name: str,
    old_name: str,
    new_name: str,
    dry_run: bool,
) -> None:
    if not table_exists(cursor, table_name):
        print(f"SKIP: table {table_name} does not exist")
        return

    if column_exists(cursor, table_name, new_name):
        print(f"SKIP: column {table_name}.{new_name} already exists")
        return

    if not column_exists(cursor, table_name, old_name):
        print(f"SKIP: column {table_name}.{old_name} does not exist")
        return

    sql = f"EXEC sp_rename N'dbo.{table_name}.{old_name}', N'{new_name}', N'COLUMN'"
    run_sql(conn, cursor, sql, dry_run, f"rename column {table_name}.{old_name} to {new_name}")


def drop_column_if_exists(
    conn: Any,
    cursor: Any,
    table_name: str,
    column_name: str,
    dry_run: bool,
) -> None:
    if not table_exists(cursor, table_name):
        print(f"SKIP: table {table_name} does not exist")
        return

    if not column_exists(cursor, table_name, column_name):
        print(f"SKIP: column {table_name}.{column_name} does not exist")
        return

    try:
        run_sql(
            conn,
            cursor,
            f"ALTER TABLE {quote_name(table_name)} DROP COLUMN {quote_name(column_name)}",
            dry_run,
            f"drop duplicate identity column {table_name}.{column_name}",
        )
    except Exception as exc:
        conn.rollback()
        print(f"WARN: skipped drop {table_name}.{column_name}: {exc}")


def drop_default_constraints_for_column(
    conn: Any,
    cursor: Any,
    table_name: str,
    column_name: str,
    dry_run: bool,
) -> None:
    cursor.execute(
        """
        SELECT dc.name
        FROM sys.default_constraints dc
        INNER JOIN sys.tables t ON t.object_id = dc.parent_object_id
        INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
        INNER JOIN sys.columns c
            ON c.object_id = t.object_id
           AND c.column_id = dc.parent_column_id
        WHERE s.name = 'dbo' AND t.name = ? AND c.name = ?
        """,
        table_name,
        column_name,
    )
    for row in cursor.fetchall():
        constraint_name = row[0]
        run_sql(
            conn,
            cursor,
            f"ALTER TABLE dbo.{quote_name(table_name)} DROP CONSTRAINT {quote_name(constraint_name)}",
            dry_run,
            f"drop default constraint {constraint_name} on {table_name}.{column_name}",
        )


def legacy_old_tables(cursor: Any) -> list[str]:
    cursor.execute(
        """
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_TYPE = 'BASE TABLE'
          AND TABLE_NAME LIKE '%[_]old'
        ORDER BY TABLE_NAME
        """
    )
    return [row[0] for row in cursor.fetchall()]


def drop_legacy_old_tables(conn: Any, cursor: Any, dry_run: bool) -> None:
    tables = legacy_old_tables(cursor)
    if not tables:
        print("SKIP: no legacy *_old tables found")
        return

    for table_name in tables:
        try:
            run_sql(
                conn,
                cursor,
                f"DROP TABLE dbo.{quote_name(table_name)}",
                dry_run,
                f"drop legacy table {table_name}",
            )
        except Exception as exc:
            conn.rollback()
            print(f"WARN: skipped drop legacy table {table_name}: {exc}")


def remove_role_identity_mirrors(conn: Any, cursor: Any, dry_run: bool) -> None:
    role_tables = ("ins", "sch", "ocon", "con", "stu")
    user_id_identity_tables = (
        "capacity",
        "capacity_package",
        "scores",
        "scl_scores",
        "result_state",
        "hedayat_fields",
        "tokens",
    )

    for table_name in role_tables:
        if not table_exists(cursor, table_name):
            print(f"SKIP: table {table_name} does not exist")
            continue

        if column_exists(cursor, table_name, "phone"):
            run_sql(
                conn,
                cursor,
                f"""
                UPDATE u
                SET u.phone = r.phone, u.edited_time = GETDATE()
                FROM users u
                INNER JOIN {quote_name(table_name)} r ON r.user_id = u.user_id
                WHERE (u.phone IS NULL OR LTRIM(RTRIM(u.phone)) = '')
                  AND r.phone IS NOT NULL
                  AND LTRIM(RTRIM(r.phone)) <> ''
                """,
                dry_run,
                f"backfill users.phone from {table_name}.phone where missing",
            )

        if column_exists(cursor, table_name, "password"):
            run_sql(
                conn,
                cursor,
                f"""
                UPDATE u
                SET u.password = r.password, u.edited_time = GETDATE()
                FROM users u
                INNER JOIN {quote_name(table_name)} r ON r.user_id = u.user_id
                WHERE (u.password IS NULL OR LTRIM(RTRIM(u.password)) = '')
                  AND r.password IS NOT NULL
                  AND LTRIM(RTRIM(r.password)) <> ''
                """,
                dry_run,
                f"backfill users.password from {table_name}.password where missing",
            )

    for table_name in role_tables:
        drop_column_if_exists(conn, cursor, table_name, "password", dry_run)
        drop_column_if_exists(conn, cursor, table_name, "phone", dry_run)

    for table_name in user_id_identity_tables:
        drop_column_if_exists(conn, cursor, table_name, "phone", dry_run)


def normalize_relation_columns(conn: Any, cursor: Any, dry_run: bool) -> None:
    renames = (
        ("con", "ins_id", "owner_user_id"),
        ("stu", "ins_id", "owner_user_id"),
        ("stu", "con_id", "consultant_user_id"),
        ("quiz_attempt", "ins_id", "owner_user_id"),
        ("quiz_attempt", "con_id", "consultant_user_id"),
    )
    for table_name, old_name, new_name in renames:
        rename_column_if_needed(conn, cursor, table_name, old_name, new_name, dry_run)

    drop_column_if_exists(conn, cursor, "con", "ins_role", dry_run)
    drop_column_if_exists(conn, cursor, "stu", "ins_role", dry_run)
    drop_column_if_exists(conn, cursor, "tokens", "role", dry_run)


def normalize_ocon_role_names(conn: Any, cursor: Any, dry_run: bool) -> None:
    exact_role_columns = (
        ("users", "role"),
        ("comments", "role"),
        ("stu", "ins_role"),
        ("con", "ins_role"),
    )
    for table_name, column_name in exact_role_columns:
        if table_exists(cursor, table_name) and column_exists(cursor, table_name, column_name):
            run_sql(
                conn,
                cursor,
                (
                    f"UPDATE {quote_name(table_name)} "
                    f"SET {quote_name(column_name)} = 'ocon', edited_time = GETDATE() "
                    f"WHERE {quote_name(column_name)} IN ('wCon', 'wcon', 'WCon')"
                ),
                dry_run,
                f"normalize {table_name}.{column_name} wCon to ocon",
            )

    replace_text_columns = (
        ("notifications", "roles"),
        ("api_logs", "end_point"),
    )
    for table_name, column_name in replace_text_columns:
        if table_exists(cursor, table_name) and column_exists(cursor, table_name, column_name):
            run_sql(
                conn,
                cursor,
                (
                    f"UPDATE {quote_name(table_name)} "
                    f"SET {quote_name(column_name)} = REPLACE(REPLACE(REPLACE({quote_name(column_name)}, 'wCon', 'ocon'), 'wcon', 'ocon'), 'WCon', 'ocon'), "
                    f"edited_time = GETDATE() "
                    f"WHERE {quote_name(column_name)} LIKE '%wCon%' "
                    f"OR {quote_name(column_name)} LIKE '%wcon%' "
                    f"OR {quote_name(column_name)} LIKE '%WCon%'"
                ),
                dry_run,
                f"replace legacy ocon text in {table_name}.{column_name}",
            )


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
    if not table_exists(cursor, table_name):
        print(f"SKIP: table {table_name} does not exist; cannot create index {index_name}")
        return

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
    if not table_exists(cursor, table_name):
        print(f"SKIP: table {table_name} does not exist; cannot add FK {constraint_name}")
        return

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


def ensure_notification_reads(conn: Any, cursor: Any, dry_run: bool) -> None:
    if not table_exists(cursor, "notifications") or not table_exists(cursor, "users"):
        print("SKIP: notification_reads requires notifications and users tables")
        return

    if table_exists(cursor, "notification_reads"):
        print("SKIP: notification_reads already exists")
        return

    sql = """
    CREATE TABLE [notification_reads] (
        [id] INT IDENTITY(1, 1) NOT NULL PRIMARY KEY,
        [notification_id] INT NOT NULL,
        [user_id] INT NOT NULL,
        [created_time] DATETIME DEFAULT GETDATE(),
        CONSTRAINT [fk_notification_reads_notification]
            FOREIGN KEY ([notification_id]) REFERENCES [notifications]([id]),
        CONSTRAINT [fk_notification_reads_user]
            FOREIGN KEY ([user_id]) REFERENCES [users]([user_id]),
        CONSTRAINT [ux_notification_reads_notification_user]
            UNIQUE ([notification_id], [user_id])
    )
    """
    run_sql(conn, cursor, sql, dry_run, "create notification_reads")


def ensure_quiz_attempt_tables(conn: Any, cursor: Any, dry_run: bool) -> None:
    if not table_exists(cursor, "quiz_attempt"):
        run_sql(
            conn,
            cursor,
            """
            CREATE TABLE [quiz_attempt] (
                [id] INT IDENTITY(1, 1) PRIMARY KEY,
                [user_id] INT NOT NULL,
                [quiz_kind] VARCHAR(25) NOT NULL,
                [quiz_id] INT NOT NULL,
                [state] INT NOT NULL DEFAULT 1,
                [remain_time] INT NULL,
                [owner_user_id] INT NULL,
                [consultant_user_id] INT NULL,
                [created_time] DATETIME DEFAULT GETDATE(),
                [edited_time] DATETIME DEFAULT GETDATE()
            )
            """,
            dry_run,
            "create quiz_attempt",
        )
    else:
        print("SKIP: quiz_attempt already exists")

    if not table_exists(cursor, "quiz_question_answer"):
        run_sql(
            conn,
            cursor,
            """
            CREATE TABLE [quiz_question_answer] (
                [id] INT IDENTITY(1, 1) PRIMARY KEY,
                [attempt_id] INT NOT NULL,
                [user_id] INT NOT NULL,
                [quiz_kind] VARCHAR(25) NOT NULL,
                [quiz_id] INT NOT NULL,
                [question_id] INT NOT NULL,
                [answer_value] NVARCHAR(MAX) NOT NULL,
                [created_time] DATETIME DEFAULT GETDATE(),
                [edited_time] DATETIME DEFAULT GETDATE()
            )
            """,
            dry_run,
            "create quiz_question_answer",
        )
    else:
        print("SKIP: quiz_question_answer already exists")


def backfill_student_package_access(conn: Any, cursor: Any, dry_run: bool) -> None:
    if not table_exists(cursor, "student_package_access"):
        print("WARN: student_package_access does not exist; cannot backfill")
        return

    owner_column = "owner_user_id" if column_exists(cursor, "stu", "owner_user_id") else "ins_id"
    consultant_column = "consultant_user_id" if column_exists(cursor, "stu", "consultant_user_id") else "con_id"
    cursor.execute(
        f"""
        SELECT user_id, {quote_name(owner_column)} AS owner_user_id,
               {quote_name(consultant_column)} AS consultant_user_id, access
        FROM stu
        WHERE access IS NOT NULL
        """
    )
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
                    row.owner_user_id,
                    row.consultant_user_id,
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
                    row.owner_user_id,
                    row.consultant_user_id,
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
    password_hash_like = "pbkdf2_sha256$%"

    if dry_run:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM users
            WHERE password IS NOT NULL
              AND password NOT LIKE ?
            """,
            password_hash_like,
        )
        row = cursor.fetchone()
        changed = int(row[0] or 0) if row else 0
        print(f"DRY RUN: migrate users.password to hash for {changed} users")
        return

    from helper.func_helper import decrypt_password, hash_password

    cursor.execute(
        """
        SELECT user_id, password
        FROM users
        WHERE password IS NOT NULL
          AND password NOT LIKE ?
        """,
        password_hash_like,
    )
    rows = cursor.fetchall()
    changed = 0

    for row in rows:
        stored_password = row.password
        plain_password = decrypt_password(stored_password)
        if plain_password is None:
            plain_password = stored_password

        new_password = hash_password(plain_password)
        changed += 1
        cursor.execute(
            "UPDATE users SET password = ?, edited_time = GETDATE() WHERE user_id = ?",
            new_password,
            row.user_id,
        )
        if changed % 500 == 0:
            print(f"PROGRESS: migrated users.password hashes for {changed} users")

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
                drop_default_constraints_for_column(conn, cursor, table_name, column_name, dry_run)
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


def run_migration(
    dry_run: bool,
    migrate_password_hash: bool,
    drop_legacy_tables: bool,
) -> None:
    try:
        import pyodbc
    except ModuleNotFoundError as exc:
        raise RuntimeError("pyodbc is required to run database migrations.") from exc

    conn = pyodbc.connect(DB_CONN_STRING)
    cursor = conn.cursor()

    try:
        rename_table_if_needed(conn, cursor, "wCon", "ocon", dry_run)
        rename_table_if_needed(conn, cursor, "redis_log", "redis_logs", dry_run)
        rename_table_if_needed(conn, cursor, "discount", "discounts", dry_run)
        rename_table_if_needed(conn, cursor, "error_log", "quiz_missing_answers", dry_run)
        rename_column_if_needed(conn, cursor, "ocon", "wCon_id", "ocon_id", dry_run)
        rename_column_if_needed(conn, cursor, "quiz_missing_answers", "q_id", "question_id", dry_run)
        normalize_ocon_role_names(conn, cursor, dry_run)
        normalize_relation_columns(conn, cursor, dry_run)
        remove_role_identity_mirrors(conn, cursor, dry_run)

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
        ensure_notification_reads(conn, cursor, dry_run)
        ensure_quiz_attempt_tables(conn, cursor, dry_run)
        backfill_student_package_access(conn, cursor, dry_run)
        alter_text_columns(conn, cursor, dry_run)
        if migrate_password_hash:
            migrate_passwords_to_hash(conn, cursor, dry_run)
        else:
            print("SKIP: users.password hash migration")

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
            "quiz_attempt",
            "ux_quiz_attempt_user_kind_quiz",
            "user_id, quiz_kind, quiz_id",
            """
            SELECT COUNT(*) FROM (
                SELECT user_id, quiz_kind, quiz_id
                FROM quiz_attempt
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
            "quiz_question_answer",
            "ux_quiz_question_answer_attempt_question",
            "attempt_id, question_id",
            """
            SELECT COUNT(*) FROM (
                SELECT attempt_id, question_id
                FROM quiz_question_answer
                WHERE attempt_id IS NOT NULL AND question_id IS NOT NULL
                GROUP BY attempt_id, question_id
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

        ensure_index_if_clean(conn, cursor, "stu", "ix_stu_owner_user_id", "owner_user_id", None, dry_run, unique=False)
        ensure_index_if_clean(
            conn, cursor, "stu", "ix_stu_consultant_user_id", "consultant_user_id", None, dry_run, unique=False
        )
        ensure_index_if_clean(conn, cursor, "con", "ix_con_owner_user_id", "owner_user_id", None, dry_run, unique=False)
        ensure_index_if_clean(
            conn,
            cursor,
            "quiz_attempt",
            "ix_quiz_attempt_dashboard",
            "owner_user_id, consultant_user_id, quiz_kind, state, quiz_id",
            None,
            dry_run,
            unique=False,
        )
        ensure_index_if_clean(
            conn,
            cursor,
            "redis_logs",
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
            "fk_quiz_attempt_user",
            "quiz_attempt",
            "user_id",
            "users",
            "user_id",
            "SELECT COUNT(*) FROM quiz_attempt q LEFT JOIN users u ON q.user_id = u.user_id WHERE q.user_id IS NOT NULL AND u.user_id IS NULL",
            dry_run,
        )
        ensure_fk_if_clean(
            conn,
            cursor,
            "fk_quiz_question_answer_attempt",
            "quiz_question_answer",
            "attempt_id",
            "quiz_attempt",
            "id",
            "SELECT COUNT(*) FROM quiz_question_answer qa LEFT JOIN quiz_attempt q ON qa.attempt_id = q.id WHERE qa.attempt_id IS NOT NULL AND q.id IS NULL",
            dry_run,
        )
        ensure_fk_if_clean(
            conn,
            cursor,
            "fk_quiz_question_answer_user",
            "quiz_question_answer",
            "user_id",
            "users",
            "user_id",
            "SELECT COUNT(*) FROM quiz_question_answer qa LEFT JOIN users u ON qa.user_id = u.user_id WHERE qa.user_id IS NOT NULL AND u.user_id IS NULL",
            dry_run,
        )

        if drop_legacy_tables:
            drop_legacy_old_tables(conn, cursor, dry_run)
        else:
            print("SKIP: legacy *_old table cleanup")

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
    parser.add_argument(
        "--migrate-password-hash",
        action="store_true",
        help="Opt in to migrating users.password values from encrypted/plain text to pbkdf2 hashes.",
    )
    parser.add_argument(
        "--drop-legacy-old-tables",
        action="store_true",
        help="Drop dbo tables whose names end with _old after the architecture migration finishes.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_migration(
        dry_run=args.dry_run,
        migrate_password_hash=args.migrate_password_hash,
        drop_legacy_tables=args.drop_legacy_old_tables,
    )
