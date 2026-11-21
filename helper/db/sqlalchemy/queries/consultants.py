from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session, aliased

from helper.db.sqlalchemy.filters import ConsultantFilters
from helper.db.sqlalchemy.models import Consultant, Institute, School, Student, User
from helper.db.sqlalchemy.pagination import Page, paginate_mappings


def consultant_list_statement(
    owner_user_id: int,
    filters: ConsultantFilters | None = None,
    sort_by: str | None = None,
    sort_direction: str | None = None,
) -> Select:
    filters = filters or ConsultantFilters()

    statement = (
        select(
            Consultant.con_id.label("con_id"),
            Consultant.user_id.label("user_id"),
            User.phone.label("phone"),
            User.password.label("password"),
            Consultant.first_name.label("first_name"),
            Consultant.last_name.label("last_name"),
            Consultant.sex.label("sex"),
        )
        .join(User, User.user_id == Consultant.user_id)
        .where(Consultant.owner_user_id == owner_user_id)
    )

    if filters.search:
        statement = statement.where(
            _word_search_condition(
                filters.search,
                Consultant.first_name,
                Consultant.last_name,
                User.phone,
            )
        )

    if filters.name:
        statement = statement.where(_word_search_condition(filters.name, Consultant.first_name, Consultant.last_name))

    if filters.phone:
        statement = statement.where(User.phone.ilike(f"%{filters.phone}%"))

    if filters.sex is not None:
        statement = statement.where(Consultant.sex == filters.sex)

    sort_columns = {
        "full_name": (Consultant.first_name, Consultant.last_name),
        "phone": (User.phone,),
        "created_time": (Consultant.created_time,),
    }
    columns = sort_columns.get(str(sort_by or ""))
    if not columns:
        return statement.order_by(Consultant.created_time.desc(), Consultant.user_id.desc())

    descending = str(sort_direction or "asc").lower() == "desc"
    ordering = [column.desc() if descending else column.asc() for column in columns]
    return statement.order_by(*ordering, Consultant.user_id.desc())


def _word_search_condition(value: str, *columns):
    words = value.split()
    return and_(*(or_(*(column.ilike(f"%{word}%") for column in columns)) for word in words))


def list_consultants_for_owner(
    session: Session,
    owner_user_id: int,
    filters: ConsultantFilters | None = None,
    sort_by: str | None = None,
    sort_direction: str | None = None,
) -> list[dict]:
    statement = consultant_list_statement(
        owner_user_id=owner_user_id,
        filters=filters,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return [dict(row) for row in session.execute(statement).mappings().all()]


def paginate_consultants_for_owner(
    session: Session,
    owner_user_id: int,
    filters: ConsultantFilters | None = None,
    page: int | str | None = None,
    page_size: int | str | None = None,
    sort_by: str | None = None,
    sort_direction: str | None = None,
) -> Page:
    statement = consultant_list_statement(
        owner_user_id=owner_user_id,
        filters=filters,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return paginate_mappings(session, statement, page=page, page_size=page_size)


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
