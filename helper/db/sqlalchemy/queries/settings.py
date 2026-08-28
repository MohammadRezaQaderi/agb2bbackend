from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from helper.db.sqlalchemy.models import Setting


def get_setting_for_user_quiz(session: Session, user_id: int, quiz_id: int) -> dict | None:
    setting = session.execute(
        select(Setting)
        .where(Setting.user_id == user_id, Setting.quiz_id == quiz_id)
        .limit(1)
    ).scalars().first()
    if not setting:
        return None
    return {
        "setting_id": setting.setting_id,
        "description": setting.description,
        "voice": setting.voice,
    }


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
