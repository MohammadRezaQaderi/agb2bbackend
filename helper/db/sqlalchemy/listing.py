from __future__ import annotations

import json

from sqlalchemy.orm import Session

from helper.db.sqlalchemy.filters import ConsultantFilters, StudentFilters
from helper.db.sqlalchemy.pagination import Page, is_paginated_request, page_payload
from helper.db.sqlalchemy.queries.consultants import (
    list_consultants_for_owner,
    paginate_consultants_for_owner,
)
from helper.db.sqlalchemy.queries.students import (
    list_student_package_access_for_users,
    list_students,
    paginate_students,
)


def attach_normalized_student_access(session: Session, students: list[dict]) -> list[dict]:
    user_ids = [int(student["user_id"]) for student in students if student.get("user_id") is not None]
    normalized_access = list_student_package_access_for_users(session=session, user_ids=user_ids)

    for student in students:
        user_id = student.get("user_id")
        if user_id is None:
            continue
        raw_access = student.get("access") or {}
        user_access = normalized_access.get(int(user_id), {})
        if not raw_access and not user_access:
            continue
        if isinstance(raw_access, str):
            try:
                access = json.loads(raw_access)
            except (TypeError, json.JSONDecodeError):
                access = {}
        elif isinstance(raw_access, dict):
            access = dict(raw_access)
        else:
            access = {}

        access.update(user_access)
        student["access"] = access
    return students


def fetch_students_for_request(
    session: Session,
    scope: str,
    user_id: int,
    request_data: dict | None,
) -> tuple[list[dict], Page | None]:
    request_data = request_data or {}
    filters = StudentFilters.from_request(request_data)
    query_options = {
        "session": session,
        "scope": scope,
        "user_id": user_id,
        "filters": filters,
        "sort_by": request_data.get("sort_by"),
        "sort_direction": request_data.get("sort_direction"),
    }
    if not is_paginated_request(request_data):
        return attach_normalized_student_access(session, list_students(**query_options)), None

    page = paginate_students(
        **query_options,
        page=request_data.get("page"),
        page_size=request_data.get("page_size"),
    )
    return attach_normalized_student_access(session, page.items), page


def fetch_consultants_for_request(
    session: Session,
    owner_user_id: int,
    request_data: dict | None,
) -> tuple[list[dict], Page | None]:
    request_data = request_data or {}
    filters = ConsultantFilters.from_request(request_data)
    query_options = {
        "session": session,
        "owner_user_id": owner_user_id,
        "filters": filters,
        "sort_by": request_data.get("sort_by"),
        "sort_direction": request_data.get("sort_direction"),
    }
    if not is_paginated_request(request_data):
        return list_consultants_for_owner(**query_options), None

    page = paginate_consultants_for_owner(
        **query_options,
        page=request_data.get("page"),
        page_size=request_data.get("page_size"),
    )
    return page.items, page


def with_page_metadata(page: Page | None, items: list[dict]) -> list[dict] | dict:
    if page is None:
        return items
    return page_payload(page, items)
