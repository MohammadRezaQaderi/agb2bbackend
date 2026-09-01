from __future__ import annotations

import json
from typing import Any

from helper.response.password_response import build_display_password


def build_student_list_response(
    students: list[dict[str, Any]],
    default_con_name: str = "",
    default_con_id: int | None = None,
) -> list[dict[str, Any]]:
    responses = []
    for stu in students:
        first_name = stu.get("first_name") or ""
        last_name = stu.get("last_name") or ""
        consultant_first_name = stu.get("consultant_first_name") or ""
        consultant_last_name = stu.get("consultant_last_name") or ""
        con_name = f"{consultant_first_name} {consultant_last_name}".strip() or default_con_name

        raw_access = stu.get("access") or "{}"
        try:
            access_data = json.loads(raw_access) if isinstance(raw_access, str) else (raw_access or {})
        except (json.JSONDecodeError, TypeError):
            access_data = {}

        responses.append(
            {
                "stu_id": stu.get("stu_id"),
                "user_id": stu.get("user_id"),
                "phone": stu.get("phone"),
                "first_name": stu.get("first_name"),
                "last_name": stu.get("last_name"),
                "con_name": con_name,
                "con_id": stu.get("con_id") or default_con_id,
                "password": build_display_password(stu.get("password")),
                "sex": stu.get("sex"),
                "city": stu.get("city"),
                "full_name": f"{first_name} {last_name}".strip(),
                "birth_date": stu.get("birth_date"),
                "access": access_data,
            }
        )
    return responses
