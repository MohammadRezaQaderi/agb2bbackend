from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from helper.db.sqlalchemy.models import (
    ApiLog,
    Comment,
    Consultant,
    Discount,
    Institute,
    Notification,
    NotificationRead,
    OwnerConsultant,
    Payment,
    PaymentLog,
    Product,
    ResultState,
    School,
    SclScore,
    Score,
    UsingDiscount,
    User,
)


PAYMENT_FIELDS = (
    "payment_id",
    "user_id",
    "phone",
    "state",
    "status",
    "price",
    "discount_price",
    "track_id",
    "result",
    "discount_id",
    "message",
    "product_data",
    "token",
)


def list_all_products(session: Session) -> list[dict]:
    statement = (
        select(
            Product.product_id.label("id"),
            Product.name.label("name"),
            Product.price.label("price"),
            Product.status.label("status"),
            Product.image.label("image"),
        )
        .order_by(Product.created_time.desc())
    )
    return [dict(row) for row in session.execute(statement).mappings().all()]


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


def get_payment_status(session: Session, user_id: int, payment_id: int) -> dict | None:
    statement = (
        select(
            Payment.payment_id.label("id"),
            Payment.state.label("state"),
            Payment.status.label("status"),
            Payment.price.label("price"),
            Payment.product_data.label("product_data"),
            Payment.result.label("result"),
            Payment.edited_time.label("date"),
        )
        .where(Payment.user_id == user_id, Payment.payment_id == payment_id)
        .order_by(Payment.created_time.desc())
        .limit(1)
    )
    row = session.execute(statement).mappings().first()
    return dict(row) if row else None


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


def get_discount_by_code(session: Session, code: str) -> dict | None:
    statement = select(Discount).where(Discount.code == code).limit(1)
    discount = session.execute(statement).scalars().first()
    if not discount:
        return None
    return {
        "id": discount.id,
        "discount_percentage": discount.discount_percentage,
        "count": discount.count,
        "status": discount.status,
        "used_apply": discount.used_apply,
        "count_apply": discount.count_apply,
        "expire_time": discount.expire_time,
    }


def create_discount(
    session: Session,
    code: str,
    status: str,
    discount_percentage: float,
    count: int = 100,
    count_apply: int = 0,
    expire_time: datetime | None = None,
) -> int:
    now = datetime.now()
    discount = Discount(
        code=code,
        status=status,
        discount_percentage=discount_percentage,
        count=count,
        count_apply=count_apply,
        expire_time=expire_time,
        created_time=now,
        edited_time=now,
    )
    session.add(discount)
    session.flush()
    return discount.id


def record_discount_usage(
    session: Session,
    discount_id: int,
    code: str,
    status: str,
    phone: str,
    user_id: int,
    counter_field: str,
) -> None:
    discount = session.get(Discount, discount_id)
    if not discount:
        return

    session.add(UsingDiscount(code=code, status=status, phone=phone, user_id=user_id))
    if counter_field == "count_apply":
        discount.count_apply = (discount.count_apply or 0) + 1
    elif counter_field == "used_apply":
        discount.used_apply = (discount.used_apply or 0) + 1
    discount.edited_time = datetime.now()
    session.flush()


def create_payment(session: Session, payment_data: dict[str, Any]) -> None:
    session.add(Payment(**{field: payment_data.get(field) for field in PAYMENT_FIELDS}))
    session.flush()


def create_payment_log(session: Session, payment_data: dict[str, Any]) -> None:
    session.add(PaymentLog(**{field: payment_data.get(field) for field in PAYMENT_FIELDS}))
    session.flush()


def get_comment_user_info_by_phone(session: Session, phone: str) -> dict | None:
    user = session.execute(
        select(
            User.user_id.label("user_id"),
            User.role.label("role"),
        )
        .where(User.phone == phone)
        .limit(1)
    ).mappings().first()
    if not user:
        return None

    user_id = user["user_id"]
    role = user["role"]
    db_name = ""

    if role == "ins":
        db_name = session.execute(select(Institute.name).where(Institute.user_id == user_id)).scalar_one_or_none() or ""
    elif role == "sch":
        db_name = session.execute(select(School.name).where(School.user_id == user_id)).scalar_one_or_none() or ""
    elif role == "con":
        row = session.execute(
            select(Consultant.first_name, Consultant.last_name).where(Consultant.user_id == user_id)
        ).first()
        db_name = f"{row[0]} {row[1]}" if row else ""
    elif role == "ocon":
        row = session.execute(
            select(OwnerConsultant.first_name, OwnerConsultant.last_name)
            .where(OwnerConsultant.user_id == user_id)
        ).first()
        db_name = f"{row[0]} {row[1]}" if row else ""

    return {"user_id": user_id, "role": role, "db_name": db_name}


def create_comment(
    session: Session,
    name: str,
    comment: str,
    rating: float,
    persian_date: str,
    user_id: int,
    phone: str,
    db_name: str,
    role: str,
) -> None:
    session.add(
        Comment(
            name=name,
            comment=comment,
            rating=rating,
            persian_date=persian_date,
            user_id=user_id,
            phone=phone,
            db_name=db_name,
            role=role,
        )
    )
    session.flush()


def create_notification(
    session: Session,
    roles: str,
    title: str,
    description: str,
    added_by: str,
    priority: str,
    persian_date: str,
    full_text: str,
    user_id: int | None = None,
) -> int:
    now = datetime.now()
    notification = Notification(
        roles=roles,
        user_id=user_id,
        title=title,
        description=description,
        added_by=added_by,
        priority=priority,
        persian_date=persian_date,
        full_text=full_text,
        created_time=now,
        edited_time=now,
    )
    session.add(notification)
    session.flush()
    return notification.id


def mark_notification_read_if_allowed(
    session: Session,
    notification_id: int,
    user_id: int,
    role_aliases: list[str],
) -> bool:
    role_conditions = [Notification.roles.like(f"%{role}%") for role in role_aliases]
    statement = (
        select(Notification.id)
        .where(
            Notification.id == notification_id,
            or_(Notification.user_id == user_id, Notification.roles.like("%all%"), *role_conditions),
        )
        .limit(1)
    )
    if session.execute(statement).scalar_one_or_none() is None:
        return False

    read_exists = session.execute(
        select(NotificationRead.id)
        .where(
            NotificationRead.notification_id == notification_id,
            NotificationRead.user_id == user_id,
        )
        .limit(1)
    ).scalar_one_or_none()
    if read_exists is None:
        session.add(NotificationRead(notification_id=notification_id, user_id=user_id))
        session.flush()
    return True


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
