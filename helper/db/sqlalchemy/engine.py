from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from config import DB_CONN_STRING


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create the shared SQLAlchemy engine for SQL Server."""
    connection_url = f"mssql+pyodbc:///?odbc_connect={quote_plus(DB_CONN_STRING)}"
    return create_engine(
        connection_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        future=True,
    )
