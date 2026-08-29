from __future__ import annotations

from sqlalchemy.orm import Session

from helper.db.sqlalchemy.models import OtpLog


def create_otp_log(session: Session, phone: str, code: str | int, provider_resp: str, type_otp: str) -> None:
    session.add(
        OtpLog(
            phone=phone,
            code=str(code),
            provider_resp=provider_resp,
            type_otp=type_otp,
        )
    )
    session.flush()
