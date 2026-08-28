from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from helper.db.sqlalchemy.models import Setting


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
