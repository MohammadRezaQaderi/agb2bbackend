from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from helper.db.sqlalchemy.models import (
    QuizAttempt,
    RedisLog,
    Student,
    StudentPackageAccess,
    User,
)


def _access_values(access_data: dict, package_name: str) -> tuple[int, int]:
    package_info = access_data.get(package_name, {})
    if isinstance(package_info, dict):
        return (
            int(package_info.get("permission") or 0),
            int(package_info.get("limit") or 0),
        )
    if isinstance(package_info, bool):
        value = 1 if package_info else 0
        return value, value
    if isinstance(package_info, (int, float, str)):
        try:
            value = int(package_info) if str(package_info).strip() != "" else 0
            return value, value
        except ValueError:
            return 0, 0
    return 0, 0


def get_latest_report_queue_status(
    session: Session,
    user_id: int,
    kind: str,
) -> dict | None:
    row = (
        session.execute(
            select(
                RedisLog.status.label("status"),
                RedisLog.result.label("result"),
                RedisLog.created_time.label("created_time"),
            )
            .where(
                RedisLog.user_id == user_id,
                RedisLog.kind == kind.upper(),
            )
            .order_by(RedisLog.created_time.desc())
            .limit(1)
        )
        .mappings()
        .first()
    )
    return dict(row) if row else None


def get_report_download_status(session: Session, phone: str, kind: str, expected_quiz_count: int) -> dict:
    student = (
        session.execute(
            select(
                Student.user_id.label("user_id"),
                Student.access.label("access"),
            )
            .join(User, User.user_id == Student.user_id)
            .where(User.phone == phone)
            .limit(1)
        )
        .mappings()
        .first()
    )
    if not student:
        return {"status": "student_not_found"}

    try:
        access_data = json.loads(student["access"] or "{}")
    except (json.JSONDecodeError, TypeError):
        access_data = {}

    normalized_access = (
        session.execute(
            select(
                StudentPackageAccess.permission.label("permission"),
                StudentPackageAccess.limit.label("limit"),
            )
            .where(
                StudentPackageAccess.stu_user_id == student["user_id"],
                StudentPackageAccess.package_name == kind,
            )
            .limit(1)
        )
        .mappings()
        .first()
    )
    if normalized_access:
        permission = int(normalized_access["permission"] or 0)
        report_permission = int(normalized_access["limit"] or 0)
    else:
        permission, report_permission = _access_values(access_data, kind)

    if permission != 1 or report_permission != 1:
        return {"status": "access_denied", "user_id": student["user_id"]}

    attempts = (
        session.execute(
            select(
                QuizAttempt.quiz_id.label("quiz_id"),
                QuizAttempt.state.label("state"),
            )
            .where(QuizAttempt.user_id == student["user_id"], QuizAttempt.quiz_kind == kind)
            .order_by(QuizAttempt.quiz_id.asc())
        )
        .mappings()
        .all()
    )
    if len(attempts) < expected_quiz_count or any(attempt["state"] != 2 for attempt in attempts):
        return {"status": "quiz_incomplete", "user_id": student["user_id"]}

    queue_info = get_latest_report_queue_status(
        session=session,
        user_id=student["user_id"],
        kind=kind,
    )
    queue = queue_info.get("status") if queue_info else None
    if queue == 1:
        return {"status": "generating", "user_id": student["user_id"]}
    if queue == 0:
        return {"status": "queued", "user_id": student["user_id"]}

    return {"status": "ready", "user_id": student["user_id"]}
