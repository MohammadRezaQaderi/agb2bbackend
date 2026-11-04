"""Safely restore a fresh copy of AGB2B into AGB2B_COPY.

The script never overwrites an existing target unless --replace-existing is
explicitly supplied. SQL Server must be able to write backup and data files in
the source database's data directory.

Usage:
    python helper/db/copy_agb2b.py --dry-run
    python helper/db/copy_agb2b.py
    python helper/db/copy_agb2b.py --replace-existing
"""
from __future__ import annotations

import argparse
import ntpath
import os
import posixpath
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import DB_CONN_STRING


def quote_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", value):
        raise ValueError("Database name contains unsupported characters")
    return f"[{value}]"


def quote_literal(value: str) -> str:
    return "N'" + value.replace("'", "''") + "'"


def master_connection_string(connection_string: str) -> str:
    parts = [part for part in connection_string.split(";") if part.strip()]
    parts = [part for part in parts if not part.lstrip().upper().startswith("DATABASE=")]
    parts.append("DATABASE=master")
    return ";".join(parts)


def server_path_module(path: str):
    return ntpath if re.match(r"^[A-Za-z]:[\\/]", path) or "\\" in path else posixpath


def server_path_dirname(path: str) -> str:
    return server_path_module(path).dirname(path)


def server_path_join(directory: str, filename: str) -> str:
    return server_path_module(directory).join(directory, filename)


def resolve_backup_directory(cursor, source_data_directory: str, explicit_directory: str | None = None) -> str:
    configured_directory = explicit_directory or os.getenv("AG_DB_BACKUP_DIRECTORY")
    if configured_directory:
        return configured_directory.rstrip("\\/")

    cursor.execute("SELECT CONVERT(NVARCHAR(4000), SERVERPROPERTY('InstanceDefaultBackupPath'))")
    row = cursor.fetchone()
    default_directory = row[0] if row and row[0] else None
    return str(default_directory or source_data_directory).rstrip("\\/")


def copy_database(
    dry_run: bool = False,
    replace_existing: bool = False,
    backup_directory: str | None = None,
) -> None:
    source = os.getenv("AG_DB_SOURCE_DATABASE", "AGB2B")
    target = os.getenv("AG_DB_COPY_DATABASE", "AGB2B_COPY")
    source_ref = quote_identifier(source)
    target_ref = quote_identifier(target)
    if source.casefold() == target.casefold():
        raise ValueError("Source and target databases must be different")
    if target.casefold() != f"{source}_COPY".casefold():
        raise ValueError("Target must be named '<source>_COPY' for safety")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = None
    try:
        import pyodbc
    except ModuleNotFoundError as exc:
        raise RuntimeError("pyodbc is required to copy SQL Server databases") from exc

    connection = pyodbc.connect(master_connection_string(DB_CONN_STRING), autocommit=True)
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT DB_ID(?)", source)
        if cursor.fetchone()[0] is None:
            raise RuntimeError(f"Source database '{source}' does not exist")

        cursor.execute(
            "SELECT [name], [physical_name], [type_desc] FROM sys.master_files "
            "WHERE [database_id] = DB_ID(?) ORDER BY [file_id]",
            source,
        )
        source_files = cursor.fetchall()
        if not source_files:
            raise RuntimeError("Could not find source database files")

        source_primary_path = next((row.physical_name for row in source_files if row.type_desc == "ROWS"), None)
        if not source_primary_path:
            raise RuntimeError("Could not find the source database data file")
        data_directory = server_path_dirname(source_primary_path)
        backup_directory = resolve_backup_directory(cursor, data_directory, backup_directory)
        backup_file = server_path_join(backup_directory, f"{target}_{timestamp}.bak")

        cursor.execute("SELECT DB_ID(?)", target)
        target_exists = cursor.fetchone()[0] is not None
        if target_exists and not replace_existing:
            raise RuntimeError(
                f"Target '{target}' already exists. Use --replace-existing only after confirming it can be replaced."
            )

        file_list = []
        first_rows_file = next(index for index, row in enumerate(source_files) if row.type_desc == "ROWS")
        for index, row in enumerate(source_files):
            logical_name = row.name
            extension = ".ldf" if row.type_desc == "LOG" else (".mdf" if index == first_rows_file else ".ndf")
            safe_base = re.sub(r"[^A-Za-z0-9_-]", "_", logical_name)
            target_path = server_path_join(data_directory, f"{target}_{timestamp}_{safe_base}{extension}")
            file_list.append((logical_name, target_path))

        plan = [
            f"Backup [{source}] to {backup_file}",
            f"Verify backup checksum",
            f"Restore as [{target}] with files: " + ", ".join(path for _, path in file_list),
        ]
        if target_exists:
            plan.insert(0, f"Replace existing target [{target}]")
        if dry_run:
            print("\n".join(f"DRY RUN: {step}" for step in plan))
            return

        backup_sql = (
            f"BACKUP DATABASE {source_ref} TO DISK = {quote_literal(backup_file)} "
            "WITH COPY_ONLY, INIT, COMPRESSION, CHECKSUM, STATS = 10"
        )
        try:
            cursor.execute(backup_sql)
        except pyodbc.Error as exc:
            raise RuntimeError(
                f"SQL Server could not write backup file '{backup_file}'. "
                "The directory must exist on the SQL Server host and its service account must have write access. "
                "Set --backup-directory or AG_DB_BACKUP_DIRECTORY to a valid server-side backup directory."
            ) from exc
        cursor.execute(f"RESTORE VERIFYONLY FROM DISK = {quote_literal(backup_file)} WITH CHECKSUM")

        if target_exists:
            cursor.execute(f"ALTER DATABASE {target_ref} SET SINGLE_USER WITH ROLLBACK IMMEDIATE")
            cursor.execute(f"DROP DATABASE {target_ref}")

        cursor.execute(f"RESTORE FILELISTONLY FROM DISK = {quote_literal(backup_file)}")
        backup_files = cursor.fetchall()
        moves = []
        for item in backup_files:
            matching_path = next((path for logical, path in file_list if logical == item.LogicalName), None)
            if matching_path is None:
                raise RuntimeError(f"Missing restore path for logical file '{item.LogicalName}'")
            moves.append(f"MOVE {quote_literal(item.LogicalName)} TO {quote_literal(matching_path)}")

        cursor.execute(
            f"RESTORE DATABASE {target_ref} FROM DISK = {quote_literal(backup_file)} "
            f"WITH {', '.join(moves)}, RECOVERY, CHECKSUM, STATS = 10"
        )
        cursor.execute(f"ALTER DATABASE {target_ref} SET MULTI_USER")
        cursor.execute("SELECT [name], [state_desc], [user_access_desc] FROM sys.databases WHERE [name] = ?", target)
        restored = cursor.fetchone()
        if restored is None or restored.state_desc != "ONLINE" or restored.user_access_desc != "MULTI_USER":
            raise RuntimeError("Restored database did not reach ONLINE / MULTI_USER state")
        print(f"Copied [{source}] to [{target}] successfully.")
        print(f"Verified backup: {backup_file}")
    finally:
        cursor.close()
        connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a safe SQL Server copy of AGB2B.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned actions without creating a backup.")
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Drop and replace the existing *_COPY target database.",
    )
    parser.add_argument(
        "--backup-directory",
        help="Existing directory on the SQL Server host used for the temporary backup file.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    copy_database(
        dry_run=args.dry_run,
        replace_existing=args.replace_existing,
        backup_directory=args.backup_directory,
    )
