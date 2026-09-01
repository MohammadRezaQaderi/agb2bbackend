from __future__ import annotations

import json
from typing import Any

from helper.response.password_response import build_display_password


def _safe_access(raw_access: Any) -> dict[str, Any]:
    try:
        return json.loads(raw_access) if isinstance(raw_access, str) else (raw_access or {})
    except (json.JSONDecodeError, TypeError):
        return {}


def build_student_report_response(
    students: list[dict[str, Any]],
    include_consultant_name: bool = False,
) -> list[dict[str, Any]]:
    responses = []
    for stu in students:
        first_name = stu.get("first_name") or ""
        last_name = stu.get("last_name") or ""
        response = {
            "id": stu.get("stu_id"),
            "student_id": stu.get("user_id"),
            "phone": stu.get("phone"),
            "first_name": stu.get("first_name"),
            "last_name": stu.get("last_name"),
            "password": build_display_password(stu.get("password")),
            "sex": stu.get("sex"),
            "city": stu.get("city"),
            "access": _safe_access(stu.get("access")),
            "full_name": f"{first_name} {last_name}".strip(),
            "consultant_comment": stu.get("comment"),
            "report_id": stu.get("user_id"),
        }

        if include_consultant_name:
            consultant_first_name = stu.get("consultant_first_name") or ""
            consultant_last_name = stu.get("consultant_last_name") or ""
            response["con_name"] = f"{consultant_first_name} {consultant_last_name}".strip()

        responses.append(response)
    return responses


def _permission_from_package_info(package_info: Any) -> int:
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


def _latest_attempts_by_student_package(quiz_attempts: list[dict[str, Any]]) -> dict[tuple[int, str], dict[str, Any]]:
    latest_attempts = {}
    for attempt in quiz_attempts:
        latest_attempts[(attempt.get("user_id"), attempt.get("quiz_kind"))] = attempt
    return latest_attempts


def build_student_management_report_response(
    students: list[dict[str, Any]],
    quiz_attempts: list[dict[str, Any]],
    packages_data: dict[str, Any],
    get_quiz_name,
    include_consultant_name: bool = False,
    package_quiz_count: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    package_quiz_count = package_quiz_count or {"AG": 7, "SCL": 4}
    latest_attempts = _latest_attempts_by_student_package(quiz_attempts)
    responses = []

    for stu in students:
        access_data = _safe_access(stu.get("access"))
        access_state = {}

        for package_name in packages_data.keys():
            package_info = access_data.get(package_name, {})
            permission = _permission_from_package_info(package_info)
            state = "-"
            last_quiz_id = 0

            if permission == 1:
                total_quizzes = package_quiz_count.get(package_name)
                if total_quizzes:
                    last_quiz_id = 1
                    latest_attempt = latest_attempts.get((stu.get("user_id"), package_name))
                    if not latest_attempt:
                        state = "not-started"
                    else:
                        last_state = latest_attempt.get("state")
                        last_quiz_id = latest_attempt.get("quiz_id")
                        if last_state == 2 and last_quiz_id == total_quizzes:
                            state = "completed"
                        else:
                            state = "in-progress"

            access_state[package_name] = {
                "permission": permission,
                "state": state,
                "current_quiz_name": get_quiz_name(package_name, last_quiz_id),
            }

        first_name = stu.get("first_name") or ""
        last_name = stu.get("last_name") or ""
        response = {
            "student_id": stu.get("user_id"),
            "first_name": stu.get("first_name"),
            "last_name": stu.get("last_name"),
            "full_name": f"{first_name} {last_name}".strip(),
            "access": access_data,
            "access_state": access_state,
        }

        if include_consultant_name:
            consultant_first_name = stu.get("consultant_first_name") or ""
            consultant_last_name = stu.get("consultant_last_name") or ""
            response["con_name"] = f"{consultant_first_name} {consultant_last_name}".strip()

        responses.append(response)

    return responses
