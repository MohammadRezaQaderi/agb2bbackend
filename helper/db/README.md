# Database Schema Workflow

`db_creator.py` defines the target schema for a new, empty database. Runtime
SQLAlchemy models map to that schema; they do not create or migrate tables.

For a copy of an existing AGB2B database:

1. Prefer `python helper/db/copy_agb2b.py --dry-run`, inspect the plan, then run
   `python helper/db/copy_agb2b.py` to create `AGB2B_COPY`. The script makes a
   checksummed copy-only backup, verifies it, and refuses to overwrite an
   existing target unless `--replace-existing` is explicitly supplied. SQL
   Server must be able to write to the source data directory. `copy_db.sql` is
   the older manual alternative and contains a destructive target replacement.
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

The student education migration assigns existing students with Persian birth
year `1390` or earlier to the second period, and later birth years to the first
period. Override the cutoff before running the migration with
`AG_STUDENT_SECOND_PERIOD_MAX_BIRTH_YEAR` if the school-year boundary differs.
Existing `education_field` values remain NULL because birth year does not
identify a student's رشته; the edit form asks for it when a second-period
student is next updated.

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
