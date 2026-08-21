from __future__ import annotations

from typing import Literal

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session, aliased

from helper.db.sqlalchemy.filters import StudentFilters
from helper.db.sqlalchemy.models import Consultant, Student, StudentPackageAccess, User
from helper.db.sqlalchemy.pagination import Page, paginate_mappings

StudentScope = Literal["owner", "consultant"]


def student_list_statement(
    scope: StudentScope,
    user_id: int,
    filters: StudentFilters | None = None,
) -> Select:
    consultant = aliased(Consultant)
    filters = filters or StudentFilters()

    statement = (
        select(
            Student.stu_id.label("stu_id"),
            Student.user_id.label("user_id"),
            User.phone.label("phone"),
            Student.first_name.label("first_name"),
            Student.last_name.label("last_name"),
            Student.sex.label("sex"),
            Student.city.label("city"),
            Student.birth_date.label("birth_date"),
            Student.access.label("access"),
            Student.comment.label("comment"),
            Student.owner_user_id.label("owner_user_id"),
            Student.consultant_user_id.label("consultant_user_id"),
            Student.consultant_user_id.label("con_id"),
            consultant.first_name.label("consultant_first_name"),
            consultant.last_name.label("consultant_last_name"),
        )
        .join(User, User.user_id == Student.user_id)
        .outerjoin(consultant, consultant.user_id == Student.consultant_user_id)
        .order_by(Student.created_time.desc(), Student.user_id.desc())
    )

    if scope == "owner":
        statement = statement.where(Student.owner_user_id == user_id)
    elif scope == "consultant":
        statement = statement.where(Student.consultant_user_id == user_id)
    else:
        raise ValueError(f"Unsupported student scope: {scope}")

    if filters.search:
        pattern = f"%{filters.search}%"
        statement = statement.where(
            or_(
                Student.first_name.like(pattern),
                Student.last_name.like(pattern),
                User.phone.like(pattern),
            )
        )

    if filters.sex is not None:
        statement = statement.where(Student.sex == filters.sex)

    if filters.city:
        statement = statement.where(Student.city == filters.city)

    if filters.package_name:
        access_conditions = [
            StudentPackageAccess.stu_user_id == Student.user_id,
            StudentPackageAccess.package_name == filters.package_name.upper(),
        ]
        if filters.access_permission is not None:
            access_conditions.append(StudentPackageAccess.permission == filters.access_permission)

        statement = statement.where(
            select(StudentPackageAccess.id)
            .where(and_(*access_conditions))
            .exists()
        )

    return statement


def list_students(
    session: Session,
    scope: StudentScope,
    user_id: int,
    filters: StudentFilters | None = None,
) -> list[dict]:
    statement = student_list_statement(scope=scope, user_id=user_id, filters=filters)
    return [dict(row) for row in session.execute(statement).mappings().all()]


def paginate_students(
    session: Session,
    scope: StudentScope,
    user_id: int,
    filters: StudentFilters | None = None,
    page: int | str | None = None,
    page_size: int | str | None = None,
) -> Page:
    statement = student_list_statement(scope=scope, user_id=user_id, filters=filters)
    return paginate_mappings(session, statement, page=page, page_size=page_size)


def list_students_for_owner(
    session: Session,
    owner_user_id: int,
    filters: StudentFilters | None = None,
) -> list[dict]:
    return list_students(session, scope="owner", user_id=owner_user_id, filters=filters)


def list_students_for_consultant(
    session: Session,
    consultant_user_id: int,
    filters: StudentFilters | None = None,
) -> list[dict]:
    return list_students(session, scope="consultant", user_id=consultant_user_id, filters=filters)
