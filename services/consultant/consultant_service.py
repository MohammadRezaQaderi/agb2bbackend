import json
from datetime import datetime

import helper.db.db_helper as db_helper
import helper.func_helper as func_helper


def get_info(conn, cursor, user_id):
    try:
        query = 'SELECT con_id, phone, first_name, last_name, ins_id, ins_role FROM con WHERE user_id = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=user_id)
        if res.ins_role == "ins":
            query_ins = 'SELECT name, logo FROM ins WHERE user_id = ?'
            res_ins = db_helper.search_table(conn=conn, cursor=cursor, query=query_ins, field=res.ins_id)
        else:
            query_ins = 'SELECT name, logo FROM sch WHERE user_id = ?'
            res_ins = db_helper.search_table(conn=conn, cursor=cursor, query=query_ins, field=res.ins_id)
        token = func_helper.get_tracking_code()
        response_info = {"phone": res.phone, "user_id": user_id, "id": res.con_id, "first_name": res.first_name,
                         "last_name": res.last_name, "role": 'con', "name": res_ins.name, "pic": res_ins.logo,
                         "ins_id": res.ins_id}
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

        query = 'SELECT ins_id FROM con WHERE user_id = ?'
        res_info_ins = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=user_id)

        query_capacity = """
                    SELECT package_name, allowed, used
                    FROM capacity_package
                    WHERE user_id = ?
                """
        res_capacity = db_helper.search_fetchall(conn=conn, cursor=cursor, query=query_capacity,
                                                 field=res_info_ins.ins_id)

        capacity_info = {
            row["package_name"]: {"allowed": row["allowed"], "used": row["used"]}
            for row in res_capacity
        }

        package_quiz_count = {
            "AG": 7,
            "SCL": 4
        }

        queries = {
            "stu_count": "SELECT COUNT(*) AS total FROM stu WHERE con_id = ?"
        }

        results = {key: db_helper.search_fetchall(conn, cursor, query, field=user_id) for key, query in queries.items()}

        stu_count = results["stu_count"][0]["total"] if results["stu_count"] else 0

        stu_package_count = func_helper.get_student_package_access_counts(
            conn, cursor, user_id, "consultant_user_id"
        )
        if stu_package_count is None:
            query_stu_access = "SELECT access FROM stu WHERE con_id = ?"
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
                WHERE con_id = ? AND quiz_kind = ? AND state = 2 AND quiz_id = ?
            """
            res_finish_quiz = db_helper.search_fetchall(conn, cursor, query_finish_quiz,
                                                        field=(user_id, package_name, total_quizzes))
            finish_quiz = res_finish_quiz[0]["total"] if res_finish_quiz and res_finish_quiz[0]["total"] else 0

            # Count students who started at least one quiz
            query_started_quiz = """
                SELECT COUNT(DISTINCT user_id) AS total 
                FROM quiz_attempt 
                WHERE con_id = ? AND quiz_kind = ?
            """
            res_started_quiz = db_helper.search_fetchall(conn, cursor, query_started_quiz,
                                                         field=(user_id, package_name))
            started_quiz = res_started_quiz[0]["total"] if res_started_quiz and res_started_quiz[0]["total"] else 0

            # Count total completed quizzes (state = 2) for this package
            query_c_quiz = """
                SELECT COUNT(*) AS total 
                FROM quiz_attempt 
                WHERE con_id = ? AND quiz_kind = ? AND state = 2
            """
            res_c_quiz = db_helper.search_fetchall(conn, cursor, query_c_quiz, field=(user_id, package_name))
            c_quiz = res_c_quiz[0]["total"] if res_c_quiz and res_c_quiz[0]["total"] else 0

            # Count total started quizzes (any state) for this package
            query_total_first = """
                SELECT COUNT(*) AS total 
                FROM quiz_attempt 
                WHERE con_id = ? AND quiz_kind = ?
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
            SELECT id, title, description, added_by, priority, fullText, persian_date
            FROM notifications
            WHERE (roles LIKE '%con%' OR roles LIKE '%all%' OR user_id = ?)
            ORDER BY created_time DESC
        """
        cursor.execute(notifications_query, (user_id,))
        columns = [col[0] for col in cursor.description]
        notifications = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cons_info = {
            "capacity": capacity_info,
            "stu_count": stu_count,
            "stu": stu_package_count,
            "quiz_report": quiz_report
        }

        token = func_helper.get_tracking_code()
        return token, {"dashboard_info": cons_info, "notifications": notifications}, ""

    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/con", "get_dashboard", str(e), request_data, user_info)
        return None, None, "اطلاعات داشبورد دریافت نشد."


def get_report(conn, cursor, request_data, user_info):
    try:
        query = 'SELECT stu_id, user_id, phone, first_name, last_name, sex, city, access, comment, password FROM stu WHERE con_id = ?'
        res = db_helper.search_allin_table(conn=conn, cursor=cursor, query=query, field=user_info["user_id"])
        report_info = []
        if res is not None:
            for stu in res:
                raw_access = getattr(stu, "access", None) or "{}"
                try:
                    access_data = json.loads(raw_access) if isinstance(raw_access, str) else (raw_access or {})
                except (json.JSONDecodeError, TypeError):
                    access_data = {}
                user_info = {"id": stu.stu_id, "student_id": stu.user_id, "phone": stu.phone, "first_name": stu.first_name,
                        "last_name": stu.last_name,
                        "password": func_helper.decrypt_password(stu.password), "sex": stu.sex, "city": stu.city,
                        "access": access_data, "full_name": stu.first_name + " " + stu.last_name,
                        "consultant_comment": stu.comment, "report_id": stu.user_id}
                report_info.append(user_info)
        token = func_helper.get_tracking_code()
        return token, report_info, ""
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/con", "get_report", str(e), request_data, user_info)
        return None, [], "مشکل در دریافت گزارش رخ داده است."


def get_management_report(conn, cursor, request_data, user_info):
    try:
        # Fetch basic student user_info for this consultant
        query = 'SELECT stu_id, user_id, phone, first_name, last_name, sex, city, access, password FROM stu WHERE con_id = ?'
        res = db_helper.search_allin_table(conn=conn, cursor=cursor, query=query, field=user_info["user_id"])

        report_info = []

        # Number of quizzes per package for state calculation
        package_quiz_count = {
            "AG": 7,
            "SCL": 4
        }

        if res is not None:
            for stu in res:
                # Parse student's access JSON safely
                raw_access = getattr(stu, "access", None) or "{}"
                try:
                    access_data = json.loads(raw_access) if isinstance(raw_access, str) else (raw_access or {})
                except (json.JSONDecodeError, TypeError):
                    access_data = {}

                # Build per-package permission and quiz state
                access_state = {}
                for package_name in func_helper.PACKAGES_DATA.keys():
                    package_info = access_data.get(package_name, {})

                    # Default permission is 0 (no access)
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

                    state = "-"
                    last_quiz_id = 0
                    if permission == 1:
                        total_quizzes = package_quiz_count.get(package_name)

                        if total_quizzes:
                            query_quiz = (
                                'SELECT state, quiz_id FROM quiz_attempt '
                                'WHERE user_id = ? AND quiz_kind = ? ORDER BY quiz_id ASC'
                            )
                            res_quiz = db_helper.search_allin_table(
                                conn=conn,
                                cursor=cursor,
                                query=query_quiz,
                                field=(stu.user_id, package_name)
                            )
                            last_quiz_id = 1
                            if not res_quiz or len(res_quiz) == 0:
                                state = "not-started"
                            else:
                                last_quiz = res_quiz[-1]
                                last_state = getattr(last_quiz, "state", None)
                                last_quiz_id = getattr(last_quiz, "quiz_id", None)

                                if last_state == 2 and last_quiz_id == total_quizzes:
                                    state = "completed"
                                else:
                                    state = "in-progress"

                    access_state[package_name] = {
                        "permission": permission,
                        "state": state,
                        "current_quiz_name": func_helper.get_quiz_name(package_name, last_quiz_id)
                    }

                info_response = {
                    "student_id": stu.user_id,
                    "first_name": stu.first_name,
                    "last_name": stu.last_name,
                    "full_name": stu.first_name + " " + stu.last_name,
                    "access": access_data,
                    "access_state": access_state,
                }
                report_info.append(info_response)
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
        query = 'SELECT first_name, last_name FROM con WHERE user_id = ?'
        res_con = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=user_info["user_id"])
        con_name = ""
        if res_con and len(res_con) >= 2:
            con_name = f"{res_con.first_name} {res_con.last_name}"
        query = 'SELECT stu_id, user_id, phone, first_name, last_name, password, sex, city, birth_date, access FROM stu WHERE con_id = ?'
        res = db_helper.search_allin_table(conn=conn, cursor=cursor, query=query, field=user_info["user_id"])
        stu_info = []
        if len(res) != 0:
            for stu in res:
                # query_quiz = 'SELECT state, quiz_id FROM quiz_attempt WHERE user_id = ? ORDER BY quiz_id asc'
                # res_quiz = db_helper.search_allin_table(conn=conn, cursor=cursor, query=query_quiz, field=stu.user_id)
                # status = ''
                # if len(res_quiz) == 0:
                #     status = "در انتظار شروع آزمون"
                # else:
                #     state_of_last_quiz = res_quiz[-1].state
                #     quiz_answered = res_quiz[-1].quiz_id
                #     if state_of_last_quiz == 1:
                #         status = "آزمون " + func_helper.AG_QUIZ_NAME_TITLE[quiz_answered - 1] + " در حال انجام است"
                #     else:
                #         if len(res_quiz) == 7 and state_of_last_quiz == 2:
                #             status = "آزمون‌ها به پایان رسیده است."
                #         else:
                #             status = "آزمون " + func_helper.AG_QUIZ_NAME_TITLE[quiz_answered - 1] + " به پایان رسیده است"
                user_info = {"stu_id": stu.stu_id, "user_id": stu.user_id, "phone": stu.phone, "first_name": stu.first_name,
                        "last_name": stu.last_name, "con_name": con_name,
                        "full_name": stu.first_name + " " + stu.last_name,
                        "con_id": user_info["user_id"], "password": func_helper.decrypt_password(stu.password), "sex": stu.sex,
                        "city": stu.city, "birth_date": stu.birth_date, "access": json.loads(stu.access)}
                stu_info.append(user_info)
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
