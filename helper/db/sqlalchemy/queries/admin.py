from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from helper.db.sqlalchemy.models import (
    Capacity,
    CapacityLog,
    CapacityPackage,
    Consultant,
    Institute,
    OwnerConsultant,
    QuizAttempt,
    QuizQuestionAnswer,
    School,
    Student,
    User,
)


def _decode_answer_value(value: Any) -> Any:
    if value is None:
        return []
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        if "," in value:
            return [item for item in value.split(",") if item != ""]
        return [value] if value != "" else []


def _capacity_info(session: Session, user_id: int) -> dict:
    statement = (
        select(
            CapacityPackage.package_name.label("package_name"),
            CapacityPackage.allowed.label("allowed"),
            CapacityPackage.used.label("used"),
        )
        .where(CapacityPackage.user_id == user_id)
        .order_by(CapacityPackage.package_name.asc())
    )
    return {
        row["package_name"]: {"allowed": row["allowed"], "used": row["used"]}
        for row in session.execute(statement).mappings().all()
        if row["package_name"]
    }


def add_capacity_to_user(session: Session, user_id: int, package_name: str, count: int) -> dict[str, int]:
    capacity = session.execute(
        select(Capacity).where(Capacity.user_id == user_id).limit(1)
    ).scalars().first()
    if not capacity:
        capacity = Capacity(user_id=user_id)
        session.add(capacity)
        session.flush()

    capacity_package = session.execute(
        select(CapacityPackage)
        .where(
            CapacityPackage.user_id == user_id,
            CapacityPackage.package_name == package_name,
        )
        .limit(1)
    ).scalars().first()

    if capacity_package:
        current_used = capacity_package.used or 0
        current_total_allowed = capacity_package.total_allowed
        if current_total_allowed is None:
            current_total_allowed = (capacity_package.allowed or 0) + current_used

        capacity_package.allowed = (capacity_package.allowed or 0) + count
        capacity_package.total_allowed = current_total_allowed + count
        capacity_package.edited_time = datetime.now()
    else:
        current_used = 0
        capacity_package = CapacityPackage(
            capacity_id=capacity.capacity_id,
            user_id=user_id,
            package_name=package_name,
            total_allowed=count,
            allowed=count,
            used=0,
        )
        session.add(capacity_package)

    session.flush()
    session.add(
        CapacityLog(
            user_id=user_id,
            capacity_id=capacity.capacity_id,
            capacity_package_id=capacity_package.capacity_package_id,
            package_name=package_name,
            allowed=capacity_package.allowed,
            used=current_used,
            change=count,
        )
    )
    session.flush()

    return {
        row["package_name"]: int(row["allowed"] or 0)
        for row in session.execute(
            select(
                CapacityPackage.package_name.label("package_name"),
                CapacityPackage.allowed.label("allowed"),
            ).where(CapacityPackage.user_id == user_id)
        ).mappings().all()
        if row["package_name"]
    }


def get_user_role_by_phone(session: Session, phone: str) -> dict | None:
    row = session.execute(
        select(
            User.user_id.label("user_id"),
            User.role.label("role"),
        )
        .where(User.phone == phone)
        .limit(1)
    ).mappings().first()
    return dict(row) if row else None


