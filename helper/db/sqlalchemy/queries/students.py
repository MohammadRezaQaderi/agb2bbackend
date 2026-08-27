from __future__ import annotations

from datetime import datetime
from typing import Literal

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session, aliased

from helper.db.sqlalchemy.filters import StudentFilters
from helper.db.sqlalchemy.models import (
    Consultant,
    Institute,
    Notification,
    OwnerConsultant,
    RedisLog,
    ResultState,
    School,
    Score,
    Setting,
    Student,
    StudentPackageAccess,
    User,
)
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


def get_student_birth_date(session: Session, user_id: int) -> str | None:
    statement = select(Student.birth_date).where(Student.user_id == user_id)
    return session.execute(statement).scalar_one_or_none()


def list_student_package_access(session: Session, user_id: int) -> list[dict]:
    statement = (
        select(
            StudentPackageAccess.package_name.label("package_name"),
            StudentPackageAccess.permission.label("permission"),
            StudentPackageAccess.limit.label("limit"),
        )
        .where(StudentPackageAccess.stu_user_id == user_id)
        .order_by(StudentPackageAccess.package_name.asc())
    )
    return [dict(row) for row in session.execute(statement).mappings().all()]


def get_student_legacy_access(session: Session, user_id: int) -> str | None:
    statement = select(Student.access).where(Student.user_id == user_id)
    return session.execute(statement).scalar_one_or_none()


def get_student_access_comment(session: Session, user_id: int) -> dict | None:
    statement = (
        select(
            Student.access.label("access"),
            Student.comment.label("comment"),
        )
        .where(Student.user_id == user_id)
        .limit(1)
    )
    row = session.execute(statement).mappings().first()
    return dict(row) if row else None


def get_student_owner_consultant_ids(session: Session, user_id: int) -> tuple[int | None, int | None] | None:
    statement = (
        select(
            Student.owner_user_id.label("owner_user_id"),
            Student.consultant_user_id.label("consultant_user_id"),
        )
        .where(Student.user_id == user_id)
        .limit(1)
    )
    row = session.execute(statement).mappings().first()
    if not row:
        return None
    if row["owner_user_id"] is None:
        return row["consultant_user_id"], row["consultant_user_id"]
    return row["owner_user_id"], row["consultant_user_id"]


def get_student_owner_user_id(session: Session, user_id: int) -> int | None:
    statement = select(Student.owner_user_id).where(Student.user_id == user_id)
    return session.execute(statement).scalar_one_or_none()


def get_student_profile(session: Session, user_id: int) -> dict | None:
    owner = aliased(User)
    statement = (
        select(
            Student.stu_id.label("stu_id"),
            Student.user_id.label("user_id"),
            User.phone.label("phone"),
            Student.first_name.label("first_name"),
            Student.last_name.label("last_name"),
            Student.sex.label("sex"),
            Student.city.label("city"),
            Student.access.label("access"),
            Student.owner_user_id.label("owner_user_id"),
            Student.consultant_user_id.label("consultant_user_id"),
            Student.birth_date.label("birth_date"),
            owner.role.label("owner_role"),
            Institute.name.label("institute_name"),
            Institute.logo.label("institute_logo"),
            Institute.user_id.label("institute_user_id"),
            School.name.label("school_name"),
            School.logo.label("school_logo"),
            School.user_id.label("school_user_id"),
            Consultant.first_name.label("consultant_first_name"),
            Consultant.last_name.label("consultant_last_name"),
            OwnerConsultant.first_name.label("ocon_first_name"),
            OwnerConsultant.last_name.label("ocon_last_name"),
        )
        .join(User, User.user_id == Student.user_id)
        .outerjoin(owner, owner.user_id == Student.owner_user_id)
        .outerjoin(Institute, Institute.user_id == Student.owner_user_id)
        .outerjoin(School, School.user_id == Student.owner_user_id)
        .outerjoin(Consultant, Consultant.user_id == Student.consultant_user_id)
        .outerjoin(OwnerConsultant, OwnerConsultant.user_id == Student.consultant_user_id)
        .where(Student.user_id == user_id)
        .limit(1)
    )
    row = session.execute(statement).mappings().first()
    return dict(row) if row else None


def get_latest_ag_score_summary(session: Session, user_id: int) -> dict | None:
    statement = (
        select(
            Score.brain_categories.label("brain_categories"),
            Score.brain_branches.label("brain_branches"),
        )
        .where(Score.user_id == user_id)
        .order_by(Score.edited_time.desc())
        .limit(1)
    )
    row = session.execute(statement).mappings().first()
    return dict(row) if row else None


def get_result_state(session: Session, user_id: int) -> dict | None:
    statement = (
        select(
            ResultState.t_state.label("t_state"),
            ResultState.r_state.label("r_state"),
            ResultState.e_state.label("e_state"),
            ResultState.a_state.label("a_state"),
            ResultState.m_state.label("m_state"),
            ResultState.f_state.label("f_state"),
            ResultState.i_state.label("i_state"),
            ResultState.edited_time.label("edited_time"),
        )
        .where(ResultState.user_id == user_id)
        .limit(1)
    )
    row = session.execute(statement).mappings().first()
    return dict(row) if row else None


def list_student_notifications(session: Session, user_id: int, role: str, limit: int = 10) -> list[dict]:
    statement = (
        select(
            Notification.title.label("title"),
            Notification.description.label("description"),
            Notification.added_by.label("added_by"),
            Notification.priority.label("priority"),
            Notification.persian_date.label("persian_date"),
            Notification.full_text.label("fullText"),
            Notification.created_time.label("created_time"),
        )
        .where(or_(Notification.user_id == user_id, Notification.roles.like(f"%{role}%")))
        .order_by(Notification.created_time.desc())
        .limit(limit)
    )
    return [dict(row) for row in session.execute(statement).mappings().all()]


def get_quiz_setting(session: Session, owner_user_id: int | None, quiz_id: int) -> dict | None:
    if owner_user_id is None:
        return None
    statement = (
        select(
            Setting.description.label("description"),
            Setting.voice.label("voice"),
        )
        .where(
            Setting.user_id == owner_user_id,
            Setting.quiz_id == quiz_id,
        )
        .limit(1)
    )
    row = session.execute(statement).mappings().first()
    return dict(row) if row else None


def update_student_name(session: Session, user_id: int, first_name: str, last_name: str) -> int:
    student = session.get(Student, user_id)
    if not student:
        return 0
    student.first_name = first_name
    student.last_name = last_name
    student.edited_time = datetime.now()
    session.flush()
    return 1


def update_user_password(session: Session, user_id: int, encrypted_password: str) -> int:
    user = session.get(User, user_id)
    if not user:
        return 0
    user.password = encrypted_password
    user.edited_time = datetime.now()
    session.flush()
    return 1


def create_redis_log(session: Session, user_id: int, kind: str, result: str, phone: str | None) -> bool:
    session.add(RedisLog(user_id=user_id, kind=kind, result=result, status=0, phone=phone))
    session.flush()
    return True
