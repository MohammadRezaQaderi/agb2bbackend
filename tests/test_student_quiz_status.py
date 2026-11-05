from unittest.mock import Mock

from services.student import student_service


QUIZZES = [
    {"id": 1, "quizName": "First"},
    {"id": 2, "quizName": "Second"},
]


def _prepare_quiz_table(monkeypatch, attempt):
    monkeypatch.setattr(student_service, "_load_student_access", lambda _user_id: {"AG": {"permission": 1}})
    monkeypatch.setattr(student_service, "_package_permission", lambda _access, _kind: (1, 1))
    monkeypatch.setattr(student_service, "get_quiz_table_info", lambda kind: QUIZZES)
    monkeypatch.setattr(student_service.answer_store, "get_attempts", lambda _user_id, _kind: [attempt])
    monkeypatch.setattr(student_service, "get_tracking_code", Mock(return_value="tracking"))


def test_empty_in_progress_attempt_is_reported_as_not_started(monkeypatch):
    _prepare_quiz_table(
        monkeypatch,
        {"quiz_id": 1, "state": 1, "answer_count": 0},
    )

    token, quizzes, message = student_service.select_stu_quiz_table_info(
        {"kind": "AG"},
        {"user_id": 42},
    )

    assert token == "tracking"
    assert message == ""
    assert quizzes[0]["status"] == 0
    assert quizzes[0]["can_start"] == 1
    assert quizzes[1]["status"] == 0
    assert quizzes[1]["can_start"] == 0


def test_attempt_with_saved_answers_is_reported_as_in_progress(monkeypatch):
    _prepare_quiz_table(
        monkeypatch,
        {"quiz_id": 1, "state": 1, "answer_count": 1},
    )

    _, quizzes, _ = student_service.select_stu_quiz_table_info(
        {"kind": "AG"},
        {"user_id": 42},
    )

    assert quizzes[0]["status"] == 1
    assert quizzes[0]["can_start"] == 1
