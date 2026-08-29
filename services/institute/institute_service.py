import config
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.filters import ConsultantFilters, StudentFilters
from helper.db.sqlalchemy.queries.consultants import (
    create_consultant_profile,
    list_consultants_for_owner,
    update_consultant_profile_for_owner,
)
from helper.db.sqlalchemy.queries.dashboard import (
    count_consultants_for_owner,
    count_student_packages_for_scope,
    count_students_for_scope,
    list_capacity_packages_for_user,
    list_notifications_for_user,
    list_quiz_attempts_for_scope,
)
from helper.db.sqlalchemy.queries.reports import list_quiz_attempts_for_users
from helper.db.sqlalchemy.queries.institutes import (
    create_institute_profile,
    get_institute_profile,
    update_institute_profile,
    verify_institute,
)
from helper.db.sqlalchemy.queries.students import (
    create_student_profile,
    list_students_for_owner,
    update_student_profile_for_owner,
)
from helper.db.sqlalchemy.queries.settings import upsert_setting
import helper.func_helper as func_helper
from helper.response import (
    build_consultant_list_response,
    build_dashboard_info_response,
    build_student_list_response,
    build_student_management_report_response,
    build_student_report_response,
)


def get_info(conn, cursor, user_id):
    try:
        with session_scope() as session:
            res = get_institute_profile(session=session, user_id=user_id)
        if not res:
            raise ValueError("institute not found")
        token = func_helper.get_tracking_code()
        info_response = {"phone": res.get("phone"), "user_id": user_id, "id": res.get("ins_id"),
                         "name": res.get("name"), "role": "ins", "pic": res.get("logo")}
        return token, info_response, ""
    except Exception as e:
        func_helper.safe_rollback(conn)
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "get_info", str(e), {},
                                        {"user_id": user_id})
        return None, None, "اطلاعات کاربر یافت نشد."


def get_dashboard(conn, cursor, request_data, user_info):
    """
    Fetches dashboard data for institute users, including per-package capacity,
    student/consultant counts, quiz statistics, and notifications.
    """
    try:
        user_id = user_info["user_id"]
        with session_scope() as session:
            capacity_packages = list_capacity_packages_for_user(session=session, user_id=user_id)
            student_count = count_students_for_scope(session=session, scope="owner", user_id=user_id)
            consultant_count = count_consultants_for_owner(session=session, owner_user_id=user_id)
            package_counts = count_student_packages_for_scope(session=session, scope="owner", user_id=user_id)
            quiz_attempts = list_quiz_attempts_for_scope(session=session, scope="owner", user_id=user_id)
            notifications = list_notifications_for_user(
                session=session,
                user_id=user_id,
                role_terms=["institute"],
            )

        cons_info = build_dashboard_info_response(
            capacity_packages=capacity_packages,
            student_count=student_count,
            consultant_count=consultant_count,
            package_counts=package_counts,
            quiz_attempts=quiz_attempts,
            packages_data=func_helper.PACKAGES_DATA,
        )

        token = func_helper.get_tracking_code()
        return token, {"dashboard_info": cons_info, "notifications": notifications}, ""

    except Exception as e:
        func_helper.safe_rollback(conn)
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "get_dashboard", str(e), request_data, user_info)
        return None, None, "اطلاعات داشبورد دریافت نشد."


def add_institute(conn, cursor, request_data, user_id):
    try:
        with session_scope() as session:
            create_institute_profile(session=session, user_id=user_id, name=request_data["name"])

        func_helper.add_capacity_signup(user_id=user_id)
        token = func_helper.get_tracking_code()

        return token, None, ""

    except Exception as e:
        func_helper.safe_rollback(conn)
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "add_institute", str(e), request_data,
                                        {"user_id": user_id, "phone": request_data["phone"]})
        return None, None, "مشکل در ثبت موسسه رخ داده است."


def get_report(conn, cursor, request_data, user_info):
    try:
        with session_scope() as session:
            students = list_students_for_owner(session=session, owner_user_id=user_info["user_id"])
        report_info = build_student_report_response(students, include_consultant_name=True)
        token = func_helper.get_tracking_code()
        return token, report_info, ""
    except Exception as e:
        func_helper.safe_rollback(conn)
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "get_report", str(e), request_data, user_info)
        return None, [], "مشکل در دریافت گزارش رخ داده است."


