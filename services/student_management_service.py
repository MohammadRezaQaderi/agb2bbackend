from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.students import (
    get_student_access_for_relation,
    list_student_options,
)
from helper.service_errors import service_exception_error_logging
from helper.tracking import get_tracking_code
from services.student.student_service import load_student_dashboard_data

def _scope_for_role(role):
    if role in {"ins", "sch"}:
        return "owner"
    if role in {"con", "ocon"}:
        return "consultant"
    return None


def get_student_options(request_data, user_info):
    try:
        scope = _scope_for_role(user_info.get("role"))
        if not scope:
            return None, None, "شما به فهرست دانش‌آموزان دسترسی ندارید."

        with session_scope() as session:
            students = list_student_options(
                session=session,
                scope=scope,
                user_id=int(user_info["user_id"]),
            )
        return get_tracking_code(), students, ""
    except Exception as exc:
        service_exception_error_logging(
            "ag_api/management",
            "get_student_options",
            str(exc),
            request_data,
            user_info,
        )
        return None, None, "فهرست دانش‌آموزان دریافت نشد."


def get_student_management(request_data, user_info):
    try:
        student_id = int(request_data["student_id"])
        with session_scope() as session:
            relation = get_student_access_for_relation(
                session=session,
                stu_user_id=student_id,
            )

        if not relation:
            return None, None, "دانش‌آموز یافت نشد."

        role = user_info.get("role")
        current_user_id = int(user_info["user_id"])
        if role in {"ins", "sch"}:
            has_access = relation.get("owner_user_id") == current_user_id
        elif role in {"con", "ocon"}:
            has_access = relation.get("consultant_user_id") == current_user_id
        else:
            has_access = False

        if not has_access:
            return None, None, "شما به این دانش‌آموز دسترسی ندارید."

        dashboard = load_student_dashboard_data(
            student_id,
            include_notifications=False,
            include_student_info=True,
        )
        return get_tracking_code(), dashboard, ""
    except Exception as exc:
        service_exception_error_logging(
            "ag_api/management",
            "get_student_management",
            str(exc),
            request_data,
            user_info,
        )
        return None, None, "اطلاعات مدیریتی دانش‌آموز دریافت نشد."
