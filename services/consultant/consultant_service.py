from datetime import datetime

import helper.db.db_helper as db_helper
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.filters import StudentFilters
from helper.db.sqlalchemy.queries.dashboard import (
    count_student_packages_for_scope,
    count_students_for_scope,
    get_consultant_owner_user_id,
    list_capacity_packages_for_user,
    list_notifications_for_user,
    list_quiz_attempts_for_scope,
)
from helper.db.sqlalchemy.queries.reports import list_quiz_attempts_for_users
from helper.db.sqlalchemy.queries.students import list_students_for_consultant
import helper.func_helper as func_helper
from helper.response import (
    build_dashboard_info_response,
    build_student_list_response,
    build_student_management_report_response,
    build_student_report_response,
)


def get_info(conn, cursor, user_id):
    try:
        query = '''
            SELECT c.con_id, u.phone, c.first_name, c.last_name, c.owner_user_id,
                   owner.role AS owner_role
            FROM con c
            INNER JOIN users u ON u.user_id = c.user_id
            LEFT JOIN users owner ON owner.user_id = c.owner_user_id
            WHERE c.user_id = ?
        '''
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=user_id)
        if res.owner_role == "ins":
            query_ins = 'SELECT name, logo FROM ins WHERE user_id = ?'
            res_ins = db_helper.search_table(conn=conn, cursor=cursor, query=query_ins, field=res.owner_user_id)
        else:
            query_ins = 'SELECT name, logo FROM sch WHERE user_id = ?'
            res_ins = db_helper.search_table(conn=conn, cursor=cursor, query=query_ins, field=res.owner_user_id)
        token = func_helper.get_tracking_code()
        response_info = {"phone": res.phone, "user_id": user_id, "id": res.con_id, "first_name": res.first_name,
                         "last_name": res.last_name, "role": 'con', "name": res_ins.name, "pic": res_ins.logo,
                         "owner_user_id": res.owner_user_id, "ins_id": res.owner_user_id}
        return token, response_info, ""
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/con", "get_info", str(e), {},
                                        {"user_id": user_id})
        return None, None, "اطلاعات کاربر یافت نشد."


def get_dashboard(conn, cursor, request_data, user_info):
    """
    Fetches dashboard data for consultant users, including:
    - Student counts
    - Quiz statistics
    - Package-specific student counts (AG, SCL)
    - Notifications
    """
    try:
        user_id = user_info["user_id"]
        with session_scope() as session:
            owner_user_id = get_consultant_owner_user_id(session=session, consultant_user_id=user_id) or user_id
            capacity_packages = list_capacity_packages_for_user(session=session, user_id=owner_user_id)
            student_count = count_students_for_scope(session=session, scope="consultant", user_id=user_id)
            package_counts = count_student_packages_for_scope(session=session, scope="consultant", user_id=user_id)
            quiz_attempts = list_quiz_attempts_for_scope(session=session, scope="consultant", user_id=user_id)
            notifications = list_notifications_for_user(
                session=session,
                user_id=user_id,
                role_terms=["con"],
            )

        cons_info = build_dashboard_info_response(
            capacity_packages=capacity_packages,
            student_count=student_count,
            package_counts=package_counts,
            quiz_attempts=quiz_attempts,
            packages_data=func_helper.PACKAGES_DATA,
        )

        token = func_helper.get_tracking_code()
        return token, {"dashboard_info": cons_info, "notifications": notifications}, ""

    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/con", "get_dashboard", str(e), request_data, user_info)
        return None, None, "اطلاعات داشبورد دریافت نشد."


def get_report(conn, cursor, request_data, user_info):
    try:
        with session_scope() as session:
            students = list_students_for_consultant(session=session, consultant_user_id=user_info["user_id"])
        report_info = build_student_report_response(students)
        token = func_helper.get_tracking_code()
        return token, report_info, ""
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/con", "get_report", str(e), request_data, user_info)
        return None, [], "مشکل در دریافت گزارش رخ داده است."


def get_management_report(conn, cursor, request_data, user_info):
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
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/con", "get_management_report", str(e),
                                        request_data, user_info)
        return None, None, "مشکل در دریافت گزارش مدیریتی رخ داده است."


# this function use for get students of con for list of students
def get_students(conn, cursor, request_data, user_info):
    try:
        filters = StudentFilters.from_request(request_data)
        with session_scope() as session:
            students = list_students_for_consultant(
                session=session,
                consultant_user_id=user_info["user_id"],
                filters=filters,
            )
        stu_info = build_student_list_response(students, default_con_id=user_info["user_id"])
        token = func_helper.get_tracking_code()
        return token, stu_info, ""
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/con", "get_students", str(e), request_data, user_info)
        return None, [], "اطلاعات دانش‌آموزان دریافت نشد."


# this function is for update the information of consultant
def change_student(conn, cursor, request_data, user_info):
    try:
        db_helper.update_record(conn, cursor, 'stu',
                                ['first_name', 'last_name', 'sex', 'city', 'editor_id', 'birth_date',
                                 'edited_time'],
                                [request_data["first_name"], request_data["last_name"], request_data["sex"],
                                 request_data["city"], user_info["user_id"],
                                 request_data["birth_date"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                'user_id = ?', [str(request_data["student_id"])])
        token = func_helper.get_tracking_code()
        return token, None, "اطلاعات دانش‌آموز شما با موفقیت تغییر کرد."
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/con", "change_student", str(e), request_data, user_info)
        return None, None, "مشکلی در تغییر اطلاعات دانش‌آموز رخ داده است."


def change_comment(conn, cursor, request_data, user_info):
    try:
        db_helper.update_record(conn, cursor, 'stu',
                                ['comment', 'editor_id', 'edited_time'],
                                [request_data["consultant_comment"], request_data["user_id"],
                                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                'user_id = ?', [str(request_data["student_id"])])
        token = func_helper.get_tracking_code()
        return token, None, "اطلاعات دانش‌آموز شما با موفقیت تغییر کرد."
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/con", "change_comment", str(e), request_data, user_info)
        return None, None, "مشکلی در تغییر توضیحات دانش‌آموز رخ داده است."


def change_user_info(conn, cursor, request_data, user_info):
    try:
        db_helper.update_record(conn, cursor, 'con',
                                ['first_name', 'last_name', 'edited_time'],
                                [request_data["first_name"], request_data["last_name"],
                                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                'user_id = ?', [str(user_info["user_id"])])
        token = func_helper.get_tracking_code()
        return token, {"first_name": request_data["first_name"], "last_name": request_data["last_name"]}, "اطلاعات شما با موفقیت تغییر یافت."
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/con", "change_user_info", str(e), request_data,
                                        user_info)
        return None, None, "اطلاعات شما با موفقیت تغییر نیافت."
