import json
from datetime import datetime

import config
import helper.db.db_helper as db_helper
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.filters import ConsultantFilters, StudentFilters
from helper.db.sqlalchemy.queries.consultants import list_consultants_for_owner
from helper.db.sqlalchemy.queries.reports import list_quiz_attempts_for_users
from helper.db.sqlalchemy.queries.students import list_students_for_owner
import helper.func_helper as func_helper
from helper.response import (
    build_consultant_list_response,
    build_student_list_response,
    build_student_management_report_response,
    build_student_report_response,
)


def get_info(conn, cursor, user_id):
    try:
        query = '''
            SELECT i.ins_id, i.name, i.logo, u.phone
            FROM ins i
            INNER JOIN users u ON u.user_id = i.user_id
            WHERE i.user_id = ?
        '''
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=user_id)
        token = func_helper.get_tracking_code()
        info_response = {"phone": res.phone, "user_id": user_id, "id": res.ins_id, "name": res.name, "role": "ins",
                         "pic": res.logo}
        return token, info_response, ""
    except Exception as e:
        conn.rollback()
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

        package_quiz_count = {
            "AG": 7,
            "SCL": 4
        }

        query_capacity = """
            SELECT package_name, allowed, used
            FROM capacity_package
            WHERE user_id = ?
        """
        res_capacity = db_helper.search_fetchall(conn=conn, cursor=cursor, query=query_capacity, field=user_id)

        capacity_info = {
            row["package_name"]: {"allowed": row["allowed"], "used": row["used"]}
            for row in res_capacity
        }

        queries = {
            "stu_count": "SELECT COUNT(*) AS total FROM stu WHERE owner_user_id = ?",
            "con_count": "SELECT COUNT(*) AS total FROM con WHERE owner_user_id = ?"
        }

        results = {key: db_helper.search_fetchall(conn, cursor, query, field=user_id) for key, query in queries.items()}

        stu_count = results["stu_count"][0]["total"] if results["stu_count"] else 0
        con_count = results["con_count"][0]["total"] if results["con_count"] else 0

        stu_package_count = func_helper.get_student_package_access_counts(
            conn, cursor, user_id, "owner_user_id"
        )
        if stu_package_count is None:
            query_stu_access = "SELECT access FROM stu WHERE owner_user_id = ?"
            res_stu_access = db_helper.search_allin_table(conn=conn, cursor=cursor, query=query_stu_access, field=user_id)

            stu_package_count = {"AG": 0, "SCL": 0}
            if res_stu_access:
                for stu in res_stu_access:
                    raw_access = getattr(stu, "access", None) or "{}"
                    try:
                        access_data = json.loads(raw_access) if isinstance(raw_access, str) else (raw_access or {})
                    except (json.JSONDecodeError, TypeError):
                        access_data = {}

                    for package_name in ["AG", "SCL"]:
                        package_info = access_data.get(package_name, {})
                        permission = 0
                        if isinstance(package_info, dict):
                            permission = int(package_info.get("permission") or 0)
                        elif isinstance(package_info, bool):
                            permission = 1 if package_info else 0
                        elif isinstance(package_info, (int, float, str)):
                            try:
                                permission = int(package_info) if str(package_info).strip() != "" else 0
                            except ValueError:
                                permission = 0

                        if permission == 1:
                            stu_package_count[package_name] += 1

        # Get quiz statistics for AG and SCL packages
        quiz_report = {}
        for package_name in ["AG", "SCL"]:
            total_quizzes = package_quiz_count.get(package_name, 0)

            # Count students who finished all quizzes (completed last quiz with state = 2)
            query_finish_quiz = """
                SELECT COUNT(DISTINCT user_id) AS total 
                FROM quiz_attempt 
                WHERE owner_user_id = ? AND quiz_kind = ? AND state = 2 AND quiz_id = ?
            """
            res_finish_quiz = db_helper.search_fetchall(conn, cursor, query_finish_quiz,
                                                        field=(user_id, package_name, total_quizzes))
            finish_quiz = res_finish_quiz[0]["total"] if res_finish_quiz and res_finish_quiz[0]["total"] else 0

            # Count students who started at least one quiz
            query_started_quiz = """
                SELECT COUNT(DISTINCT user_id) AS total 
                FROM quiz_attempt 
                WHERE owner_user_id = ? AND quiz_kind = ?
            """
            res_started_quiz = db_helper.search_fetchall(conn, cursor, query_started_quiz,
                                                         field=(user_id, package_name))
            started_quiz = res_started_quiz[0]["total"] if res_started_quiz and res_started_quiz[0]["total"] else 0

            # Count total completed quizzes (state = 2) for this package
            query_c_quiz = """
                SELECT COUNT(*) AS total 
                FROM quiz_attempt 
                WHERE owner_user_id = ? AND quiz_kind = ? AND state = 2
            """
            res_c_quiz = db_helper.search_fetchall(conn, cursor, query_c_quiz, field=(user_id, package_name))
            c_quiz = res_c_quiz[0]["total"] if res_c_quiz and res_c_quiz[0]["total"] else 0

            # Count total started quizzes (any state) for this package
            query_total_first = """
                SELECT COUNT(*) AS total 
                FROM quiz_attempt 
                WHERE owner_user_id = ? AND quiz_kind = ?
            """
            res_total_first = db_helper.search_fetchall(conn, cursor, query_total_first, field=(user_id, package_name))
            total_first = res_total_first[0]["total"] if res_total_first and res_total_first[0]["total"] else 0

            # Not completed quizzes = total started - completed
            nc_quiz = total_first - c_quiz

            quiz_report[package_name] = {
                "finish_quiz": finish_quiz,
                "started_quiz": started_quiz,
                "c_quiz": c_quiz,
                "nc_quiz": nc_quiz
            }

        notifications_query = """
            SELECT n.id, n.title, n.description, n.added_by, n.priority, n.fullText, n.persian_date,
                   CASE WHEN EXISTS (
                       SELECT 1 FROM notification_reads nr
                       WHERE nr.notification_id = n.id AND nr.user_id = ?
                   ) THEN 1 ELSE 0 END AS is_read
            FROM notifications n
            WHERE (n.roles LIKE '%institute%' OR n.roles LIKE '%all%' OR n.user_id = ?)
            ORDER BY n.created_time DESC
        """
        cursor.execute(notifications_query, (user_id, user_id))
        columns = [col[0] for col in cursor.description]
        notifications = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cons_info = {
            "capacity": capacity_info,
            "stu_count": stu_count,
            "con_count": con_count,
            "stu": stu_package_count,
            "quiz_report": quiz_report
        }

        token = func_helper.get_tracking_code()
        return token, {"dashboard_info": cons_info, "notifications": notifications}, ""

    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "get_dashboard", str(e), request_data, user_info)
        return None, None, "اطلاعات داشبورد دریافت نشد."


