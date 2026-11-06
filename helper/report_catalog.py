from __future__ import annotations

from collections.abc import Callable
from typing import Any

from helper.constants import PSY_PACKAGE_TITLES


REPORT_STATUS_MESSAGES = {
    "ready": "کارنامه آماده دریافت است.",
    "access_denied": "شما به این محصول دسترسی ندارید.",
    "report_access_denied": "دسترسی دریافت کارنامه برای شما فعال نشده است.",
    "quiz_incomplete": "برای دریافت کارنامه، ابتدا همه آزمون‌های این مجموعه را کامل کنید.",
    "queued": "کارنامه در صف تولید قرار دارد.",
    "generating": "کارنامه در حال تولید است. لطفا کمی صبور باشید.",
    "preparing": "تولید کارنامه تمام شده و فایل در حال آماده‌سازی است.",
    "failed": "تولید کارنامه با خطا روبه‌رو شده است. لطفا با پشتیبانی در ارتباط باشید.",
    "not_requested": "آزمون‌ها کامل شده‌اند، اما درخواست تولید کارنامه ثبت نشده است.",
    "not_available": "تولید این کارنامه هنوز در سامانه فعال نشده است.",
}


CORE_REPORT_PRODUCTS = {
    "AG": {
        "title": "کارنامه رغبت و توان",
        "subtitle": "کارنامه‌های مرتبط با ذره‌بین",
        "description": "نتایج شخصیت‌شناسی، استعدادسنجی و هدایت تحصیلی و شغلی.",
        "icon": "school",
        "color": "#018790",
        "reports": [
            {
                "id": "ag-first-report",
                "title": "شخصیت‌شناسی و استعدادسنجی",
                "icon": "psychology",
                "download_action": "get_ag_first_pdf",
                "file_name": "Report1.pdf",
                "download_name": "شخصیت‌شناسی.pdf",
            },
            {
                "id": "ag-second-report",
                "title": "هدایت تحصیلی و شغلی",
                "icon": "school",
                "download_action": "get_ag_second_pdf",
                "file_name": "Report2.pdf",
                "download_name": "هدایت‌تحصیلی.pdf",
            },
        ],
    },
    "SCL": {
        "title": "کارنامه دوپامین تحصیلی",
        "subtitle": "کارنامه‌های مرتبط با دوپامین",
        "description": "نتایج آسیب‌شناسی تحصیلی و الگوی مطالعه.",
        "icon": "brain",
        "color": "#76153C",
        "reports": [
            {
                "id": "scl-first-report",
                "title": "آسیب‌شناسی تحصیلی",
                "icon": "psychology",
                "download_action": "get_scl_first_pdf",
                "file_name": "Report3.pdf",
                "download_name": "آسیب‌شناسی.pdf",
            },
            {
                "id": "scl-second-report",
                "title": "سبک مطالعاتی",
                "icon": "book",
                "download_action": "get_scl_second_pdf",
                "file_name": "Report4.pdf",
                "download_name": "مطالعاتی.pdf",
            },
        ],
    },
}

ADVISOR_REPORTS = {
    "SCL": [
        {
            "id": "scl-third-report",
            "title": "اجمالی (ویژه مشاور)",
            "icon": "advisor",
            "download_action": "get_scl_third_pdf",
            "file_name": "Report5.pdf",
            "download_name": "اجمالی.pdf",
        }
    ],
}


def _access_values(access: dict[str, Any], package_name: str) -> tuple[int, int]:
    package_access = access.get(package_name, {})
    if isinstance(package_access, dict):
        return (
            int(package_access.get("permission") or 0),
            int(package_access.get("limit") or 0),
        )
    if isinstance(package_access, bool):
        value = 1 if package_access else 0
        return value, value
    try:
        value = int(package_access or 0)
    except (TypeError, ValueError):
        value = 0
    return value, value


def _base_status(
    permission: int,
    report_permission: int,
    completed_quizzes: int,
    quiz_count: int,
    queue_status: int | None,
) -> str:
    if permission != 1:
        return "access_denied"
    if report_permission != 1:
        return "report_access_denied"
    if completed_quizzes < quiz_count:
        return "quiz_incomplete"
    if queue_status == 0:
        return "queued"
    if queue_status == 1:
        return "generating"
    if queue_status == 2:
        return "preparing"
    if queue_status == 3:
        return "failed"
    return "not_requested"


def _product_status(report_statuses: list[str], fallback: str) -> str:
    if report_statuses and all(status == "ready" for status in report_statuses):
        return "ready"
    for status in (
        "generating",
        "queued",
        "preparing",
        "failed",
        "quiz_incomplete",
        "report_access_denied",
        "access_denied",
        "not_requested",
        "not_available",
    ):
        if status in report_statuses:
            return status
    return fallback


