from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from helper.db.sqlalchemy.models import OwnerConsultant, User


def get_owner_consultant_profile(session: Session, user_id: int) -> dict | None:
    statement = (
        select(
            OwnerConsultant.ocon_id.label("ocon_id"),
            OwnerConsultant.first_name.label("first_name"),
            OwnerConsultant.last_name.label("last_name"),
            OwnerConsultant.logo.label("logo"),
            User.phone.label("phone"),
        )
        .join(User, User.user_id == OwnerConsultant.user_id)
        .where(OwnerConsultant.user_id == user_id)
        .limit(1)
    )
    row = session.execute(statement).mappings().first()
    return dict(row) if row else None


def create_owner_consultant_profile(
    session: Session,
    user_id: int,
    first_name: str,
    last_name: str,
    sex: int,
) -> None:
    session.add(
        OwnerConsultant(
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            sex=sex,
        )
    )
    session.flush()


def update_owner_consultant_profile(
    session: Session,
    user_id: int,
    first_name: str,
    last_name: str,
    logo: str | None = None,
) -> int:
    owner_consultant = session.get(OwnerConsultant, user_id)
    if not owner_consultant:
        return 0

    owner_consultant.first_name = first_name
    owner_consultant.last_name = last_name
    if logo is not None:
        owner_consultant.logo = logo
    owner_consultant.edited_time = datetime.now()
    session.flush()
    return 1


def verify_owner_consultant(session: Session, user_id: int) -> int:
    owner_consultant = session.get(OwnerConsultant, user_id)
    if not owner_consultant:
        return 0

    owner_consultant.verify = 1
    owner_consultant.edited_time = datetime.now()
    session.flush()
    return 1
