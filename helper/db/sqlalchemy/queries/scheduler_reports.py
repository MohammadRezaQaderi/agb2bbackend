from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, aliased

from helper.db.sqlalchemy.models import (
    Consultant,
    HedayatField,
    Institute,
    OwnerConsultant,
    QuizAttempt,
    RedisLog,
    ResultState,
    School,
    SclScore,
    Score,
    Student,
    User,
)


def update_redis_log_status(session: Session, user_id: int | str, kind: str, result: str, status: int) -> int:
    statement = (
        update(RedisLog)
        .where(RedisLog.user_id == int(user_id), RedisLog.kind == (kind or "").upper())
        .values(result=result, status=status, edited_time=datetime.now())
    )
    updated = session.execute(statement)
    session.flush()
    return int(updated.rowcount or 0)


def get_scheduler_student_context(session: Session, user_id: int | str) -> dict | None:
    owner = aliased(User)
    row = session.execute(
        select(
            Student.user_id.label("user_id"),
            Student.first_name.label("first_name"),
            Student.last_name.label("last_name"),
            User.phone.label("phone"),
            Student.owner_user_id.label("owner_user_id"),
            Student.consultant_user_id.label("consultant_user_id"),
            owner.role.label("owner_role"),
            Institute.name.label("institute_name"),
            Institute.logo.label("institute_logo"),
            School.name.label("school_name"),
            School.logo.label("school_logo"),
            OwnerConsultant.first_name.label("ocon_first_name"),
            OwnerConsultant.last_name.label("ocon_last_name"),
            Consultant.first_name.label("consultant_first_name"),
            Consultant.last_name.label("consultant_last_name"),
        )
        .join(User, User.user_id == Student.user_id)
        .outerjoin(owner, owner.user_id == Student.owner_user_id)
        .outerjoin(Institute, Institute.user_id == Student.owner_user_id)
        .outerjoin(School, School.user_id == Student.owner_user_id)
        .outerjoin(OwnerConsultant, OwnerConsultant.user_id == Student.owner_user_id)
        .outerjoin(Consultant, Consultant.user_id == Student.consultant_user_id)
        .where(Student.user_id == int(user_id))
        .limit(1)
    ).mappings().first()
    return dict(row) if row else None


def count_completed_quiz_attempts(session: Session, user_id: int | str, report_kind: str) -> int:
    statement = (
        select(func.count())
        .select_from(QuizAttempt)
        .where(
            QuizAttempt.user_id == int(user_id),
            QuizAttempt.quiz_kind == report_kind,
            QuizAttempt.state == 2,
        )
    )
    return int(session.execute(statement).scalar_one() or 0)


def upsert_hedayat_fields(session: Session, user_id: int | str, suggested: str, other: str) -> None:
    record = session.execute(
        select(HedayatField).where(HedayatField.user_id == int(user_id)).limit(1)
    ).scalars().first()
    if not record:
        session.add(HedayatField(user_id=int(user_id), suggested=suggested, other=other))
        session.flush()
        return

    record.suggested = suggested
    record.other = other
    record.edited_time = datetime.now()
    session.flush()


def upsert_scl_score(session: Session, user_id: int | str, scl_date: str) -> None:
    record = session.execute(
        select(SclScore).where(SclScore.user_id == int(user_id)).limit(1)
    ).scalars().first()
    if not record:
        session.add(SclScore(user_id=int(user_id), scl_date=scl_date))
        session.flush()
        return

    record.scl_date = scl_date
    record.edited_time = datetime.now()
    session.flush()


def upsert_result_state(session: Session, user_id: int | str, state_data: list[str]) -> None:
    record = session.get(ResultState, int(user_id))
    values = {
        "t_state": state_data[0],
        "r_state": state_data[1],
        "e_state": state_data[2],
        "a_state": state_data[3],
        "m_state": state_data[4],
        "f_state": state_data[5],
        "i_state": state_data[6],
    }
    if not record:
        session.add(ResultState(user_id=int(user_id), **values))
        session.flush()
        return

    for key, value in values.items():
        setattr(record, key, value)
    record.edited_time = datetime.now()
    session.flush()


def upsert_score(
    session: Session,
    user_id: int | str,
    quiz_score: str,
    brain_fields: str,
    brain_categories: str,
    brain_branches: str,
) -> None:
    record = session.execute(
        select(Score).where(Score.user_id == int(user_id)).limit(1)
    ).scalars().first()
    values = {
        "quiz_score": quiz_score,
        "brain_fields": brain_fields,
        "brain_categories": brain_categories,
        "brain_branches": brain_branches,
    }
    if not record:
        session.add(Score(user_id=int(user_id), **values))
        session.flush()
        return

    for key, value in values.items():
        setattr(record, key, value)
    record.edited_time = datetime.now()
    session.flush()
