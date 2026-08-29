from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from helper.db.sqlalchemy.models import QuizAttempt, QuizMissingAnswer, QuizQuestionAnswer


def _attempt_to_dict(attempt: QuizAttempt) -> dict:
    return {
        "id": attempt.id,
        "user_id": attempt.user_id,
        "quiz_kind": attempt.quiz_kind,
        "quiz_id": attempt.quiz_id,
        "state": attempt.state,
        "remain_time": attempt.remain_time,
        "owner_user_id": attempt.owner_user_id,
        "consultant_user_id": attempt.consultant_user_id,
        "ins_id": attempt.owner_user_id,
        "con_id": attempt.consultant_user_id,
        "created_time": attempt.created_time,
        "edited_time": attempt.edited_time,
    }


def list_attempts_for_user_kind(session: Session, user_id: int, quiz_kind: str) -> list[dict]:
    statement = (
        select(QuizAttempt)
        .where(QuizAttempt.user_id == user_id, QuizAttempt.quiz_kind == quiz_kind)
        .order_by(QuizAttempt.quiz_id.asc())
    )
    return [_attempt_to_dict(attempt) for attempt in session.execute(statement).scalars().all()]


def get_attempt_for_user_kind_quiz(
    session: Session,
    user_id: int,
    quiz_kind: str,
    quiz_id: int,
) -> dict | None:
    statement = (
        select(QuizAttempt)
        .where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.quiz_kind == quiz_kind,
            QuizAttempt.quiz_id == quiz_id,
        )
        .limit(1)
    )
    attempt = session.execute(statement).scalars().first()
    return _attempt_to_dict(attempt) if attempt else None


def list_answers_for_attempt(session: Session, attempt_id: int) -> list[dict]:
    statement = (
        select(
            QuizQuestionAnswer.question_id.label("question_id"),
            QuizQuestionAnswer.answer_value.label("answer_value"),
        )
        .where(QuizQuestionAnswer.attempt_id == attempt_id)
        .order_by(QuizQuestionAnswer.question_id.asc())
    )
    return [dict(row) for row in session.execute(statement).mappings().all()]


def list_answers_for_user_kind(session: Session, user_id: int, quiz_kind: str) -> list[dict]:
    statement = (
        select(
            QuizQuestionAnswer.question_id.label("question_id"),
            QuizQuestionAnswer.answer_value.label("answer_value"),
        )
        .where(
            QuizQuestionAnswer.user_id == user_id,
            QuizQuestionAnswer.quiz_kind == quiz_kind,
        )
        .order_by(QuizQuestionAnswer.quiz_id.asc(), QuizQuestionAnswer.question_id.asc())
    )
    return [dict(row) for row in session.execute(statement).mappings().all()]


def count_completed_attempts(session: Session, user_id: int, quiz_kind: str) -> int:
    statement = (
        select(func.count())
        .select_from(QuizAttempt)
        .where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.quiz_kind == quiz_kind,
            QuizAttempt.state == 2,
        )
    )
    return int(session.execute(statement).scalar_one() or 0)


def save_attempt(
    session: Session,
    user_id: int,
    quiz_kind: str,
    quiz_id: int,
    state: int,
    owner_user_id: int | None,
    consultant_user_id: int | None,
    remain_time: int | None = None,
) -> dict:
    statement = (
        select(QuizAttempt)
        .where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.quiz_kind == quiz_kind,
            QuizAttempt.quiz_id == quiz_id,
        )
        .limit(1)
    )
    attempt = session.execute(statement).scalars().first()
    if attempt:
        attempt.state = state
        attempt.edited_time = datetime.now()
        if remain_time is not None:
            attempt.remain_time = remain_time
        session.flush()
        return _attempt_to_dict(attempt)

    attempt = QuizAttempt(
        user_id=user_id,
        quiz_kind=quiz_kind,
        quiz_id=quiz_id,
        state=state,
        remain_time=remain_time,
        owner_user_id=owner_user_id,
        consultant_user_id=consultant_user_id,
    )
    session.add(attempt)
    session.flush()
    return _attempt_to_dict(attempt)


def mark_attempt_finished(session: Session, user_id: int, quiz_kind: str, quiz_id: int) -> int:
    statement = (
        select(QuizAttempt)
        .where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.quiz_kind == quiz_kind,
            QuizAttempt.quiz_id == quiz_id,
        )
        .limit(1)
    )
    attempt = session.execute(statement).scalars().first()
    if not attempt:
        return 0

    attempt.state = 2
    attempt.edited_time = datetime.now()
    session.flush()
    return 1


def save_question_answer(
    session: Session,
    attempt: dict,
    question_id: int,
    answer_value: str,
) -> bool | int:
    statement = (
        select(QuizQuestionAnswer)
        .where(
            QuizQuestionAnswer.attempt_id == attempt["id"],
            QuizQuestionAnswer.question_id == question_id,
        )
        .order_by(QuizQuestionAnswer.id.asc())
        .limit(1)
    )
    existing_answer = session.execute(statement).scalars().first()
    if existing_answer:
        existing_answer.answer_value = answer_value
        existing_answer.edited_time = datetime.now()
        session.flush()
        return 1

    session.add(
        QuizQuestionAnswer(
            attempt_id=attempt["id"],
            user_id=attempt["user_id"],
            quiz_kind=attempt["quiz_kind"],
            quiz_id=attempt["quiz_id"],
            question_id=question_id,
            answer_value=answer_value,
        )
    )
    session.flush()
    return True


def create_missing_answer(session: Session, user_id: int, question_id: int) -> bool:
    session.add(QuizMissingAnswer(user_id=user_id, question_id=question_id))
    session.flush()
    return True
