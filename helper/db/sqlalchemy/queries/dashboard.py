from __future__ import annotations

from typing import Literal

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from helper.db.sqlalchemy.models import (
    CapacityPackage,
    Consultant,
    Notification,
    NotificationRead,
    QuizAttempt,
    Student,
    StudentPackageAccess,
)

StudentScope = Literal["owner", "consultant"]


def _student_scope_column(scope: StudentScope):
    if scope == "owner":
        return Student.owner_user_id
    if scope == "consultant":
        return Student.consultant_user_id
    raise ValueError(f"Unsupported student scope: {scope}")


def _package_access_scope_column(scope: StudentScope):
    if scope == "owner":
        return StudentPackageAccess.owner_user_id
    if scope == "consultant":
        return StudentPackageAccess.consultant_user_id
    raise ValueError(f"Unsupported student package access scope: {scope}")


def _quiz_scope_column(scope: StudentScope):
    if scope == "owner":
        return QuizAttempt.owner_user_id
    if scope == "consultant":
        return QuizAttempt.consultant_user_id
    raise ValueError(f"Unsupported quiz scope: {scope}")


def list_capacity_packages_for_user(session: Session, user_id: int) -> list[dict]:
    statement = (
        select(
            CapacityPackage.package_name.label("package_name"),
            CapacityPackage.allowed.label("allowed"),
            CapacityPackage.used.label("used"),
        )
        .where(CapacityPackage.user_id == user_id)
        .order_by(CapacityPackage.package_name.asc())
    )
    return [dict(row) for row in session.execute(statement).mappings().all()]


def count_students_for_scope(session: Session, scope: StudentScope, user_id: int) -> int:
    statement = select(func.count()).select_from(Student).where(_student_scope_column(scope) == user_id)
    return int(session.execute(statement).scalar_one() or 0)


def count_consultants_for_owner(session: Session, owner_user_id: int) -> int:
    statement = select(func.count()).select_from(Consultant).where(Consultant.owner_user_id == owner_user_id)
    return int(session.execute(statement).scalar_one() or 0)


def count_student_packages_for_scope(session: Session, scope: StudentScope, user_id: int) -> dict[str, int]:
    statement = (
        select(
            StudentPackageAccess.package_name.label("package_name"),
            func.count().label("total"),
        )
        .where(_package_access_scope_column(scope) == user_id)
        .where(StudentPackageAccess.permission == 1)
        .group_by(StudentPackageAccess.package_name)
    )
    return {
        row["package_name"]: int(row["total"] or 0)
        for row in session.execute(statement).mappings().all()
        if row["package_name"]
    }


def list_quiz_attempts_for_scope(session: Session, scope: StudentScope, user_id: int) -> list[dict]:
    statement = (
        select(
            QuizAttempt.user_id.label("user_id"),
            QuizAttempt.quiz_kind.label("quiz_kind"),
            QuizAttempt.quiz_id.label("quiz_id"),
            QuizAttempt.state.label("state"),
        )
        .where(_quiz_scope_column(scope) == user_id)
        .order_by(QuizAttempt.user_id.asc(), QuizAttempt.quiz_kind.asc(), QuizAttempt.quiz_id.asc())
    )
    return [dict(row) for row in session.execute(statement).mappings().all()]


def get_consultant_owner_user_id(session: Session, consultant_user_id: int) -> int | None:
    statement = select(Consultant.owner_user_id).where(Consultant.user_id == consultant_user_id)
    return session.execute(statement).scalar_one_or_none()


def list_notifications_for_user(session: Session, user_id: int, role_terms: list[str]) -> list[dict]:
    read_exists = exists().where(
        NotificationRead.notification_id == Notification.id,
        NotificationRead.user_id == user_id,
    )
    role_conditions = [Notification.roles.like(f"%{role}%") for role in role_terms]

    statement = (
        select(
            Notification.id.label("id"),
            Notification.title.label("title"),
            Notification.description.label("description"),
            Notification.added_by.label("added_by"),
            Notification.priority.label("priority"),
            Notification.full_text.label("fullText"),
            Notification.persian_date.label("persian_date"),
            read_exists.label("is_read"),
        )
        .where(or_(Notification.user_id == user_id, Notification.roles.like("%all%"), *role_conditions))
        .order_by(Notification.created_time.desc())
    )

    return [
        {**dict(row), "is_read": 1 if row["is_read"] else 0}
        for row in session.execute(statement).mappings().all()
    ]
