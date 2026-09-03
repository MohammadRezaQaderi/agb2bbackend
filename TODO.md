# AGUserBackend Cleanup TODO

Generated: 2026-08-10

This list is based on a quick pass over the current repository. The goal is to
clean the project before adding new features, while keeping production behavior
stable.

## P0 - Security And Production Safety

- [x] Remove real secret fallbacks from `config.py`.
  - Secret defaults for `AG_KAVENEGAR_API_KEY`, `AG_PASSWORD_SECRET_KEY`,
    `AG_DB_UID`, and `AG_DB_PWD` were removed.
  - `.env.example` now documents the required runtime values.
  - Production fails fast when required env vars are missing.
- [ ] Rotate any credentials that have already been committed or shared.
- [x] Rework `DEVELOP_TOKEN` usage in `/ag_api/admin_request`.
  - The admin endpoint currently trusts one static token from config.
  - Replace with a real admin auth path or a scoped internal service token.
  - Admin auth now checks `admins.token_hash` and stores admin audit events in
    `admin_logs`.
  - Admin tokens are created/rotated with `helper/db/create_admin.py`; there is
    no config-token bootstrap path left in runtime.
- [ ] Review password storage behavior.
  - Passwords are decryptable via Fernet and some APIs return decrypted
    passwords in responses/reports.
  - Decide whether the product really needs reversible passwords; otherwise
    migrate to one-way hashing.
- [x] Redact sensitive request fields before writing service error logs.
  - `password`, `re_password`, OTP/security codes, and tokens are masked before
    storing `api_logs.data`.
- [x] Harden file upload endpoints in `main.py`.
  - Validate file extension and content type.
  - Avoid `filename.split(".")[1]`; use `pathlib.Path(...).suffix`.
  - Enforce file size limits.
  - Prevent deleting arbitrary previous files via `last_pic` / `last_voice`.
  - Static file responses now resolve paths inside their configured storage
    directory before serving.

## P1 - Project Structure And Maintainability

- [ ] Split `main.py` into FastAPI routers.
  - `main.py` is currently about 1350 lines and mixes metrics, auth dispatch,
    uploads, static file serving, and report download logic.
  - Suggested routers: `auth`, `actions`, `admin`, `files`, `reports`,
    `health`.
  - `routers/health.py`, `routers/static_data.py`, and `routers/files.py`
    have been extracted.
  - `routers/actions.py` and `routers/uploads.py` have been extracted.
  - `routers/action_helpers.py` now centralizes action payload parsing,
    auth dispatch, Redis pre-auth dispatch, and endpoint exception logging.
  - Report downloads remain in `main.py` intentionally until report cleanup is
    resumed.
- [x] Replace `from services.service import *` with explicit imports.
  - This makes endpoint dependencies searchable and safer during refactors.
- [ ] Extract duplicate report-download logic.
  - `get_ag_first_pdf`, `get_ag_second_pdf`, and SCL report endpoints repeat
    permission checks, quiz completion checks, queue checks, and file lookup.
  - Create one helper/service such as `get_student_report_file(kind,
    report_number, expected_quiz_count)`.
- [ ] Standardize API response shapes and HTTP status usage.
  - Some business errors return HTTP 200 with `status` in JSON.
  - Other paths use custom HTTP status codes like `321`-`324`.
  - Define one response contract before adding new features.
- [ ] Move business constants out of `helper/func_helper.py`.
  - `PROVINCES`, `PACKAGES_DATA`, quiz titles, password helpers, DB helpers,
    and validation helpers are all in one large file.
  - Suggested modules: `constants.py`, `security.py`, `validators.py`,
    `connections.py`.

## P1 - Database And Transactions

- [ ] Resolve duplicate database rows after architecture migration.
  - `users.phone` still has duplicates, including same-role duplicates
    (`ins+ins`, `ocon+ocon`, `sch+sch`) and cross-role duplicates
    (`ins+con`, `ins+sch`).
  - Decide whether one phone can own multiple roles. If yes, change the auth
    model before adding a unique index on `users.phone`; if no, merge users and
    move dependent rows intentionally.
  - Known orphan duplicate users from `AGB2B_COPY`: `1685`, `3897`, `3898`,
    `3899`; verify again before deleting in production data.
  - `capacity` has duplicate `user_id` rows for `1684` and `3896`.
    `capacity_package` has duplicate `(user_id, package_name)` rows for
    `(1684, AG)`, `(1684, SCL)`, `(3896, AG)`, and `(3896, SCL)`.
  - After cleanup, rerun the architecture migration so `ux_users_phone`,
    `ux_capacity_user_id`, and `ux_capacity_package_user_package` can be
    created when data is clean.