def get_management_report(conn, cursor, request_data, user_info):
    try:
        with session_scope() as session:
            students = list_students_for_owner(session=session, owner_user_id=user_info["user_id"])
            quiz_attempts = list_quiz_attempts_for_users(
                session=session,
                user_ids=[student["user_id"] for student in students],
            )
        report_info = build_student_management_report_response(
            students,
            quiz_attempts,
            packages_data=func_helper.PACKAGES_DATA,
            get_quiz_name=func_helper.get_quiz_name,
            include_consultant_name=True,
        )
        token = func_helper.get_tracking_code()
        return token, report_info, ""
    except Exception as e:
        func_helper.safe_rollback(conn)
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "get_management_report", str(e),
                                        request_data,
                                        user_info)
        return None, None, "مشکل در دریافت گزارش مدیریتی رخ داده است."


# this function is for add consultant in ins
def add_consultant(conn, cursor, request_data, con_user_id, user_info):
    try:
        with session_scope() as session:
            create_consultant_profile(
                session=session,
                user_id=con_user_id,
                owner_user_id=user_info["user_id"],
                editor_id=user_info["user_id"],
                first_name=request_data["first_name"],
                last_name=request_data["last_name"],
                sex=request_data["sex"],
            )
        token = func_helper.get_tracking_code()
        return token, None, "مشاور شما با موفقیت ثبت شد."
    except Exception as e:
        func_helper.safe_rollback(conn)
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "add_consultant", str(e), request_data, user_info)
        return None, None, "مشکلی در ثبت نهایی اطلاعات مشاور رخ داده است لطفا با پیشیبانی در ارتباط باشید."


# this function is for update the information of consultant
def change_consultant(conn, cursor, request_data, user_info):
    try:
        with session_scope() as session:
            update_consultant_profile_for_owner(
                session=session,
                user_id=int(request_data["consultant_id"]),
                editor_id=request_data["user_id"],
                first_name=request_data["first_name"],
                last_name=request_data["last_name"],
                sex=request_data["sex"],
            )
        token = func_helper.get_tracking_code()
        return token, None, "اطلاعات مشاور شما با موفقیت تغییر کرد."
    except Exception as e:
        func_helper.safe_rollback(conn)
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "change_consultant", str(e), request_data, user_info)
        return None, None, "مشکلی در ثبت نهایی اطلاعات مشاور رخ داده است لطفا با پیشیبانی در ارتباط باشید."


# this function use for get consultant of ins for list of consultants and add students cons pick filed
def get_consultants(conn, cursor, request_data, user_info):
    try:
        filters = ConsultantFilters.from_request(request_data)
        with session_scope() as session:
            consultants = list_consultants_for_owner(
                session=session,
                owner_user_id=user_info["user_id"],
                filters=filters,
            )
        cons_info = build_consultant_list_response(consultants)
        token = func_helper.get_tracking_code()
        return token, cons_info, ""
    except Exception as e:
        func_helper.safe_rollback(conn)
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "get_consultants", str(e), request_data, user_info)
        return None, [], "اطلاعات مشاورین دریافت نشد."


# this function for insert student to ins
def add_student(conn, cursor, request_data, stu_user_id, user_info):
    try:
        with session_scope() as session:
            create_student_profile(
                session=session,
                user_id=stu_user_id,
                owner_user_id=user_info["user_id"],
                consultant_user_id=request_data["con_id"],
                adder_id=user_info["user_id"],
                first_name=request_data["first_name"],
                last_name=request_data["last_name"],
                sex=request_data["sex"],
                city=request_data["city"],
                birth_date=request_data["birth_date"],
            )
        token = func_helper.get_tracking_code()
        return token, None, "دانش‌آموز شما با موفقیت ثبت شد."
    except Exception as e:
        func_helper.safe_rollback(conn)
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "add_student", str(e), request_data, user_info)
        return None, None, "مشکلی در افزودن دانش‌آموز رخ داده است."


