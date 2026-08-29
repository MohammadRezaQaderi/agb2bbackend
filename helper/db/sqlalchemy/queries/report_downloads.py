from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from helper.db.sqlalchemy.models import QuizAttempt, RedisLog, Student, User


def _access_permission(access_data: dict, package_name: str) -> int:
    package_info = access_data.get(package_name, {})
    if isinstance(package_info, dict):
        return int(package_info.get("permission") or 0)
    if isinstance(package_info, bool):
        return 1 if package_info else 0
    if isinstance(package_info, (int, float, str)):
        try:
            return int(package_info) if str(package_info).strip() != "" else 0
        except ValueError:
            return 0
    return 0


def get_report_download_status(session: Session, phone: str, kind: str, expected_quiz_count: int) -> dict:
    student = session.execute(
        select(
            Student.user_id.label("user_id"),
            Student.access.label("access"),
        )
        .join(User, User.user_id == Student.user_id)
        .where(User.phone == phone)
        .limit(1)
    ).mappings().first()
    if not student:
        return {"status": "student_not_found"}

    try:
        access_data = json.loads(student["access"] or "{}")
    except (json.JSONDecodeError, TypeError):
        access_data = {}

    if _access_permission(access_data, kind) != 1:
        return {"status": "access_denied", "user_id": student["user_id"]}

    attempts = session.execute(
        select(
            QuizAttempt.quiz_id.label("quiz_id"),
            QuizAttempt.state.label("state"),
        )
        .where(QuizAttempt.user_id == student["user_id"], QuizAttempt.quiz_kind == kind)
        .order_by(QuizAttempt.quiz_id.asc())
    ).mappings().all()
    if len(attempts) < expected_quiz_count or any(attempt["state"] != 2 for attempt in attempts):
        return {"status": "quiz_incomplete", "user_id": student["user_id"]}

    queue = session.execute(
        select(RedisLog.status)
        .where(RedisLog.user_id == student["user_id"], RedisLog.kind == kind)
        .order_by(RedisLog.created_time.desc())
        .limit(1)
    ).scalar_one_or_none()
    if queue == 1:
        return {"status": "generating", "user_id": student["user_id"]}
    if queue == 0:
        return {"status": "queued", "user_id": student["user_id"]}

    return {"status": "ready", "user_id": student["user_id"]}
