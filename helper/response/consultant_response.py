from __future__ import annotations

from typing import Any


def build_consultant_list_response(consultants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    responses = []
    for consultant in consultants:
        first_name = consultant.get("first_name") or ""
        last_name = consultant.get("last_name") or ""

        responses.append(
            {
                "con_id": consultant.get("con_id"),
                "user_id": consultant.get("user_id"),
                "phone": consultant.get("phone"),
                "first_name": consultant.get("first_name"),
                "last_name": consultant.get("last_name"),
                "sex": consultant.get("sex"),
                "full_name": f"{first_name} {last_name}".strip(),
                "password": None,
            }
        )
    return responses
