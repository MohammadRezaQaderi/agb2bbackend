# SQLAlchemy Layer

This package is the gradual replacement path for ad-hoc SQL strings and the
legacy `helper.db.db_helper` functions.

## Layout

- `engine.py`: SQL Server engine built from the existing `config.DB_CONN_STRING`.
- `session.py`: `create_session()`, `SessionLocal`, and `session_scope()`
  transaction helper.
- `base.py`: declarative base and shared mixins.
- `models.py`: ORM models mapped to the current table names.
- `filters.py`: small immutable filter objects built from request data.
- `pagination.py`: shared pagination helpers for mapping-style query results.
- `queries/`: composable query builders and read functions.

## Migration Rules

- Keep table names unchanged while schema cleanup is still settling.
- Move read-heavy endpoints first: lists, dashboards, reports, admin lookups.
- Keep business logic in services; query modules should only build/fetch data.
- Move write paths only after transaction ownership is centralized.
- Do not delete the legacy pyodbc helpers until all callers are migrated.
