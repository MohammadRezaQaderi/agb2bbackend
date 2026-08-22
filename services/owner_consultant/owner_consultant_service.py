from datetime import datetime

import config
import helper.db.db_helper as db_helper
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.filters import StudentFilters
from helper.db.sqlalchemy.queries.dashboard import (
    count_student_packages_for_scope,
    count_students_for_scope,
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
            SELECT o.ocon_id, u.phone, o.first_name, o.last_name, o.logo
            FROM ocon o
            INNER JOIN users u ON u.user_id = o.user_id
            WHERE o.user_id = ?
        '''
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=user_id)
        token = func_helper.get_tracking_code()
        user_info = {"phone": res.phone, "user_id": user_id, "id": res.ocon_id, "first_name": res.first_name, "role": "ocon",
                "last_name": res.last_name, "pic": res.logo}
        return token, user_info, ""
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ocon", "get_info", str(e), {},
                                        {"user_id": user_id})
        return None, None, "اطلاعات کاربر یافت نشد."


def get_dashboard(conn, cursor, request_data, user_info):
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
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ocon", "get_dashboard", str(e), request_data,
                                        user_info)
        return None, None, "اطلاعات داشبورد دریافت نشد."


def add_owner_consultant(conn, cursor, request_data, user_id):
    try:
        table = "ocon"
        sex = request_data.get("sex")
        if not sex:
            sex = 1
        field = '([first_name], [last_name], [user_id], [sex])'
        values = (
            request_data["first_name"], request_data["last_name"], user_id, sex)
        db_helper.insert_value(conn=conn, cursor=cursor, table_name=table, fields=field,
                               values=values)
        func_helper.add_capacity_signup(conn, cursor, user_id, request_data["phone"])
        token = func_helper.get_tracking_code()
        return token, None, ""
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ocon", "add_owner_consultant", str(e), request_data,
                                        {"user_id": user_id, "phone": request_data["phone"]})
        return None, None, "مشکل در ثبت مشاور ارشد رخ داده است."


def get_report(conn, cursor, request_data, user_info):
    try:
        with session_scope() as session:
            students = list_students_for_consultant(session=session, consultant_user_id=user_info["user_id"])
        report_info = build_student_report_response(students)
        token = func_helper.get_tracking_code()
        return token, report_info, ""
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ocon", "get_report", str(e), request_data, user_info)
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
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ocon", "get_management_report", str(e),
                                        request_data, user_info)
        return None, None, "مشکل در دریافت گزارش مدیریتی رخ داده است."


def add_student(conn, cursor, request_data, stu_user_id, user_info):
    try:
        table = "stu"
        field = '([user_id], [first_name], [last_name], [sex], [city], [owner_user_id], [consultant_user_id], [adder_id], [editor_id], [birth_date])'
        values = (
            stu_user_id, request_data["first_name"], request_data["last_name"], request_data["sex"], request_data["city"],
            request_data["user_id"],
            user_info["user_id"], user_info["user_id"], user_info["user_id"], request_data["birth_date"],)
        db_helper.insert_value(conn=conn, cursor=cursor, table_name=table, fields=field,
                               values=values)
        token = func_helper.get_tracking_code()
        return token, None, "دانش‌آموز شما با موفقیت ثبت شد."
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ocon", "add_student", str(e), request_data, user_info)
        return None, None, "مشکلی در افزودن دانش‌آموز رخ داده است."


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
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ocon", "change_student", str(e), request_data, user_info)
        return None, None, "مشکلی در تغییر اطلاعات دانش‌آموز رخ داده است."


def change_comment(conn, cursor, request_data, user_info):
    try:
        db_helper.update_record(conn, cursor, 'stu',
                                ['comment', 'editor_id', 'edited_time'],
                                [request_data["consultant_comment"], user_info["user_id"],
                                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                'user_id = ?', [str(request_data["student_id"])])
        token = func_helper.get_tracking_code()
        return token, None, "اطلاعات دانش‌آموز شما با موفقیت تغییر کرد."
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ocon", "change_comment", str(e), request_data, user_info)
        return None, None, "مشکلی در تغییر توضیحات دانش‌آموز رخ داده است."


def change_user_info(conn, cursor, request_data, user_info):
    try:
        update_fields = ['first_name', 'last_name', 'edited_time']
        update_values = [
            request_data["first_name"],
            request_data["last_name"],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ]
        pic = func_helper.save_base64_image(
            request_data.get("pic"),
            request_data.get("last_pic"),
            config.INS_PIC_DIR,
        )
        if pic is not None:
            update_fields.insert(2, 'logo')
            update_values.insert(2, pic)

        db_helper.update_record(conn, cursor, 'ocon',
                                update_fields,
                                update_values,
                                'user_id = ?', [str(user_info["user_id"])])
        token = func_helper.get_tracking_code()
        response = {"first_name": request_data["first_name"], "last_name": request_data["last_name"]}
        if pic is not None:
            response["pic"] = pic
        return token, response, "اطلاعات شما با موفقیت تغییر یافت."
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ocon", "change_user_info", str(e), request_data,
                                        user_info)
        return None, None, "اطلاعات شما با موفقیت تغییر نیافت."


def get_students(conn, cursor, request_data, user_info):
    try:
        query = 'SELECT first_name, last_name FROM ocon WHERE user_id = ?'
        res_con = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=user_info["user_id"])
        con_name = ""
        if res_con and len(res_con) >= 2:
            con_name = f"{res_con.first_name} {res_con.last_name}"
        filters = StudentFilters.from_request(request_data)
        with session_scope() as session:
            students = list_students_for_consultant(
                session=session,
                consultant_user_id=user_info["user_id"],
                filters=filters,
            )
        stu_info = build_student_list_response(
            students,
            default_con_name=con_name,
            default_con_id=user_info["user_id"],
        )
        token = func_helper.get_tracking_code()
        return token, stu_info, ""
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ocon", "get_students", str(e), request_data, user_info)
        return None, [], "اطلاعات دانش‌آموزان دریافت نشد."


def change_user_voice(conn, cursor, request_data, user_info):
    try:
        token = func_helper.get_tracking_code()
        if request_data["setting_id"] == "no setting":
            table = "setting"
            field = '([user_id], [description], [voice], [quiz_id])'
            values = (
                request_data["user_id"], request_data["description"], request_data["voice"], request_data["quiz_id"],)
            db_helper.insert_value(conn=conn, cursor=cursor, table_name=table, fields=field,
                                   values=values)
            return token, None, "اطلاعات شما با موفقیت تغییر یافت."
        else:
            db_helper.update_record(conn, cursor, 'setting',
                                    ['description', 'voice', 'edited_time'],
                                    [request_data["description"], request_data["voice"],
                                     datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                    'setting_id = ?', [str(request_data["setting_id"])])
            return token, None, "اطلاعات شما با موفقیت تغییر یافت."
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ocon", "change_user_voice", str(e), request_data,
                                        user_info)
        return None, None, "اطلاعات شما با موفقیت تغییر نیافت."


def change_setting(conn, cursor, request_data, user_info):
    try:
        if request_data["setting_id"] == "no setting":
            table = "setting"
            field = '([user_id], [description], [voice], [quiz_id])'
            values = (
                request_data["user_id"], request_data["description"], request_data["voice"], request_data["quiz_id"],)
            db_helper.insert_value(conn=conn, cursor=cursor, table_name=table, fields=field,
                                   values=values)
            token = func_helper.get_tracking_code()
            return token, None, "پیش اطلاعات اولیه آزمون شما تغییر یافت."
        else:
            db_helper.update_record(conn, cursor, 'setting',
                                    ['description', 'edited_time'],
                                    [request_data["description"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                    'setting_id = ?', [str(request_data["setting_id"])])
            token = func_helper.get_tracking_code()
            return token, None, "پیش اطلاعات اولیه آزمون شما تغییر یافت."
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ocon", "change_setting", str(e), request_data, user_info)
        return None, None, "پیش اطلاعات اولیه آزمون شما تغییر نیافت."


def verify_user(conn, cursor, user_id):
    try:
        db_helper.update_record(conn, cursor, 'ocon',
                                ['verify', 'edited_time'],
                                [1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                'user_id = ?', [str(user_id)])
        token = func_helper.get_tracking_code()
        query = '''
            SELECT o.ocon_id, u.phone, o.first_name, o.last_name, o.logo
            FROM ocon o
            INNER JOIN users u ON u.user_id = o.user_id
            WHERE o.user_id = ?
        '''
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=user_id)
        user_info = {"phone": res.phone, "user_id": user_id, "id": res.ocon_id, "first_name": res.first_name, "role": "ocon",
                "last_name": res.last_name, "pic": res.logo}
        return token, user_info, ""
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ocon", "verify_user", str(e), None,
                                        {"user_id": user_id})
        return None, None, "اطلاعات کاربر یافت نشد."


def change_student_access(conn, cursor, request_data, user_info):
    """
    Update student access permissions and manage capacity tracking for owner consultant.

    Uses the reusable helper function func_helper.update_student_access_and_capacity.
    """
    return func_helper.update_student_access_and_capacity(
        conn=conn,
        cursor=cursor,
        request_data=request_data,
        user_info=user_info,
        role_type="ocon",
        id_field="consultant_user_id",
        end_point="ag_api/ocon"
    )