- [x] Remove legacy runtime `helper/db/db_helper.py`.
  - Runtime database access now goes through the SQLAlchemy layer.
  - Low-level pyodbc usage remains only in schema/migration/report scripts.
- [x] Centralize transaction handling.
  - Runtime writes use SQLAlchemy `session_scope()` so related inserts/updates
    commit or rollback together.
  - Manual `commit()` / `rollback()` remains only in migration/schema/report
    scripts.
  - Account/student creation avoids mutating request payloads with generated
    credentials during DB transactions.
- [ ] Review dynamic SQL helper inputs.
  - Values are parameterized, but table names, field names, and conditions are
    built with f-strings.
  - Keep these helpers internal or add allowlists for table/column names.
- [ ] Decide where schema management lives.
  - `helper/db/db_creator.py`, `helper/db/migration.py`, and
    `helper/db/last_schema.py`
    overlap.
  - Pick a migration workflow and mark old schema helpers as legacy if needed.

## P2 - Tooling, Tests, And CI

- [ ] Add a minimal test setup.
  - Add `pytest`, `pytest-asyncio`, and FastAPI `TestClient` tests for
    request validation, auth failures, health endpoint behavior, and report
    permission checks.
  - Mock DB/Redis/Kavenegar so tests run without production services.
- [ ] Add formatting/linting.
  - Suggested baseline: `ruff` for linting/import sorting and `black` or
    `ruff format` for formatting.
  - Add a simple `pyproject.toml` so the team runs the same checks.
- [ ] Pin all dependencies in `requirements.txt`.
  - `pandas`, `openpyxl`, `prometheus_client`, `httpx`, and `cryptography` are
    currently unpinned.
- [ ] Add a lightweight CI command.
  - Example stages: install dependencies, run lint, run tests, import-check the
    app.
- [x] Add `.env.example` and update deployment docs to use the same env names
  as `config.py`.
  - Deployment docs now point to `.env.example` and use `AG_DB_*` names.

## P2 - Logging And Observability

- [x] Replace `print()` in application paths with structured logging.
  - Keep CLI/report scripts user-friendly, but app code should use Python
    logging with request context/tracking code.
  - Runtime services/helpers now use module loggers; remaining prints are in
    CLI, migration, report, or office-generation paths.
- [x] Review Prometheus label cardinality.
  - HTTP metrics label raw request paths; dynamic paths with phone numbers or
    filenames can create high-cardinality metrics.
  - Prefer route templates where possible.
  - Middleware now uses FastAPI route templates and a fixed unmatched-route
    label instead of raw unknown paths.
- [x] Improve `/ag_api/health`.
  - Separate liveness from readiness.
  - Add optional Redis check.
  - `/health` remains readiness-compatible for deployment, `/ready` mirrors it,
    and `/live` returns process liveness without DB/Redis dependencies.
  - Redis readiness is enabled only when `AG_HEALTH_CHECK_REDIS=1`.
  - Avoid exposing detailed DB errors to public callers.

## P2 - Repository Hygiene

- [ ] Ignore generated report outputs.
  - `report/outputs/` is currently untracked output and should probably be
    ignored unless sample fixtures are intentional.
- [ ] Clean local artifacts before committing.
  - `__pycache__/` and `venv/` are ignored, but local copies exist in the
    workspace.
  - Do not delete them during feature work unless the team wants a cleanup
    commit.
- [ ] Decide whether deployment scripts are Windows-only.
  - Current deployment docs and `.bat` scripts are PM2/Windows focused, while
    Docker files suggest a container path.
  - Document the supported production path clearly.
- [ ] Review Postman files for secrets or stale environments.

## P3 - Feature Readiness

- [ ] Document the current method-type action contract.
  - Endpoints dispatch behavior through `method_type`; new features should not
    add more hidden actions without documentation.
- [ ] Add request/response models for new features.
  - Introduce Pydantic models gradually around new endpoints first, then
    backfill older action handlers.
- [ ] Create a small service boundary for external integrations.
  - SMS, Redis OTP cache, report files, and payment helpers should be behind
    interfaces that are easy to mock.
- [ ] Add migration notes for any future auth/password changes.
  - Password encryption and token tables are sensitive; write rollback and data
    migration notes before changing production data.

## Suggested First Cleanup PRs

1. Security config PR:
   remove secret defaults, add `.env.example`, align deployment docs, rotate
   credentials.
2. Tooling PR:
   add `pyproject.toml`, `ruff`, pinned dependencies, and one import-check test.
3. Router extraction PR:
   move health/metrics/admin/auth endpoints out of `main.py` without changing
   behavior.
4. Report-download cleanup PR:
   extract duplicated AG/SCL report logic and add mocked tests for permissions
   and file states.
