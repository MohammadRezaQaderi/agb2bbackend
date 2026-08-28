from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from helper.db.sqlalchemy.models import ApiLog, Comment, Payment, ResultState, SclScore, Score


def list_user_transactions(session: Session, user_id: int) -> list[dict]:
    statement = (
        select(
            Payment.payment_id.label("id"),
            Payment.state.label("state"),
            Payment.status.label("status"),
            Payment.product_data.label("product_data"),
            Payment.result.label("result"),
            Payment.edited_time.label("date"),
        )
        .where(Payment.user_id == user_id)
        .order_by(Payment.created_time.desc())
    )
    return [dict(row) for row in session.execute(statement).mappings().all()]


def list_latest_comments(session: Session, limit: int = 100) -> list[dict]:
    statement = (
        select(
            Comment.id.label("id"),
            Comment.name.label("name"),
            Comment.comment.label("comment"),
            Comment.rating.label("rating"),
            Comment.persian_date.label("persian_date"),
        )
        .order_by(Comment.created_time.desc())
        .limit(limit)
    )
    return [dict(row) for row in session.execute(statement).mappings().all()]


def get_result_state_for_user(session: Session, user_id: int) -> dict | None:
    statement = (
        select(
            ResultState.t_state.label("t_state"),
            ResultState.r_state.label("r_state"),
            ResultState.e_state.label("e_state"),
            ResultState.a_state.label("a_state"),
            ResultState.m_state.label("m_state"),
            ResultState.f_state.label("f_state"),
            ResultState.i_state.label("i_state"),
        )
        .where(ResultState.user_id == user_id)
    )
    row = session.execute(statement).mappings().first()
    return dict(row) if row else None


def get_score_brain_categories(session: Session, user_id: int) -> str | None:
    statement = select(Score.brain_categories).where(Score.user_id == user_id)
    return session.execute(statement).scalar_one_or_none()


def get_scl_score_date(session: Session, user_id: int) -> str | None:
    statement = select(SclScore.scl_date).where(SclScore.user_id == user_id)
    return session.execute(statement).scalar_one_or_none()


def payment_id_exists(session: Session, payment_id: int) -> bool:
    statement = select(Payment.id).where(Payment.payment_id == payment_id).limit(1)
    return session.execute(statement).scalar_one_or_none() is not None


def create_api_log(
    session: Session,
    user_id: int | None,
    phone: str | None,
    end_point: str,
    func_name: str,
    data: str | None,
    error_p: str,
) -> bool:
    session.add(
        ApiLog(
            user_id=user_id,
            phone=phone,
            end_point=end_point,
            func_name=func_name,
            data=data,
            error_p=error_p,
        )
    )
    session.flush()
    return True
