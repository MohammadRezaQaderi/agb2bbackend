from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, aliased

from helper.db.sqlalchemy.filters import ConsultantFilters
from helper.db.sqlalchemy.models import Consultant, Institute, School, Student, User


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


def get_consultant_profile(session: Session, user_id: int) -> dict | None:
    owner = aliased(User)
    statement = (
        select(
            Consultant.con_id.label("con_id"),
            User.phone.label("phone"),
            Consultant.first_name.label("first_name"),
            Consultant.last_name.label("last_name"),
            Consultant.owner_user_id.label("owner_user_id"),
            owner.role.label("owner_role"),
            Institute.name.label("institute_name"),
            Institute.logo.label("institute_logo"),
            School.name.label("school_name"),
            School.logo.label("school_logo"),
        )
        .join(User, User.user_id == Consultant.user_id)
        .outerjoin(owner, owner.user_id == Consultant.owner_user_id)
        .outerjoin(Institute, Institute.user_id == Consultant.owner_user_id)
        .outerjoin(School, School.user_id == Consultant.owner_user_id)
        .where(Consultant.user_id == user_id)
        .limit(1)
    )
    row = session.execute(statement).mappings().first()
    return dict(row) if row else None


def update_student_profile_by_consultant(
    session: Session,
    student_user_id: int,
    editor_id: int,
    first_name: str,
    last_name: str,
    sex: int,
    city: str,
    birth_date: str,
) -> int:
    student = session.get(Student, student_user_id)
    if not student:
        return 0

    student.first_name = first_name
    student.last_name = last_name
    student.sex = sex
    student.city = city
    student.birth_date = birth_date
    student.editor_id = editor_id
    student.edited_time = datetime.now()
    session.flush()
    return 1


def update_student_comment_by_consultant(
    session: Session,
    student_user_id: int,
    editor_id: int,
    comment: str,
) -> int:
    student = session.get(Student, student_user_id)
    if not student:
        return 0

    student.comment = comment
    student.editor_id = editor_id
    student.edited_time = datetime.now()
    session.flush()
    return 1


def update_consultant_name(session: Session, user_id: int, first_name: str, last_name: str) -> int:
    consultant = session.get(Consultant, user_id)
    if not consultant:
        return 0

    consultant.first_name = first_name
    consultant.last_name = last_name
    consultant.edited_time = datetime.now()
    session.flush()
    return 1


def create_consultant_profile(
    session: Session,
    user_id: int,
    owner_user_id: int,
    editor_id: int,
    first_name: str,
    last_name: str,
    sex: int,
) -> None:
    session.add(
        Consultant(
            user_id=user_id,
            owner_user_id=owner_user_id,
            editor_id=editor_id,
            first_name=first_name,
            last_name=last_name,
            sex=sex,
        )
    )
    session.flush()


def update_consultant_profile_for_owner(
    session: Session,
    user_id: int,
    editor_id: int,
    first_name: str,
    last_name: str,
    sex: int,
) -> int:
    consultant = session.get(Consultant, user_id)
    if not consultant:
        return 0

    consultant.first_name = first_name
    consultant.last_name = last_name
    consultant.sex = sex
    consultant.editor_id = editor_id
    consultant.edited_time = datetime.now()
    session.flush()
    return 1