def add_institute(conn, cursor, request_data, user_id):
    try:
        table = "ins"
        field = '([name], [user_id])'
        values = (request_data["name"], user_id)
        db_helper.insert_value(conn=conn, cursor=cursor, table_name=table, fields=field, values=values)

        func_helper.add_capacity_signup(conn, cursor, user_id, request_data["phone"])
        token = func_helper.get_tracking_code()

        return token, None, ""

    except Exception as e:
        conn.rollback()
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
        conn.rollback()
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
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "get_management_report", str(e),
                                        request_data,
                                        user_info)
        return None, None, "مشکل در دریافت گزارش مدیریتی رخ داده است."


# this function is for add consultant in ins
def add_consultant(conn, cursor, request_data, con_user_id, user_info):
    try:
        table = "con"
        field = '([first_name], [last_name], [user_id], [owner_user_id], [editor_id], [sex])'
        values = (
            request_data["first_name"], request_data["last_name"], con_user_id,
            user_info["user_id"], user_info["user_id"], request_data["sex"])
        db_helper.insert_value(conn=conn, cursor=cursor, table_name=table, fields=field,
                               values=values)
        token = func_helper.get_tracking_code()
        return token, None, "مشاور شما با موفقیت ثبت شد."
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "add_consultant", str(e), request_data, user_info)
        return None, None, "مشکلی در ثبت نهایی اطلاعات مشاور رخ داده است لطفا با پیشیبانی در ارتباط باشید."


# this function is for update the information of consultant
def change_consultant(conn, cursor, request_data, user_info):
    try:
        db_helper.update_record(conn, cursor, 'con',
                                ['first_name', 'last_name', 'sex', 'editor_id', 'edited_time'],
                                [request_data["first_name"], request_data["last_name"], request_data["sex"],
                                 request_data["user_id"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                'user_id = ?', [str(request_data["consultant_id"])])
        token = func_helper.get_tracking_code()
        return token, None, "اطلاعات مشاور شما با موفقیت تغییر کرد."
    except Exception as e:
        conn.rollback()
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
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "get_consultants", str(e), request_data, user_info)
        return None, [], "اطلاعات مشاورین دریافت نشد."


# this function for insert student to ins
def add_student(conn, cursor, request_data, stu_user_id, user_info):
    try:
        table = "stu"
        field = '([first_name], [last_name], [sex], [city], [consultant_user_id], [user_id], [owner_user_id], [adder_id], [birth_date])'
        values = (
            request_data["first_name"], request_data["last_name"], request_data["sex"], request_data["city"],
            request_data["con_id"], stu_user_id,
            user_info["user_id"], user_info["user_id"], request_data["birth_date"],)
        db_helper.insert_value(conn=conn, cursor=cursor, table_name=table, fields=field,
                               values=values)
        token = func_helper.get_tracking_code()
        return token, None, "دانش‌آموز شما با موفقیت ثبت شد."
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "add_student", str(e), request_data, user_info)
        return None, None, "مشکلی در افزودن دانش‌آموز رخ داده است."


