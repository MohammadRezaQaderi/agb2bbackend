from __future__ import annotations

import json
import os
from typing import Any

import helper.file_helper as file_helper
from config import REPORTS_DIR
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.report_downloads import (
    get_latest_report_queue_status,
)
from helper.db.sqlalchemy.queries.reports import list_quiz_attempts_for_users
from helper.db.sqlalchemy.queries.students import (
    list_student_package_access_for_users,
)
from helper.quiz.quiz_data_extractor import get_package_quiz_counts
from helper.report_catalog import build_student_report_catalog


def _parse_access(raw_access: Any) -> dict[str, Any]:
    if isinstance(raw_access, dict):
        return dict(raw_access)
    if isinstance(raw_access, str):
        try:
            parsed = json.loads(raw_access)
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, json.JSONDecodeError):
            return {}
    return {}


def load_student_report_catalog(
    user_id: int,
    phone: str,
    raw_access: Any,
    *,
    include_advisor_reports: bool = False,
    package_name: str | None = None,
) -> dict[str, Any]:
    access = _parse_access(raw_access)
    requested_package = str(package_name or "").strip().upper()

    with session_scope() as session:
        normalized_access = list_student_package_access_for_users(
            session=session,
            user_ids=[user_id],
        ).get(user_id, {})
        access.update(normalized_access)

        psy_package_names = [
            package_name
            for package_name, package_access in access.items()
            if package_name.startswith("PSY_")
            and isinstance(package_access, dict)
            and int(package_access.get("permission") or 0) == 1
        ]
        if requested_package in {"AG", "SCL"}:
            package_names = [requested_package]
        elif requested_package == "PSY":
            package_names = psy_package_names
        elif requested_package.startswith("PSY_"):
            package_names = [requested_package]
        elif requested_package:
            package_names = []
        else:
            package_names = ["AG", "SCL", *psy_package_names]
        package_names = list(dict.fromkeys(package_names))
        attempts = list_quiz_attempts_for_users(
            session=session,
            user_ids=[user_id],
            package_names=package_names,
        )
        queue_statuses = {}
        for package_name in package_names:
            queue_info = get_latest_report_queue_status(
                session=session,
                user_id=user_id,
                kind=package_name,
            )
            queue_statuses[package_name] = queue_info.get("status") if queue_info else None

    attempts_by_package = {package_name: [] for package_name in package_names}
    for attempt in attempts:
        package_name = str(attempt.get("quiz_kind") or "").upper()
        if package_name in attempts_by_package:
            attempts_by_package[package_name].append(attempt)

    quiz_counts = get_package_quiz_counts(package_names)
    normalized_phone = file_helper.normalize_storage_filename(phone)
    report_directory = file_helper.safe_storage_path(
        REPORTS_DIR,
        normalized_phone,
    )

    def _file_available(_package_name: str, file_name: str) -> bool:
        try:
            return os.path.isfile(file_helper.safe_storage_path(report_directory, file_name))
        except file_helper.FileValidationError:
            return False

    return build_student_report_catalog(
        access=access,
        quiz_counts=quiz_counts,
        attempts_by_package=attempts_by_package,
        queue_statuses=queue_statuses,
        file_available=_file_available,
        include_advisor_reports=include_advisor_reports,
        product_filter=requested_package,
    )
