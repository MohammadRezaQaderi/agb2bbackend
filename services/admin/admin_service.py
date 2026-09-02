import hashlib
import json
import logging

from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.admin import (
    add_capacity_to_user,
    count_admins,
    create_admin,
    create_admin_log,
    get_active_admin_by_token_hash,
    get_admin_user_info_by_phone,
    get_student_quiz_answer_info_by_phone,
    get_user_role_by_phone,
)
from helper.log_sanitizer import sanitize_log_data
import helper.func_helper as func_helper
from config import DEVELOP_TOKEN


logger = logging.getLogger(__name__)


def _admin_token_hash(token: str) -> str:
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def authenticate_admin_token(token: str | None) -> dict | None:
    if not token:
        return None

    token_hash = _admin_token_hash(token)
    try:
        with session_scope() as session:
            if count_admins(session=session) == 0 and DEVELOP_TOKEN:
                create_admin(
                    session=session,
                    admin_name="develop_admin",
                    token_hash=_admin_token_hash(DEVELOP_TOKEN),
                    created_by="config_seed",
                )
            admin = get_active_admin_by_token_hash(session=session, token_hash=token_hash)
        return admin
    except Exception:
        logger.exception("Admin authentication failed")
        return None


def _json_value(value):
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)


def _response_message(response: dict) -> str:
    if response.get("error"):
        return str(response.get("error"))
    response_body = response.get("response")
    if isinstance(response_body, dict):
        return str(response_body.get("message") or "")
    return ""


def _target_user_id_from_response(response: dict) -> int | None:
    response_body = response.get("response")
    if not isinstance(response_body, dict):
        return None
    data = response_body.get("data")
    if not isinstance(data, dict):
        return None
    value = data.get("user_id") or data.get("student_id")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def log_admin_action(admin_context: dict | None, action_type: str, request_data: dict, response: dict) -> None:
    if not admin_context:
        return

    try:
        with session_scope() as session:
            create_admin_log(
                session=session,
                admin_id=admin_context.get("id"),
                admin_name=admin_context.get("admin_name"),
                action_type=action_type,
                target_phone=request_data.get("phone") if isinstance(request_data, dict) else None,
                target_user_id=_target_user_id_from_response(response),
                request_data=_json_value(sanitize_log_data(request_data)),
                response_status=str(response.get("status") or ""),
                response_message=_response_message(response),
                tracking_code=response.get("tracking_code"),
            )
    except Exception:
        logger.exception("Admin audit logging failed")


def change_capacity(request_data):
    """
    Update capacity with phone number of the user and log the changes.
    """
    try:
        phone = request_data.get("phone")
        kind = request_data.get("kind")
        count = request_data.get("count")

        if not phone:
            return None, None, "شماره تلفن الزامی است."

        if not kind:
            return None, None, "نوع بسته الزامی است."

        kind = kind.upper()
        if kind not in func_helper.PACKAGES_DATA:
            valid_packages = "، ".join(f"{package} ({func_helper.get_kind_name(package)})" for package in func_helper.PACKAGES_DATA.keys())
            return None, None, f"نوع بسته معتبر نیست. بسته‌های معتبر: {valid_packages}"

        if not isinstance(count, int):
            return None, None, "تعداد باید یک عدد صحیح مثبت باشد."

        if count <= 0:
            return None, None, "تعداد باید یک عدد صحیح مثبت باشد."

        package_names = list(func_helper.PACKAGES_DATA.keys())
        capacity_result = {package_name: 0 for package_name in package_names}
        with session_scope() as session:
            user_res = get_user_role_by_phone(session=session, phone=phone)
            if not user_res:
                return None, None, "کاربری با این شماره تلفن یافت نشد."

            user_id = user_res["user_id"]
            role = user_res["role"]
            if role not in ["ins", "sch", "ocon"]:
                return None, None, "نقش کاربر باید ins، sch یا ocon باشد."

            all_packages = add_capacity_to_user(session=session, user_id=user_id, package_name=kind, count=count)

        for pkg_name, allowed in all_packages.items():
            pkg_name = str(pkg_name or "").upper()
            if pkg_name in capacity_result:
                capacity_result[pkg_name] = allowed

        token = func_helper.get_tracking_code()
        return token, {
            "phone": phone,
            "capacity": capacity_result
        }, ""

    except Exception as e:
        func_helper.service_exception_error_logging("ag_api/admin_request", "change_capacity", str(e), request_data, {}
        )
        return None, None, f"خطا در به‌روزرسانی ظرفیت: {str(e)}"


def get_user_info(request_data):
    """
    Get user user_info by phone number.
    
    Requirements:
    - Request data has phone
    - Get information from users and ins, sch, ocon, con, stu tables
    - For ocon, sch, ins return capacity
    - Return user user_info
    """
    try:
        phone = request_data.get("phone")

        if not phone:
            return None, None, "شماره تلفن الزامی است."

        with session_scope() as session:
            user_info = get_admin_user_info_by_phone(session=session, phone=phone)

        if not user_info:
            return None, None, "کاربری با این شماره تلفن یافت نشد."

        token = func_helper.get_tracking_code()
        return token, user_info, ""

    except Exception as e:
        func_helper.service_exception_error_logging("ag_api/admin_request", "get_user_info", str(e), request_data, {}
        )
        return None, None, f"خطا در دریافت اطلاعات کاربر: {str(e)}"


def check_student_quiz_answer(request_data):
    """
    Check student quiz answer and student state.
    
    Requirements:
    - With quiz_attempt and quiz_question_answer tables check student quiz answer
    - Check student state (in stu table with access field for permission and limits)
    - Return object of student quiz answer and student state
    """
    try:
        phone = request_data.get("phone")

        if not phone:
            return None, None, "شماره تلفن الزامی است."

        with session_scope() as session:
            stu_res = get_student_quiz_answer_info_by_phone(session=session, phone=phone)

        if not stu_res:
            return None, None, "دانش‌آموزی با این شماره تلفن یافت نشد."

        user_id = stu_res["user_id"]
        access_data = stu_res["access"]
        student_state = {}
        for package_name in ["AG", "SCL"]:
            package_info = access_data.get(package_name, {})
            permission = 0
            limit = 0

            if isinstance(package_info, dict):
                permission = int(package_info.get("permission") or 0)
                limit = int(package_info.get("limit") or 0)
            elif isinstance(package_info, bool):
                permission = 1 if package_info else 0
            elif isinstance(package_info, (int, float, str)):
                try:
                    permission = int(package_info) if str(package_info).strip() != "" else 0
                except ValueError:
                    permission = 0

            student_state[package_name] = {
                "permission": permission,
                "limit": limit
            }

        result = {
            "student_id": user_id,
            "phone": phone,
            "first_name": stu_res["first_name"],
            "last_name": stu_res["last_name"],
            "quiz_answers": stu_res["quiz_attempts"],
            "student_state": student_state,
            "access": access_data
        }

        token = func_helper.get_tracking_code()
        return token, result, ""

    except Exception as e:
        func_helper.service_exception_error_logging("ag_api/admin_request", "check_student_quiz_answer", str(e), request_data, {}
        )
        return None, None, f"خطا در بررسی پاسخ‌های آزمون دانش‌آموز: {str(e)}"
