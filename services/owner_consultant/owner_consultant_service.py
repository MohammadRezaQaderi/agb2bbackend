import config
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.filters import StudentFilters
from helper.db.sqlalchemy.queries.consultants import (
    update_student_comment_by_consultant,
    update_student_profile_by_consultant,
)
from helper.db.sqlalchemy.queries.dashboard import (
    count_student_packages_for_scope,
    count_students_for_scope,
    list_capacity_packages_for_user,
    list_notifications_for_user,
    list_quiz_attempts_for_scope,
)
from helper.db.sqlalchemy.queries.owner_consultants import (
    get_owner_consultant_profile,
    update_owner_consultant_profile,
    verify_owner_consultant,
)
from helper.db.sqlalchemy.queries.reports import list_quiz_attempts_for_users
from helper.db.sqlalchemy.queries.settings import upsert_setting
from helper.db.sqlalchemy.queries.students import (
    list_students_for_consultant,
)
import helper.func_helper as func_helper
from helper.response import (
    build_dashboard_info_response,
    build_student_list_response,
    build_student_management_report_response,
    build_student_report_response,
)


def get_info(user_id):
    try:
        with session_scope() as session:
            res = get_owner_consultant_profile(session=session, user_id=user_id)
        if not res:
            raise ValueError("owner consultant not found")
        token = func_helper.get_tracking_code()
        user_info = {
            "phone": res.get("phone"),
            "user_id": user_id,
            "id": res.get("ocon_id"),
            "first_name": res.get("first_name"),
            "role": "ocon",
            "last_name": res.get("last_name"),
            "pic": res.get("logo"),
        }
        return token, user_info, ""
    except Exception as e:
        func_helper.service_exception_error_logging("ag_api/ocon", "get_info", str(e), {},
                                        {"user_id": user_id})
        return None, None, "اطلاعات کاربر یافت نشد."


def get_dashboard(request_data, user_info):
    """
    Fetches dashboard data for owner consultants, including:
    - Per-package capacity (AG, BK, etc.)
    - Student counts
    - Quiz statistics
    - Notifications
    """
    try:
        user_id = user_info["user_id"]
        with session_scope() as session:
            capacity_packages = list_capacity_packages_for_user(session=session, user_id=user_id)
            student_count = count_students_for_scope(session=session, scope="consultant", user_id=user_id)
            package_counts = count_student_packages_for_scope(session=session, scope="consultant", user_id=user_id)
            quiz_attempts = list_quiz_attempts_for_scope(session=session, scope="consultant", user_id=user_id)
            notifications = list_notifications_for_user(
                session=session,
                user_id=user_id,
                role_terms=["ownerConsultant"],
            )

        token = func_helper.get_tracking_code()
        cons_info = build_dashboard_info_response(
            capacity_packages=capacity_packages,
            student_count=student_count,
            package_counts=package_counts,
            quiz_attempts=quiz_attempts,
            packages_data=func_helper.PACKAGES_DATA,
        )

        return token, {"dashboard_info": cons_info, "notifications": notifications}, ""

    except Exception as e:
        func_helper.service_exception_error_logging("ag_api/ocon", "get_dashboard", str(e), request_data,
                                        user_info)
        return None, None, "اطلاعات داشبورد دریافت نشد."


def get_report(request_data, user_info):
    try:
        with session_scope() as session:
            students = list_students_for_consultant(session=session, consultant_user_id=user_info["user_id"])
        report_info = build_student_report_response(students)
        token = func_helper.get_tracking_code()
        return token, report_info, ""
    except Exception as e:
        func_helper.service_exception_error_logging("ag_api/ocon", "get_report", str(e), request_data, user_info)
        return None, [], "مشکل در دریافت گزارش رخ داده است."


def get_management_report(request_data, user_info):
    try:
        with session_scope() as session:
            students = list_students_for_consultant(session=session, consultant_user_id=user_info["user_id"])
            quiz_attempts = list_quiz_attempts_for_users(
                session=session,
                user_ids=[student["user_id"] for student in students],
            )
        report_info = build_student_management_report_response(
            students,
            quiz_attempts,
            packages_data=func_helper.PACKAGES_DATA,
            get_quiz_name=func_helper.get_quiz_name,
        )
        token = func_helper.get_tracking_code()
        return token, report_info, ""
    except Exception as e:
        func_helper.service_exception_error_logging("ag_api/ocon", "get_management_report", str(e),
                                        request_data, user_info)
        return None, None, "مشکل در دریافت گزارش مدیریتی رخ داده است."


def change_student(request_data, user_info):
    try:
        with session_scope() as session:
            update_student_profile_by_consultant(
                session=session,
                student_user_id=int(request_data["student_id"]),
                editor_id=user_info["user_id"],
                first_name=request_data["first_name"],
                last_name=request_data["last_name"],
                sex=request_data["sex"],
                city=request_data["city"],
                birth_date=request_data["birth_date"],
            )
        token = func_helper.get_tracking_code()
        return token, None, "اطلاعات دانش‌آموز شما با موفقیت تغییر کرد."
    except Exception as e:
        func_helper.service_exception_error_logging("ag_api/ocon", "change_student", str(e), request_data, user_info)
        return None, None, "مشکلی در تغییر اطلاعات دانش‌آموز رخ داده است."


