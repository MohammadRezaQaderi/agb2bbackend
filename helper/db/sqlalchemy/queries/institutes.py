from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from helper.db.sqlalchemy.models import Institute, Setting, User


def get_institute_profile(session: Session, user_id: int) -> dict | None:
    statement = (
        select(
            Institute.ins_id.label("ins_id"),
            Institute.name.label("name"),
            Institute.logo.label("logo"),
            User.phone.label("phone"),
        )
        .join(User, User.user_id == Institute.user_id)
        .where(Institute.user_id == user_id)
        .limit(1)
    )
    row = session.execute(statement).mappings().first()
    return dict(row) if row else None


def create_institute_profile(session: Session, user_id: int, name: str) -> None:
    session.add(Institute(user_id=user_id, name=name))
    session.flush()


def update_institute_profile(session: Session, user_id: int, name: str, logo: str | None = None) -> int:
    institute = session.get(Institute, user_id)
    if not institute:
        return 0

    institute.name = name
    if logo is not None:
        institute.logo = logo
    institute.edited_time = datetime.now()
    session.flush()
    return 1


def verify_institute(session: Session, user_id: int) -> int:
    institute = session.get(Institute, user_id)
    if not institute:
        return 0

    institute.verify = 1
    institute.edited_time = datetime.now()
    session.flush()
    return 1


def upsert_setting(
    session: Session,
    setting_id: int | str,
    user_id: int,
    description: str,
    voice: str | None,
    quiz_id: int,
) -> None:
    if setting_id == "no setting":
        session.add(Setting(user_id=user_id, description=description, voice=voice, quiz_id=quiz_id))
        session.flush()
        return

    setting = session.get(Setting, int(setting_id))
    if not setting:
        return

    setting.description = description
    if voice is not None:
        setting.voice = voice
    setting.edited_time = datetime.now()
    session.flush()
