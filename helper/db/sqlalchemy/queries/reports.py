from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from helper.db.sqlalchemy.models import QuizAttempt


def list_quiz_attempts_for_users(
    session: Session,
    user_ids: list[int],
    package_names: list[str] | None = None,
) -> list[dict]:
    if not user_ids:
        return []
    if package_names is not None and not package_names:
        return []

    statement = (
        select(
            QuizAttempt.user_id.label("user_id"),
            QuizAttempt.quiz_kind.label("quiz_kind"),
            QuizAttempt.quiz_id.label("quiz_id"),
            QuizAttempt.state.label("state"),
        )
        .where(QuizAttempt.user_id.in_(user_ids))
    )
    if package_names is not None:
        statement = statement.where(QuizAttempt.quiz_kind.in_(package_names))
    statement = statement.order_by(
        QuizAttempt.user_id.asc(),
        QuizAttempt.quiz_kind.asc(),
        QuizAttempt.quiz_id.asc(),
    )
    return [dict(row) for row in session.execute(statement).mappings().all()]
