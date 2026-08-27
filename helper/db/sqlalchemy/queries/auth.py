from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from helper.db.sqlalchemy.models import Institute, OwnerConsultant, School, Token, User


def get_user_auth_by_phone(session: Session, phone: str) -> dict | None:
    statement = (
        select(
            User.user_id.label("user_id"),
            User.phone.label("phone"),
            User.password.label("password"),
            User.role.label("role"),
        )
        .where(User.phone == phone)
        .limit(1)
    )
    row = session.execute(statement).mappings().first()
    return dict(row) if row else None


def get_user_identity_by_phone(session: Session, phone: str) -> dict | None:
    statement = (
        select(
            User.user_id.label("user_id"),
            User.phone.label("phone"),
            User.role.label("role"),
        )
        .where(User.phone == phone)
        .limit(1)
    )
    row = session.execute(statement).mappings().first()
    return dict(row) if row else None


def user_phone_exists(session: Session, phone: str) -> bool:
    statement = select(User.user_id).where(User.phone == phone).limit(1)
    return session.execute(statement).scalar_one_or_none() is not None


def create_user(session: Session, phone: str, password: str, role: str) -> int:
    user = User(phone=phone, password=password, role=role)
    session.add(user)
    session.flush()
    return user.user_id


def get_token_for_user(session: Session, user_id: int) -> str | None:
    statement = select(Token.token).where(Token.user_id == user_id).limit(1)
    return session.execute(statement).scalar_one_or_none()


def token_exists(session: Session, token: str) -> bool:
    statement = select(Token.token_id).where(Token.token == token).limit(1)
    return session.execute(statement).scalar_one_or_none() is not None


def create_token(session: Session, user_id: int, token: str) -> str:
    session.add(Token(user_id=user_id, token=token))
    session.flush()
    return token


def delete_token_for_user(session: Session, user_id: int) -> int:
    result = session.execute(delete(Token).where(Token.user_id == user_id))
    return int(result.rowcount or 0)


def get_role_verify_status(session: Session, user_id: int, role: str) -> int | None:
    role = (role or "").lower()
    model_by_role = {
        "ins": Institute,
        "sch": School,
        "ocon": OwnerConsultant,
    }
    model = model_by_role.get(role)
    if model is None:
        return None

    statement = select(model.verify).where(model.user_id == user_id).limit(1)
    return session.execute(statement).scalar_one_or_none()