def change_comment(request_data, user_info):
    try:
        with session_scope() as session:
            update_student_comment_by_consultant(
                session=session,
                student_user_id=int(request_data["student_id"]),
                editor_id=user_info["user_id"],
                comment=request_data["consultant_comment"],
            )
        token = func_helper.get_tracking_code()
        return token, None, "اطلاعات دانش‌آموز شما با موفقیت تغییر کرد."
    except Exception as e:
        func_helper.service_exception_error_logging("ag_api/ocon", "change_comment", str(e), request_data, user_info)
        return None, None, "مشکلی در تغییر توضیحات دانش‌آموز رخ داده است."


def change_user_info(request_data, user_info):
    try:
        pic = func_helper.save_base64_image(
            request_data.get("pic"),
            request_data.get("last_pic"),
            config.INS_PIC_DIR,
        )
        with session_scope() as session:
            update_owner_consultant_profile(
                session=session,
                user_id=user_info["user_id"],
                first_name=request_data["first_name"],
                last_name=request_data["last_name"],
                logo=pic,
            )
        token = func_helper.get_tracking_code()
        response = {"first_name": request_data["first_name"], "last_name": request_data["last_name"]}
        if pic is not None:
            response["pic"] = pic
        return token, response, "اطلاعات شما با موفقیت تغییر یافت."
    except Exception as e:
        func_helper.service_exception_error_logging("ag_api/ocon", "change_user_info", str(e), request_data,
                                        user_info)
        return None, None, "اطلاعات شما با موفقیت تغییر نیافت."


def get_students(request_data, user_info):
    try:
        with session_scope() as session:
            res_con = get_owner_consultant_profile(session=session, user_id=user_info["user_id"])
            filters = StudentFilters.from_request(request_data)
            students = list_students_for_consultant(
                session=session,
                consultant_user_id=user_info["user_id"],
                filters=filters,
            )
        con_name = ""
        if res_con:
            con_name = f"{res_con.get('first_name')} {res_con.get('last_name')}"
        stu_info = build_student_list_response(
            students,
            default_con_name=con_name,
            default_con_id=user_info["user_id"],
        )
        token = func_helper.get_tracking_code()
        return token, stu_info, ""
    except Exception as e:
        func_helper.service_exception_error_logging("ag_api/ocon", "get_students", str(e), request_data, user_info)
        return None, [], "اطلاعات دانش‌آموزان دریافت نشد."


def change_user_voice(request_data, user_info):
    try:
        token = func_helper.get_tracking_code()
        with session_scope() as session:
            upsert_setting(
                session=session,
                setting_id=request_data["setting_id"],
                user_id=request_data["user_id"],
                description=request_data["description"],
                voice=request_data["voice"],
                quiz_id=request_data["quiz_id"],
            )
        return token, None, "اطلاعات شما با موفقیت تغییر یافت."
    except Exception as e:
        func_helper.service_exception_error_logging("ag_api/ocon", "change_user_voice", str(e), request_data,
                                        user_info)
        return None, None, "اطلاعات شما با موفقیت تغییر نیافت."


def change_setting(request_data, user_info):
    try:
        with session_scope() as session:
            upsert_setting(
                session=session,
                setting_id=request_data["setting_id"],
                user_id=request_data["user_id"],
                description=request_data["description"],
                voice=request_data.get("voice"),
                quiz_id=request_data["quiz_id"],
            )
        token = func_helper.get_tracking_code()
        return token, None, "پیش اطلاعات اولیه آزمون شما تغییر یافت."
    except Exception as e:
        func_helper.service_exception_error_logging("ag_api/ocon", "change_setting", str(e), request_data, user_info)
        return None, None, "پیش اطلاعات اولیه آزمون شما تغییر نیافت."


def verify_user(user_id):
    try:
        with session_scope() as session:
            verify_owner_consultant(session=session, user_id=user_id)
            res = get_owner_consultant_profile(session=session, user_id=user_id)
        if not res:
            raise ValueError("owner consultant not found")
        token = func_helper.get_tracking_code()
        user_info = {
            "phone": res.get("phone"),
            "user_id": user_id,
            "id": res.get("ocon_id"),
            "first_name": res.get("first_name"),
            "role": "ocon",
            "last_name": res.get("last_name"),
            "pic": res.get("logo"),
        }
        return token, user_info, ""
    except Exception as e:
        func_helper.service_exception_error_logging("ag_api/ocon", "verify_user", str(e), None,
                                        {"user_id": user_id})
        return None, None, "اطلاعات کاربر یافت نشد."


def change_student_access(request_data, user_info):
    """
    Update student access permissions and manage capacity tracking for owner consultant.

    Uses the reusable helper function func_helper.update_student_access_and_capacity.
    """
    return func_helper.update_student_access_and_capacity(
        request_data=request_data,
        user_info=user_info,
        role_type="ocon",
        id_field="consultant_user_id",
        end_point="ag_api/ocon"
    )
