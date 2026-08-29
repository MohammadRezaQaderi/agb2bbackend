from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.admin import (
    add_capacity_to_user,
    get_admin_user_info_by_phone,
    get_student_quiz_answer_info_by_phone,
    get_user_role_by_phone,
)
import helper.func_helper as func_helper


def change_capacity(conn, cursor, request_data):
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
        func_helper.service_exception_error_logging(
            conn, cursor, "ag_api/admin_request", "change_capacity", str(e), request_data, {}
        )
        return None, None, f"خطا در به‌روزرسانی ظرفیت: {str(e)}"


def get_user_info(conn, cursor, request_data):
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
        func_helper.service_exception_error_logging(
            conn, cursor, "ag_api/admin_request", "get_user_info", str(e), request_data, {}
        )
        return None, None, f"خطا در دریافت اطلاعات کاربر: {str(e)}"


def check_student_quiz_answer(conn, cursor, request_data):
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
        func_helper.service_exception_error_logging(
            conn, cursor, "ag_api/admin_request", "check_student_quiz_answer", str(e), request_data, {}
        )
        return None, None, f"خطا در بررسی پاسخ‌های آزمون دانش‌آموز: {str(e)}"
