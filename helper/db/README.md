# Database Schema Workflow

`db_creator.py` defines the target schema for a new, empty database. Runtime
SQLAlchemy models map to that schema; they do not create or migrate tables.

For a copy of an existing AGB2B database:

1. Run `copy_db.sql` in SQL Server to create a fresh `AGB2B_COPY` from a backup.
   Its restore paths and logical file names must match the server.
2. Set `AG_DB_DATABASE=AGB2B_COPY` and the other `AG_DB_*` connection variables
   for the shell running Python. Check this setting before every migration;
   the scripts use the configured database, which defaults to `AGB2B_COPY`.
3. Run `python helper/db/architecture_migration.py --dry-run`, review its
   output, then run `python helper/db/architecture_migration.py`. This is the
   one-time conversion of a legacy copy. It also adds `ocon.logo` when absent.
   Do not use `--migrate-password-hash` with the current reversible-password
   application flow. `--drop-legacy-old-tables` is an explicit data deletion
   option and is not part of the normal upgrade.
4. Run `python helper/db/live_migration.py --dry-run`, then
   `python helper/db/live_migration.py` for incremental changes. Applied steps
   are recorded in `dbo.schema_migrations`.

For a new empty database, use `python helper/db/db_creator.py`. It creates
missing tables only; it does not upgrade existing tables. Future schema changes
should update this target schema and add an idempotent step to
`live_migration.py`. Existing databases must not be upgraded by rerunning
`db_creator.py` alone.

`migration.py` is a historical rebuild script that drops current tables and
depends on `*_old` tables. Direct execution is disabled. `last_schema.py` is
not present in this repository. `migrate_quiz_answers.py` is a separate data
backfill, not the schema workflow.

Dynamic SQL identifiers in the active migration scripts are selected by code
or read from SQL Server metadata and quoted before use. Runtime requests use
SQLAlchemy expressions with bound values. The legacy `migration.py` remains
for reference only.