# this function is for update the information of consultant
def change_student(conn, cursor, request_data, user_info):
    try:
        with session_scope() as session:
            update_student_profile_for_owner(
                session=session,
                student_user_id=int(request_data["student_id"]),
                editor_id=user_info["user_id"],
                first_name=request_data["first_name"],
                last_name=request_data["last_name"],
                sex=request_data["sex"],
                city=request_data["city"],
                consultant_user_id=request_data["con_id"],
                birth_date=request_data["birth_date"],
            )
        token = func_helper.get_tracking_code()
        return token, None, "اطلاعات دانش‌آموز شما با موفقیت تغییر کرد."
    except Exception as e:
        func_helper.safe_rollback(conn)
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "change_student", str(e), request_data, user_info)
        return None, None, "مشکلی در تغییر اطلاعات دانش‌آموز رخ داده است."


# this function use for get students of ins for list of students
def get_students(conn, cursor, request_data, user_info):
    try:
        filters = StudentFilters.from_request(request_data)
        with session_scope() as session:
            students = list_students_for_owner(
                session=session,
                owner_user_id=user_info["user_id"],
                filters=filters,
            )

        stu_info = build_student_list_response(students)
        token = func_helper.get_tracking_code()
        return token, stu_info, ""
    except Exception as e:
        func_helper.safe_rollback(conn)
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "get_students", str(e), request_data, user_info)
        return None, [], "اطلاعات دانش‌آموزان دریافت نشد."


def change_user_info(conn, cursor, request_data, user_info):
    try:
        pic = func_helper.save_base64_image(
            request_data.get("pic"),
            request_data.get("last_pic"),
            config.INS_PIC_DIR,
        )
        with session_scope() as session:
            update_institute_profile(
                session=session,
                user_id=user_info["user_id"],
                name=request_data["name"],
                logo=pic,
            )
        token = func_helper.get_tracking_code()
        response = {"name": request_data["name"]}
        if pic is not None:
            response["pic"] = pic
        return token, response, "اطلاعات شما با موفقیت تغییر یافت."
    except Exception as e:
        func_helper.safe_rollback(conn)
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "change_user_info", str(e), request_data,
                                        user_info)
        return None, None, "اطلاعات شما با موفقیت تغییر نیافت."


def change_user_image(conn, cursor, request_data, user_info):
    try:
        with session_scope() as session:
            update_institute_profile(
                session=session,
                user_id=int(request_data["user_id"]),
                name=request_data["name"],
                logo=request_data["pic"],
            )
        token = func_helper.get_tracking_code()
        return token, {"name": request_data["name"], "pic": request_data["pic"]}, "اطلاعات شما با موفقیت تغییر یافت."
    except Exception as e:
        func_helper.safe_rollback(conn)
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "change_user_image", str(e), request_data, user_info)

        return None, None, "اطلاعات شما با موفقیت تغییر نیافت."


def change_user_voice(conn, cursor, request_data, user_info):
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
        func_helper.safe_rollback(conn)
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "change_user_voice", str(e), request_data, user_info)
        return None, None, "اطلاعات شما با موفقیت تغییر نیافت."


def change_setting(conn, cursor, request_data, user_info):
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
        func_helper.safe_rollback(conn)
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "change_setting", str(e), request_data, user_info)
        return None, None, "پیش اطلاعات اولیه آزمون شما تغییر نیافت."


def verify_user(conn, cursor, user_id):
    try:
        with session_scope() as session:
            verify_institute(session=session, user_id=user_id)
        token = func_helper.get_tracking_code()
        with session_scope() as session:
            res = get_institute_profile(session=session, user_id=user_id)
        if not res:
            raise ValueError("institute not found")
        info_response = {"phone": res.get("phone"), "user_id": user_id, "id": res.get("ins_id"),
                         "name": res.get("name"), "role": "ins", "pic": res.get("logo")}
        return token, info_response, ""
    except Exception as e:
        func_helper.safe_rollback(conn)
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "verify_user", str(e), None,
                                        {"user_id": user_id})
        return None, None, "اطلاعات کاربر یافت نشد."


def change_student_access(conn, cursor, request_data, user_info):
    """
    Update student access permissions and manage capacity tracking for institute.
    
    Uses the reusable helper function func_helper.update_student_access_and_capacity.
    """
    return func_helper.update_student_access_and_capacity(
        request_data=request_data,
        user_info=user_info,
        role_type="ins",
        id_field="owner_user_id",
        end_point="ag_api/ins"
    )
