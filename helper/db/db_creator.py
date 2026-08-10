"""
Helpers for creating and dropping SQL Server tables that power the KS backend.

Usage:
    python helper/db/db_creator.py
"""
from __future__ import annotations
import os
import sys
from typing import Iterable, Sequence
import pyodbc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import DB_TRUST_CERT, DB_PWD, DB_UID, DB_SERVER, DB_DATABASE, DB_DRIVER

TABLE_DEFINITIONS = {
    "users": """
        CREATE TABLE users (
            user_id INT IDENTITY(1, 1) PRIMARY KEY,
            phone NVARCHAR(12),
            password NVARCHAR(255),
            role NVARCHAR(100) NULL,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "ins": """
        CREATE TABLE ins (
            ins_id INT IDENTITY(1, 1),
            user_id INT PRIMARY KEY,
            phone NVARCHAR(12),
            name NVARCHAR(100),
            logo VARCHAR(MAX),
            password NVARCHAR(255),
            verify INT DEFAULT 0,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "sch": """
        CREATE TABLE sch (
            sch_id INT IDENTITY(1, 1),
            user_id INT PRIMARY KEY,
            phone NVARCHAR(12),
            name NVARCHAR(100),
            logo VARCHAR(MAX),
            password NVARCHAR(255),
            verify INT DEFAULT 0,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "wCon": """
        CREATE TABLE wCon (
            wCon_id INT IDENTITY(1, 1),
            user_id INT PRIMARY KEY,
            phone NVARCHAR(12),
            first_name NVARCHAR(50),
            last_name NVARCHAR(50),
            logo VARCHAR(MAX),
            password NVARCHAR(255),
            sex INT DEFAULT 1,
            verify INT DEFAULT 0,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "con": """
        CREATE TABLE con (
            con_id INT IDENTITY(1, 1),
            user_id INT PRIMARY KEY,
            phone NVARCHAR(12),
            first_name NVARCHAR(50),
            last_name NVARCHAR(50),
            sex INT DEFAULT 1,
            ins_id INT,
            editor_id INT,
            password NVARCHAR(255),
            ins_role NVARCHAR(15),
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "stu": """
        CREATE TABLE stu (
            stu_id INT IDENTITY(1, 1),
            user_id INT PRIMARY KEY,
            phone NVARCHAR(12),
            first_name NVARCHAR(50),
            last_name NVARCHAR(50),
            sex INT,
            city NVARCHAR(100),
            access VARCHAR(MAX) DEFAULT '{}',
            password NVARCHAR(255),
            comment NVARCHAR(MAX),
            birth_date NVARCHAR(4),
            ins_role NVARCHAR(15),
            ins_id INT,
            con_id INT,
            adder_id INT,
            editor_id INT,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "setting": """
        CREATE TABLE setting (
            setting_id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            description NVARCHAR(MAX),
            voice NVARCHAR(MAX),
            quiz_id INT,
            editor_id INT,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "capacity": """
        CREATE TABLE capacity (
            capacity_id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            phone NVARCHAR(12),
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "capacity_package": """
        CREATE TABLE capacity_package (
            capacity_package_id INT IDENTITY(1, 1) PRIMARY KEY,
            capacity_id INT FOREIGN KEY REFERENCES capacity(capacity_id),
            package_name NVARCHAR(50),
            user_id INT,
            phone NVARCHAR(12),
            allowed INT DEFAULT 0,
            used INT DEFAULT 0,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "quiz_answer": """
        CREATE TABLE quiz_answer (
            quiz_answer_id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            quiz_id INT,
            quiz_kind VARCHAR(25), 
            answers NVARCHAR(MAX),
            state INT,
            ins_id INT,
            con_id INT,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "scores": """
        CREATE TABLE scores (
            scores_id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            phone NVARCHAR(12),
            quiz_score NVARCHAR(MAX),
            brain_fields NVARCHAR(MAX),
            brain_categories NVARCHAR(MAX),
            brain_branches NVARCHAR(MAX),
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "scl_scores": """
        CREATE TABLE scl_scores (
            scores_id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            phone NVARCHAR(12),
            scl_date NVARCHAR(MAX),
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "result_state": """
        CREATE TABLE result_state (
            result_state_id INT IDENTITY(1, 1),
            user_id INT PRIMARY KEY,
            phone NVARCHAR(12),
            t_state NVARCHAR(100),
            r_state NVARCHAR(100),
            e_state NVARCHAR(100),
            a_state NVARCHAR(100),
            m_state NVARCHAR(100),
            f_state NVARCHAR(100),
            i_state NVARCHAR(100),
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "hedayat_fields": """
        CREATE TABLE hedayat_fields (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            phone NVARCHAR(12),
            suggested NVARCHAR(MAX),
            other NVARCHAR(MAX),
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "notifications": """
        CREATE TABLE notifications (
            id INT IDENTITY(1, 1) NOT NULL PRIMARY KEY,
            roles NCHAR(100),
            user_id INT,
            title NVARCHAR(MAX),
            description NVARCHAR(MAX),
            added_by NVARCHAR(MAX),         
            priority NCHAR(100),   
            persian_date NVARCHAR(50),
            fullText NVARCHAR(MAX),      
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE(),
        )
    """,
    "payment": """
        CREATE TABLE payment (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            payment_id INT NOT NULL,
            user_id INT NOT NULL,
            phone NVARCHAR(12) NOT NULL,
            state NVARCHAR(100),
            status NVARCHAR(100),
            price INT,
            discount_price INT,
            track_id NVARCHAR(100),
            discount_id INT DEFAULT NULL,
            result NVARCHAR(100) NULL,
            saleReferenceId NVARCHAR(50) NULL,
            message TEXT,
            token NVARCHAR(MAX),
            product_data NVARCHAR(MAX),
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "payment_log": """
        CREATE TABLE payment_log (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            payment_id INT NOT NULL,
            user_id INT NOT NULL,
            phone NVARCHAR(12) NOT NULL,
            state NVARCHAR(100),
            status NVARCHAR(100),
            price INT,
            discount_price INT,
            track_id NVARCHAR(100),
            result NVARCHAR(100) NULL,
            discount_id INT DEFAULT NULL,
            saleReferenceId NVARCHAR(50) NULL,
            message TEXT,
            token NVARCHAR(MAX),
            product_data NVARCHAR(MAX),
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "discount": """
        CREATE TABLE discount (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            code VARCHAR(10),
            status NVARCHAR(100),
            discount_percentage FLOAT,
            used INT DEFAULT 0,
            count INT DEFAULT 100,
            used_apply INT DEFAULT 0,
            count_apply INT DEFAULT 0,
            expire_time DATETIME DEFAULT NULL,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "using_discount": """
        CREATE TABLE using_discount (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            code VARCHAR(10),
            status NVARCHAR(100),
            user_id INT NOT NULL,
            phone NVARCHAR(12) NOT NULL,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "tokens": """
        CREATE TABLE tokens (
            token_id INT IDENTITY(1, 1) PRIMARY KEY,
            token VARCHAR(MAX),
            user_id INT UNIQUE,
            phone NVARCHAR(12),
            role NVARCHAR(100) NULL,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "comments": """
        CREATE TABLE comments (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            name NVARCHAR(400),      
            comment NVARCHAR(MAX),
            rating FLOAT DEFAULT 5.0,
            persian_date NVARCHAR(MAX),
            user_id INT NOT NULL,
            phone NVARCHAR(12) NOT NULL,
            role NVARCHAR(100) NULL,
            db_name NVARCHAR(400) NOT NULL,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE(),
        )
    """,
    "otp_logs": """
    CREATE TABLE otp_logs (
            id INT IDENTITY(1, 1) NOT NULL PRIMARY KEY,
            phone VARCHAR(12),
            code VARCHAR(10),
            type_otp VARCHAR(10),
            provider_resp NVARCHAR(MAX),
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE(),
        )
    """,
    "redis_log": """
        CREATE TABLE redis_log (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            kind NVARCHAR(20),
            result VARCHAR(MAX),
            status INT DEFAULT 0,
            phone NVARCHAR(12),
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "error_log": """
        CREATE TABLE error_log (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            q_id INT,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "api_logs": """
        CREATE TABLE api_logs (
            id INT IDENTITY(1, 1) NOT NULL PRIMARY KEY,
            user_id INT,
            phone NVARCHAR(12),
            end_point NCHAR(100),
            func_name NCHAR(100),
            data NVARCHAR(MAX),         
            error_p NVARCHAR(MAX),         
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE(),
        )
    """,
    "capacity_logs": """
        CREATE TABLE capacity_logs (
            id INT IDENTITY(1, 1) NOT NULL PRIMARY KEY,
            user_id INT,
            capacity_id INT,
            capacity_package_id INT,
            package_name NVARCHAR(50),
            allowed INT DEFAULT 0,
            used INT DEFAULT 0,
            change INT DEFAULT 0,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE(),
        )
    """,
}

DEFAULT_TABLES: Sequence[str] = (
    'users', 'ins', 'sch', 'wCon', 'con', 'stu', 'setting', 'capacity', 'capacity_package', 'capacity_logs',
    'quiz_answer', 'scores', 'scl_scores', 'result_state', 'hedayat_fields', 'notifications', 'payment',
    'payment_log', 'discount', 'using_discount', 'tokens', 'comments', 'otp_logs', 'redis_log', 'error_log',
    'api_logs'
)


def _table_exists(cursor: pyodbc.Cursor, table: str) -> bool:
    """Return True if the table already exists in the database."""
    return cursor.tables(table=table, tableType="TABLE").fetchone() is not None


def create_tables(conn: pyodbc.Connection, cursor: pyodbc.Cursor, tables: Iterable[str]) -> None:
    """Create the requested tables if they are missing."""
    for table in tables:
        ddl = TABLE_DEFINITIONS.get(table)
        if ddl is None:
            print(f"[WARN] No definition for '{table}', skipping.")
            continue
        if _table_exists(cursor, table):
            print(f"[SKIP] '{table}' already exists.")
            continue
        cursor.execute(ddl)
        conn.commit()
        print(f"[OK] '{table}' table created.")


def drop_tables(conn: pyodbc.Connection, cursor: pyodbc.Cursor, tables: Iterable[str]) -> None:
    """Drop the requested tables if they exist."""
    for table in tables:
        if not _table_exists(cursor, table):
            print(f"[SKIP] '{table}' does not exist.")
            continue
        try:
            cursor.execute(f"DROP TABLE {table}")
            conn.commit()
            print(f"[OK] '{table}' dropped.")
        except pyodbc.Error as exc:
            print(f"[ERR] Could not drop '{table}': {exc}")


def build_connection() -> pyodbc.Connection:
    """Create a SQL Server connection based on environment variables."""
    return pyodbc.connect(
        driver=DB_DRIVER,
        host=DB_SERVER,
        database=DB_DATABASE,
        UID=DB_UID,
        PWD=DB_PWD,
        TrustServerCertificate=DB_TRUST_CERT,
    )


def main() -> None:
    conn = build_connection()
    cursor = conn.cursor()
    drop_tables(conn, cursor,
                [])
    create_tables(conn, cursor, ["capacity_logs"])

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