def build_student_report_catalog(
    access: dict[str, Any],
    quiz_counts: dict[str, int],
    attempts_by_package: dict[str, list[dict[str, Any]]],
    queue_statuses: dict[str, int | None],
    file_available: Callable[[str, str], bool],
    include_advisor_reports: bool = False,
    product_filter: str | None = None,
) -> dict[str, Any]:
    products = []
    requested_product = str(product_filter or "").strip().upper()

    for package_name, definition in CORE_REPORT_PRODUCTS.items():
        if requested_product and requested_product != package_name:
            continue
        permission, report_permission = _access_values(access, package_name)
        quiz_count = int(quiz_counts.get(package_name) or 0)
        completed_quizzes = sum(
            1 for attempt in attempts_by_package.get(package_name, []) if int(attempt.get("state") or 0) == 2
        )
        base_status = _base_status(
            permission,
            report_permission,
            completed_quizzes,
            quiz_count,
            queue_statuses.get(package_name),
        )
        reports = []
        report_definitions = list(definition["reports"])
        if include_advisor_reports:
            report_definitions.extend(ADVISOR_REPORTS.get(package_name, []))

        for report_definition in report_definitions:
            report_status = base_status
            if (
                permission == 1
                and report_permission == 1
                and completed_quizzes >= quiz_count
                and file_available(package_name, report_definition["file_name"])
            ):
                report_status = "ready"
            reports.append(
                {
                    **report_definition,
                    "package_name": package_name,
                    "status": report_status,
                    "status_message": REPORT_STATUS_MESSAGES[report_status],
                    "can_download": report_status == "ready",
                }
            )

        status = _product_status(
            [report["status"] for report in reports],
            base_status,
        )
        products.append(
            {
                "code": package_name,
                **{key: value for key, value in definition.items() if key != "reports"},
                "permission": permission,
                "report_permission": report_permission,
                "quiz_count": quiz_count,
                "completed_quizzes": completed_quizzes,
                "status": status,
                "status_message": REPORT_STATUS_MESSAGES[status],
                "reports": reports,
            }
        )

    psy_reports = []
    psy_permissions = []
    for package_name in sorted(access):
        if not package_name.startswith("PSY_"):
            continue
        if requested_product and requested_product not in {"PSY", package_name}:
            continue
        permission, report_permission = _access_values(access, package_name)
        if permission != 1:
            continue
        psy_permissions.append(report_permission)
        quiz_count = int(quiz_counts.get(package_name) or 0)
        completed_quizzes = sum(
            1 for attempt in attempts_by_package.get(package_name, []) if int(attempt.get("state") or 0) == 2
        )
        status = _base_status(
            permission,
            report_permission,
            completed_quizzes,
            quiz_count,
            queue_statuses.get(package_name),
        )
        if status not in {
            "report_access_denied",
            "quiz_incomplete",
            "queued",
            "generating",
            "failed",
        }:
            status = "not_available"
        psy_reports.append(
            {
                "id": f"{package_name.lower()}-report",
                "title": f"کارنامه {PSY_PACKAGE_TITLES.get(package_name, package_name)}",
                "icon": "psychology",
                "package_name": package_name,
                "download_action": None,
                "file_name": None,
                "download_name": None,
                "status": status,
                "status_message": REPORT_STATUS_MESSAGES[status],
                "can_download": False,
            }
        )

    if psy_reports:
        status = _product_status(
            [report["status"] for report in psy_reports],
            "not_available",
        )
        products.append(
            {
                "code": "PSY",
                "title": "کارنامه‌های روان‌شناسی",
                "subtitle": "کارنامه‌های بسته‌های PSY",
                "description": "وضعیت کارنامه آزمون‌های روان‌شناسی فعال شما.",
                "icon": "psychology",
                "color": "#5B3FD6",
                "permission": 1,
                "report_permission": 1 if any(psy_permissions) else 0,
                "quiz_count": sum(int(quiz_counts.get(report["package_name"]) or 0) for report in psy_reports),
                "completed_quizzes": sum(
                    1
                    for package_name in attempts_by_package
                    if package_name.startswith("PSY_")
                    for attempt in attempts_by_package[package_name]
                    if int(attempt.get("state") or 0) == 2
                ),
                "status": status,
                "status_message": REPORT_STATUS_MESSAGES[status],
                "reports": psy_reports,
            }
        )

    return {"products": products}
