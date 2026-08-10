"""
Database helper utilities for Report scripts.

Provides synchronous database connection functions for use in standalone scripts.
"""
import os
import pyodbc
from typing import Tuple, Optional

from config import DB_DRIVER, DB_SERVER, DB_DATABASE, DB_UID, DB_PWD, DB_TRUST_CERT


def _get_db_config() -> dict:
    """Return DB connection kwargs, sourcing overrides from environment variables."""
    return {
        "driver": DB_DRIVER,
        "host": DB_SERVER,
        "database": DB_DATABASE,
        "UID": DB_UID,
        "PWD": DB_PWD,
        "TrustServerCertificate": DB_TRUST_CERT,
    }


def get_db_connection() -> Tuple[pyodbc.Connection, pyodbc.Cursor]:
    """
    Establish and return a synchronous SQL Server connection and cursor.

    Returns:
        Tuple of (connection, cursor) for database operations.

    Raises:
        pyodbc.Error: If connection fails.
    """
    config = _get_db_config()
    conn = pyodbc.connect(**config)
    return conn, conn.cursor()


def close_db_connection(conn: Optional[pyodbc.Connection], cursor: Optional[pyodbc.Cursor]) -> None:
    """
    Safely close the SQL Server connection and cursor.

    Args:
        conn: Database connection to close.
        cursor: Database cursor to close.
    """
    try:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    except pyodbc.Error as e:
        print(f"[DB] Error closing connection: {e}")


if __name__ == "__main__":
    """Test database connection."""
    print("Testing database connection...")
    try:
        conn, cursor = get_db_connection()
        print("✓ Database connection successful!")
        close_db_connection(conn, cursor)
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