def get_admin_user_info_by_phone(session: Session, phone: str) -> dict | None:
    user = session.execute(
        select(
            User.user_id.label("user_id"),
            User.phone.label("phone"),
            User.role.label("role"),
        )
        .where(User.phone == phone)
        .limit(1)
    ).mappings().first()
    if not user:
        return None

    user_info = dict(user)
    user_id = user_info["user_id"]
    role = user_info.get("role")

    if role == "ins":
        row = session.execute(
            select(
                Institute.ins_id.label("ins_id"),
                Institute.name.label("name"),
                Institute.logo.label("logo"),
                Institute.verify.label("verify"),
            )
            .where(Institute.user_id == user_id)
            .limit(1)
        ).mappings().first()
        if row:
            user_info.update(dict(row))
            user_info["capacity"] = _capacity_info(session, user_id)

    elif role == "sch":
        row = session.execute(
            select(
                School.sch_id.label("sch_id"),
                School.name.label("name"),
                School.logo.label("logo"),
                School.verify.label("verify"),
            )
            .where(School.user_id == user_id)
            .limit(1)
        ).mappings().first()
        if row:
            user_info.update(dict(row))
            user_info["capacity"] = _capacity_info(session, user_id)

    elif role == "ocon":
        row = session.execute(
            select(
                OwnerConsultant.ocon_id.label("ocon_id"),
                OwnerConsultant.first_name.label("first_name"),
                OwnerConsultant.last_name.label("last_name"),
                OwnerConsultant.sex.label("sex"),
                OwnerConsultant.verify.label("verify"),
            )
            .where(OwnerConsultant.user_id == user_id)
            .limit(1)
        ).mappings().first()
        if row:
            user_info.update(dict(row))
            user_info["capacity"] = _capacity_info(session, user_id)

    elif role == "con":
        owner = aliased(User)
        row = session.execute(
            select(
                Consultant.con_id.label("con_id"),
                Consultant.first_name.label("first_name"),
                Consultant.last_name.label("last_name"),
                Consultant.sex.label("sex"),
                Consultant.owner_user_id.label("owner_user_id"),
                owner.role.label("owner_role"),
            )
            .outerjoin(owner, owner.user_id == Consultant.owner_user_id)
            .where(Consultant.user_id == user_id)
            .limit(1)
        ).mappings().first()
        if row:
            user_info.update(dict(row))
            user_info["ins_id"] = row["owner_user_id"]

    elif role == "stu":
        owner = aliased(User)
        row = session.execute(
            select(
                Student.stu_id.label("stu_id"),
                Student.first_name.label("first_name"),
                Student.last_name.label("last_name"),
                Student.sex.label("sex"),
                Student.city.label("city"),
                Student.birth_date.label("birth_date"),
                Student.owner_user_id.label("owner_user_id"),
                Student.consultant_user_id.label("consultant_user_id"),
                owner.role.label("owner_role"),
                Student.access.label("access"),
            )
            .outerjoin(owner, owner.user_id == Student.owner_user_id)
            .where(Student.user_id == user_id)
            .limit(1)
        ).mappings().first()
        if row:
            user_info.update(dict(row))
            user_info["ins_id"] = row["owner_user_id"]
            user_info["con_id"] = row["consultant_user_id"]
            try:
                access_data = json.loads(row["access"] or "{}")
            except (json.JSONDecodeError, TypeError):
                access_data = {}
            user_info["access"] = access_data

    return user_info


def get_student_quiz_answer_info_by_phone(session: Session, phone: str) -> dict | None:
    student = session.execute(
        select(
            Student.user_id.label("user_id"),
            Student.first_name.label("first_name"),
            Student.last_name.label("last_name"),
            Student.access.label("access"),
        )
        .join(User, User.user_id == Student.user_id)
        .where(User.phone == phone)
        .limit(1)
    ).mappings().first()
    if not student:
        return None

    try:
        access_data = json.loads(student["access"] or "{}")
    except (json.JSONDecodeError, TypeError):
        access_data = {}

    attempts = session.execute(
        select(
            QuizAttempt.id.label("id"),
            QuizAttempt.quiz_id.label("quiz_id"),
            QuizAttempt.quiz_kind.label("quiz_kind"),
            QuizAttempt.state.label("state"),
        )
        .where(QuizAttempt.user_id == student["user_id"])
        .order_by(QuizAttempt.quiz_kind.asc(), QuizAttempt.quiz_id.asc())
    ).mappings().all()

    answer_rows = session.execute(
        select(
            QuizQuestionAnswer.attempt_id.label("attempt_id"),
            QuizQuestionAnswer.question_id.label("question_id"),
            QuizQuestionAnswer.answer_value.label("answer_value"),
        )
        .where(QuizQuestionAnswer.user_id == student["user_id"])
        .order_by(QuizQuestionAnswer.question_id.asc())
    ).mappings().all()
    answers_by_attempt: dict[int, dict[str, Any]] = {}
    for answer in answer_rows:
        answers_by_attempt.setdefault(answer["attempt_id"], {})[
            str(answer["question_id"])
        ] = _decode_answer_value(answer["answer_value"])

    return {
        "user_id": student["user_id"],
        "first_name": student["first_name"],
        "last_name": student["last_name"],
        "access": access_data,
        "quiz_attempts": [
            {
                "quiz_id": attempt["quiz_id"],
                "quiz_kind": attempt["quiz_kind"],
                "answers": answers_by_attempt.get(attempt["id"], {}),
                "state": attempt["state"],
            }
            for attempt in attempts
        ],
    }