# this function is for update the information of consultant
def change_student(conn, cursor, request_data, user_info):
    try:
        db_helper.update_record(conn, cursor, 'stu',
                                ['first_name', 'last_name', 'sex', 'city', 'consultant_user_id', 'editor_id',
                                 'birth_date', 'edited_time'],
                                [request_data["first_name"], request_data["last_name"], request_data["sex"],
                                 request_data["city"], request_data["con_id"], user_info["user_id"],
                                 request_data["birth_date"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                'user_id = ?', [str(request_data["student_id"])])
        token = func_helper.get_tracking_code()
        return token, None, "اطلاعات دانش‌آموز شما با موفقیت تغییر کرد."
    except Exception as e:
        conn.rollback()
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
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "get_students", str(e), request_data, user_info)
        return None, [], "اطلاعات دانش‌آموزان دریافت نشد."


def change_user_info(conn, cursor, request_data, user_info):
    try:
        update_fields = ['name', 'edited_time']
        update_values = [request_data["name"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        pic = func_helper.save_base64_image(
            request_data.get("pic"),
            request_data.get("last_pic"),
            config.INS_PIC_DIR,
        )
        if pic is not None:
            update_fields.insert(1, 'logo')
            update_values.insert(1, pic)

        db_helper.update_record(conn, cursor, 'ins',
                                update_fields,
                                update_values,
                                'user_id = ?', [str(user_info["user_id"])])
        token = func_helper.get_tracking_code()
        response = {"name": request_data["name"]}
        if pic is not None:
            response["pic"] = pic
        return token, response, "اطلاعات شما با موفقیت تغییر یافت."
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "change_user_info", str(e), request_data,
                                        user_info)
        return None, None, "اطلاعات شما با موفقیت تغییر نیافت."


def change_user_image(conn, cursor, request_data, user_info):
    try:
        db_helper.update_record(conn, cursor, 'ins',
                                ['name', 'logo', 'edited_time'],
                                [request_data["name"], request_data["pic"],
                                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                'user_id = ?', [str(request_data["user_id"])])
        token = func_helper.get_tracking_code()
        return token, {"name": request_data["name"], "pic": request_data["pic"]}, "اطلاعات شما با موفقیت تغییر یافت."
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "change_user_image", str(e), request_data, user_info)

        return None, None, "اطلاعات شما با موفقیت تغییر نیافت."


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
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "change_user_voice", str(e), request_data, user_info)
        return None, None, "اطلاعات شما با موفقیت تغییر نیافت."


def change_setting(conn, cursor, request_data, user_info):
    try:
        if request_data["setting_id"] == "no setting":
            table = "setting"
            field = '([user_id], [description], [voice], [quiz_id])'
            values = (
                request_data["user_id"], request_data["description"], request_data["voice"], request_data["quiz_id"],)
            res_add_ins = db_helper.insert_value(conn=conn, cursor=cursor, table_name=table, fields=field,
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
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "change_setting", str(e), request_data, user_info)
        return None, None, "پیش اطلاعات اولیه آزمون شما تغییر نیافت."


def verify_user(conn, cursor, user_id):
    try:
        db_helper.update_record(conn, cursor, 'ins',
                                ['verify', 'edited_time'],
                                [1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                'user_id = ?', [str(user_id)])
        token = func_helper.get_tracking_code()
        query = '''
            SELECT i.ins_id, i.name, i.logo, u.phone
            FROM ins i
            INNER JOIN users u ON u.user_id = i.user_id
            WHERE i.user_id = ?
        '''
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=user_id)
        info_response = {"phone": res.phone, "user_id": user_id, "id": res.ins_id, "name": res.name, "role": "ins",
                         "pic": res.logo}
        return token, info_response, ""
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/ins", "verify_user", str(e), None,
                                        {"user_id": user_id})
        return None, None, "اطلاعات کاربر یافت نشد."


def change_student_access(conn, cursor, request_data, user_info):
    """
    Update student access permissions and manage capacity tracking for institute.
    
    Uses the reusable helper function func_helper.update_student_access_and_capacity.
    """
    return func_helper.update_student_access_and_capacity(
        conn=conn,
        cursor=cursor,
        request_data=request_data,
        user_info=user_info,
        role_type="ins",
        id_field="owner_user_id",
        end_point="ag_api/ins"
    )
