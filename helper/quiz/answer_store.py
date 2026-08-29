from __future__ import annotations

import json
from typing import Any

from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.quiz import (
    count_completed_attempts,
    get_attempt_for_user_kind_quiz,
    list_answers_for_attempt,
    list_answers_for_user_kind,
    list_attempts_for_user_kind,
    mark_attempt_finished,
    save_attempt,
    save_question_answer,
)


def normalize_quiz_kind(kind: Any) -> str:
    return str(kind or "").upper()


def encode_answer_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def decode_answer_value(value: Any) -> Any:
    if value is None:
        return []
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        if "," in value:
            return [item for item in value.split(",") if item != ""]
        return [value] if value != "" else []


def normalize_answer_value(value: Any) -> Any:
    if isinstance(value, list):
        return [item for item in value if item is not None]
    return value


def get_attempts(user_id: int, quiz_kind: str):
    with session_scope() as session:
        return list_attempts_for_user_kind(
            session=session,
            user_id=user_id,
            quiz_kind=normalize_quiz_kind(quiz_kind),
        )


def get_attempt(user_id: int, quiz_kind: str, quiz_id: int):
    with session_scope() as session:
        return get_attempt_for_user_kind_quiz(
            session=session,
            user_id=user_id,
            quiz_kind=normalize_quiz_kind(quiz_kind),
            quiz_id=quiz_id,
        )


def upsert_attempt(user_id: int, quiz_kind: str, quiz_id: int, state: int,
                   owner_user_id: int | None, consultant_user_id: int | None, remain_time: int | None = None):
    quiz_kind = normalize_quiz_kind(quiz_kind)
    with session_scope() as session:
        return save_attempt(
            session=session,
            user_id=user_id,
            quiz_kind=quiz_kind,
            quiz_id=quiz_id,
            state=state,
            owner_user_id=owner_user_id,
            consultant_user_id=consultant_user_id,
            remain_time=remain_time,
        )


def finish_attempt(user_id: int, quiz_kind: str, quiz_id: int):
    with session_scope() as session:
        return mark_attempt_finished(
            session=session,
            user_id=user_id,
            quiz_kind=normalize_quiz_kind(quiz_kind),
            quiz_id=quiz_id,
        )


def upsert_question_answer(attempt: dict, question_id: int, answer_value: Any):
    stored_value = encode_answer_value(normalize_answer_value(answer_value))
    with session_scope() as session:
        return save_question_answer(
            session=session,
            attempt={**attempt, "quiz_kind": normalize_quiz_kind(attempt["quiz_kind"])},
            question_id=question_id,
            answer_value=stored_value,
        )


def get_answers_for_attempt(attempt_id: int) -> dict[str, Any]:
    with session_scope() as session:
        rows = list_answers_for_attempt(session=session, attempt_id=attempt_id)
    return {str(row["question_id"]): decode_answer_value(row.get("answer_value")) for row in rows}


def get_answers_for_user_kind(user_id: int, quiz_kind: str) -> dict[str, Any]:
    with session_scope() as session:
        rows = list_answers_for_user_kind(
            session=session,
            user_id=user_id,
            quiz_kind=normalize_quiz_kind(quiz_kind),
        )
    return {str(row["question_id"]): decode_answer_value(row.get("answer_value")) for row in rows}


def get_completed_count(user_id: int, quiz_kind: str) -> int:
    with session_scope() as session:
        return count_completed_attempts(
            session=session,
            user_id=user_id,
            quiz_kind=normalize_quiz_kind(quiz_kind),
        )
