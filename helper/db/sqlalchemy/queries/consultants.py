from __future__ import annotations

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from helper.db.sqlalchemy.filters import ConsultantFilters
from helper.db.sqlalchemy.models import Consultant, User


def consultant_list_statement(
    owner_user_id: int,
    filters: ConsultantFilters | None = None,
) -> Select:
    filters = filters or ConsultantFilters()

    statement = (
        select(
            Consultant.con_id.label("con_id"),
            Consultant.user_id.label("user_id"),
            User.phone.label("phone"),
            Consultant.first_name.label("first_name"),
            Consultant.last_name.label("last_name"),
            Consultant.sex.label("sex"),
        )
        .join(User, User.user_id == Consultant.user_id)
        .where(Consultant.owner_user_id == owner_user_id)
        .order_by(Consultant.created_time.desc(), Consultant.user_id.desc())
    )

    if filters.search:
        pattern = f"%{filters.search}%"
        statement = statement.where(
            or_(
                Consultant.first_name.like(pattern),
                Consultant.last_name.like(pattern),
                User.phone.like(pattern),
            )
        )

    if filters.sex is not None:
        statement = statement.where(Consultant.sex == filters.sex)

    return statement


def list_consultants_for_owner(
    session: Session,
    owner_user_id: int,
    filters: ConsultantFilters | None = None,
) -> list[dict]:
    statement = consultant_list_statement(owner_user_id=owner_user_id, filters=filters)
    return [dict(row) for row in session.execute(statement).mappings().all()]
