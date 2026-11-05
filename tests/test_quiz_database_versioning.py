from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import helper.db.architecture_migration as architecture_migration
from helper.db.sqlalchemy.models import QuizAttempt, Setting
from helper.db.sqlalchemy.queries.quiz import save_attempt
from helper.db.sqlalchemy.queries.settings import get_setting_for_user_quiz, upsert_setting


def test_settings_are_isolated_by_package_name():
    engine = create_engine("sqlite://")
    Setting.__table__.create(engine)

    with Session(engine) as session:
        upsert_setting(session, "no setting", 7, "AG", "AG description", None, 1)
        upsert_setting(session, "no setting", 7, "SCL", "SCL description", None, 1)

        ag_setting = get_setting_for_user_quiz(session, 7, "AG", 1)
        scl_setting = get_setting_for_user_quiz(session, 7, "SCL", 1)

    assert ag_setting["description"] == "AG description"
    assert ag_setting["package_name"] == "AG"
    assert scl_setting["description"] == "SCL description"
    assert scl_setting["package_name"] == "SCL"


def test_existing_attempt_keeps_its_original_versions():
    engine = create_engine("sqlite://")
    QuizAttempt.__table__.create(engine)

    with Session(engine) as session:
        created = save_attempt(
            session=session,
            user_id=10,
            quiz_kind="AG",
            quiz_id=1,
            definition_version="legacy-v1",
            scoring_version="legacy-v1",
            state=1,
            owner_user_id=20,
            consultant_user_id=30,
        )
        updated = save_attempt(
            session=session,
            user_id=10,
            quiz_kind="AG",
            quiz_id=1,
            definition_version="future-v2",
            scoring_version="future-v2",
            state=2,
            owner_user_id=20,
            consultant_user_id=30,
        )

    assert created["definition_version"] == "legacy-v1"
    assert created["scoring_version"] == "legacy-v1"
    assert updated["definition_version"] == "legacy-v1"
    assert updated["scoring_version"] == "legacy-v1"
    assert updated["state"] == 2


def test_migration_plans_package_and_version_backfills(monkeypatch):
    added_columns = []
    sql_operations = []
    indexes = []

    monkeypatch.setattr(architecture_migration, "table_exists", lambda cursor, table: True)
    monkeypatch.setattr(architecture_migration, "column_exists", lambda cursor, table, column: False)
    monkeypatch.setattr(
        architecture_migration,
        "ensure_column",
        lambda conn, cursor, table, column, definition, dry_run: added_columns.append(
            (table, column, definition, dry_run)
        ),
    )
    monkeypatch.setattr(
        architecture_migration,
        "run_sql",
        lambda conn, cursor, sql, dry_run, label: sql_operations.append((label, sql, dry_run)),
    )
    monkeypatch.setattr(
        architecture_migration,
        "ensure_index_if_clean",
        lambda conn, cursor, table, index, columns, duplicate_sql, dry_run: indexes.append(
            (table, index, columns, duplicate_sql, dry_run)
        ),
    )

    architecture_migration.ensure_quiz_package_versioning(object(), object(), dry_run=True)

    assert ("setting", "package_name", "VARCHAR(25) NULL", True) in added_columns
    assert ("quiz_attempt", "definition_version", "VARCHAR(50) NULL", True) in added_columns
    assert ("quiz_attempt", "scoring_version", "VARCHAR(50) NULL", True) in added_columns
    assert [operation[0] for operation in sql_operations] == [
        "backfill setting.package_name as AG",
        "backfill quiz_attempt.definition_version",
        "backfill quiz_attempt.scoring_version",
    ]
    assert "package_name = 'AG'" in sql_operations[0][1]
    assert indexes[0][1] == "ux_setting_user_package_quiz"
    assert indexes[0][2] == "user_id, package_name, quiz_id"
