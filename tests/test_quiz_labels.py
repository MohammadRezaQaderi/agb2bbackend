import json
from contextlib import nullcontext
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from helper.db.sqlalchemy.base import Base
from helper.db.sqlalchemy.models import QuizLabel, User
from helper.db.sqlalchemy.queries.quiz_labels import (
    get_quiz_labels,
    list_quiz_labels_for_user,
    upsert_quiz_labels,
)
import scheduler.scheduler as scheduler_module


def _create_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add(User(user_id=10, phone="09120000000", password="x", role="stu"))
    session.commit()
    return session


def test_quiz_labels_are_stored_as_unicode_json_and_read_back():
    with _create_session() as session:
        stored = upsert_quiz_labels(
            session=session,
            user_id=10,
            quiz_kind="scl",
            labels={"اضطراب": 2.5, "OCD": {"ocd1": 4}},
            metadata={"missing_questions": [4, 8]},
            definition_version="legacy-v1",
            scoring_version="legacy-v1",
        )
        raw_json = session.get(QuizLabel, stored["id"]).labels_json
        loaded = get_quiz_labels(session=session, user_id=10, quiz_kind="SCL")

    assert "اضطراب" in raw_json
    assert json.loads(raw_json)["OCD"]["ocd1"] == 4
    assert loaded["labels"]["اضطراب"] == 2.5
    assert loaded["metadata"] == {"missing_questions": [4, 8]}


def test_quiz_label_upsert_keeps_one_current_row_per_user_and_kind():
    with _create_session() as session:
        created = upsert_quiz_labels(
            session=session,
            user_id=10,
            quiz_kind="AG",
            labels={"Realistic": 1},
            metadata={"correct": 1},
            definition_version="legacy-v1",
            scoring_version="legacy-v1",
        )
        updated = upsert_quiz_labels(
            session=session,
            user_id=10,
            quiz_kind="ag",
            labels={"Realistic": 7},
            metadata={"correct": 7},
            definition_version="v2",
            scoring_version="v2",
        )
        upsert_quiz_labels(
            session=session,
            user_id=10,
            quiz_kind="SCL",
            labels={"anxiety": 3},
            definition_version="legacy-v1",
            scoring_version="legacy-v1",
        )

        row_count = session.scalar(select(func.count()).select_from(QuizLabel))
        records = list_quiz_labels_for_user(session=session, user_id=10)

    assert created["id"] == updated["id"]
    assert row_count == 2
    assert [record["quiz_kind"] for record in records] == ["AG", "SCL"]
    assert records[0]["labels"] == {"Realistic": 7}
    assert records[0]["metadata"] == {"correct": 7}
    assert records[0]["definition_version"] == "v2"


def test_quiz_labels_require_json_objects():
    with _create_session() as session:
        with pytest.raises(TypeError, match="labels must be a mapping"):
            upsert_quiz_labels(
                session=session,
                user_id=10,
                quiz_kind="AG",
                labels=[1, 2, 3],
                definition_version="legacy-v1",
                scoring_version="legacy-v1",
            )

        with pytest.raises(ValueError, match="Out of range float values"):
            upsert_quiz_labels(
                session=session,
                user_id=10,
                quiz_kind="AG",
                labels={"invalid": float("nan")},
                definition_version="legacy-v1",
                scoring_version="legacy-v1",
            )


def test_psy_scheduler_handler_persists_computed_labels(monkeypatch):
    session = Mock()
    stored_labels = Mock()
    update_status = Mock()
    monkeypatch.setattr(
        scheduler_module,
        "session_scope",
        lambda: nullcontext(session),
    )
    monkeypatch.setattr(scheduler_module, "upsert_quiz_labels", stored_labels)
    monkeypatch.setattr(scheduler_module, "update_redis_log_status", update_status)

    runtime = Mock(
        package_name="PSY_ANX",
        definition_versions=("v1",),
        scoring_version="v1",
    )
    runtime.score_user.return_value = ({"pen.worry": 10}, [3, 4])
    report_scheduler = scheduler_module.AGReportScheduler.__new__(
        scheduler_module.AGReportScheduler
    )
    report_scheduler._log_error = Mock()

    report_scheduler._handle_psy_labels("10", runtime)

    stored_labels.assert_called_once_with(
        session=session,
        user_id="10",
        quiz_kind="PSY_ANX",
        labels={"pen.worry": 10},
        metadata={"missing_questions": [3, 4]},
        definition_version="v1",
        scoring_version="v1",
    )
    assert [call.kwargs["status"] for call in update_status.call_args_list] == [1, 2]
