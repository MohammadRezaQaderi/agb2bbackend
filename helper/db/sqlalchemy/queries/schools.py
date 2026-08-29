from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from helper.db.sqlalchemy.models import School, User


def get_school_profile(session: Session, user_id: int) -> dict | None:
    statement = (
        select(
            School.sch_id.label("sch_id"),
            School.name.label("name"),
            School.logo.label("logo"),
            User.phone.label("phone"),
        )
        .join(User, User.user_id == School.user_id)
        .where(School.user_id == user_id)
        .limit(1)
    )
    row = session.execute(statement).mappings().first()
    return dict(row) if row else None


def create_school_profile(session: Session, user_id: int, name: str) -> None:
    session.add(School(user_id=user_id, name=name))
    session.flush()


def update_school_profile(session: Session, user_id: int, name: str, logo: str | None = None) -> int:
    school = session.get(School, user_id)
    if not school:
        return 0

    school.name = name
    if logo is not None:
        school.logo = logo
    school.edited_time = datetime.now()
    session.flush()
    return 1


def verify_school(session: Session, user_id: int) -> int:
    school = session.get(School, user_id)
    if not school:
        return 0

    school.verify = 1
    school.edited_time = datetime.now()
    session.flush()
    return 1
