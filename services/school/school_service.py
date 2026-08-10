import json
import uuid
from datetime import datetime

import helper.db.db_helper as db_helper
import helper.func_helper as func_helper


def select_school_info(conn, cursor, user_id):
    try:
        query = 'SELECT sch_id, name, logo, phone FROM sch WHERE user_id = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=user_id)
        token = str(uuid.uuid4())
        info_response = {"phone": res.phone, "user_id": user_id, "id": res.sch_id, "name": res.name, "role": "sch",
                         "pic": res.logo}
        return token, info_response
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/sch", "select_school_info", str(e), None,
                                        {"user_id": user_id})
        return None, None


def select_sch_dashboard(conn, cursor, request_data, info):
    """
    Fetches dashboard data for school users, including capacity info,
    student/consultant counts, quiz progress, and notifications.
    """
    try:
        user_id = info["user_id"]

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
            "stu_count": "SELECT COUNT(*) AS total FROM stu WHERE ins_id = ?",
            "con_count": "SELECT COUNT(*) AS total FROM con WHERE ins_id = ?"
        }

        results = {key: db_helper.search_fetchall(conn, cursor, query, field=user_id) for key, query in queries.items()}

        stu_count = results["stu_count"][0]["total"] if results["stu_count"] else 0
        con_count = results["con_count"][0]["total"] if results["con_count"] else 0

        query_stu_access = "SELECT access FROM stu WHERE ins_id = ?"
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
                FROM quiz_answer 
                WHERE ins_id = ? AND quiz_kind = ? AND state = 2 AND quiz_id = ?
            """
            res_finish_quiz = db_helper.search_fetchall(conn, cursor, query_finish_quiz,
                                                        field=(user_id, package_name, total_quizzes))
            finish_quiz = res_finish_quiz[0]["total"] if res_finish_quiz and res_finish_quiz[0]["total"] else 0

            # Count students who started at least one quiz
            query_started_quiz = """
                SELECT COUNT(DISTINCT user_id) AS total 
                FROM quiz_answer 
                WHERE ins_id = ? AND quiz_kind = ?
            """
            res_started_quiz = db_helper.search_fetchall(conn, cursor, query_started_quiz,
                                                         field=(user_id, package_name))
            started_quiz = res_started_quiz[0]["total"] if res_started_quiz and res_started_quiz[0]["total"] else 0

            # Count total completed quizzes (state = 2) for this package
            query_c_quiz = """
                SELECT COUNT(*) AS total 
                FROM quiz_answer 
                WHERE ins_id = ? AND quiz_kind = ? AND state = 2
            """
            res_c_quiz = db_helper.search_fetchall(conn, cursor, query_c_quiz, field=(user_id, package_name))
            c_quiz = res_c_quiz[0]["total"] if res_c_quiz and res_c_quiz[0]["total"] else 0

            # Count total started quizzes (any state) for this package
            query_total_first = """
                SELECT COUNT(*) AS total 
                FROM quiz_answer 
                WHERE ins_id = ? AND quiz_kind = ?
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
            WHERE (roles LIKE '%school%' OR roles LIKE '%all%' OR user_id = ?)
            ORDER BY created_time DESC
        """
        cursor.execute(notifications_query, (user_id,))
        columns = [col[0] for col in cursor.description]
        notifications = [dict(zip(columns, row)) for row in cursor.fetchall()]

        sch_info = {
            "capacity": capacity_info,
            "stu_count": stu_count,
            "con_count": con_count,
            "stu": stu_package_count,
            "quiz_report": quiz_report
        }

        token = str(uuid.uuid4())
        return token, sch_info, notifications

    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/sch", "select_sch_dashboard", str(e), request_data, info)
        return None, {}, []


def insert_school(conn, cursor, request_data, user_id):
    try:
        table = "sch"
        field = '([name], [phone], [password], [user_id])'
        values = (request_data["name"], request_data["phone"], func_helper.encrypt_password(request_data["password"]), user_id,)
        db_helper.insert_value(conn=conn, cursor=cursor, table_name=table, fields=field,
                               values=values)
        func_helper.add_capacity_signup(conn, cursor, user_id, request_data["phone"])
        token = str(uuid.uuid4())
        return token
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/sch", "insert_school", str(e), request_data,
                                        {"user_id": user_id, "phone": request_data["phone"]})
        return None


def select_sch_report(conn, cursor, request_data, info):
    try:
        query = 'SELECT stu_id, user_id, phone, first_name, last_name, sex, city, access, comment, password, con_id FROM stu WHERE ins_id = ?'
        res = db_helper.search_allin_table(conn=conn, cursor=cursor, query=query, field=info["user_id"])
        report_info = []
        if res is not None:
            for stu in res:
                query = 'SELECT first_name, last_name FROM con WHERE user_id = ?'
                res_con = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=stu.con_id)
                con_name = ""
                if res_con and len(res_con) >= 2:
                    con_name = f"{res_con.first_name} {res_con.last_name}"
                raw_access = getattr(stu, "access", None) or "{}"
                try:
                    access_data = json.loads(raw_access) if isinstance(raw_access, str) else (raw_access or {})
                except (json.JSONDecodeError, TypeError):
                    access_data = {}
                info_response = {"id": stu.stu_id, "student_id": stu.user_id, "phone": stu.phone,
                                 "first_name": stu.first_name,
                                 "last_name": stu.last_name, "con_name": con_name,
                                 "password": func_helper.decrypt_password(stu.password), "sex": stu.sex, "city": stu.city,
                                 "access": access_data, "full_name": stu.first_name + " " + stu.last_name,
                                 "consultant_comment": stu.comment, "report_id": stu.user_id}
                report_info.append(info_response)
        token = str(uuid.uuid4())
        return token, report_info
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/sch", "select_sch_report", str(e), request_data, info)
        return None, []


def select_sch_management_report(conn, cursor, request_data, info):
    try:
        # Fetch basic student info for this school
        query = 'SELECT stu_id, user_id, phone, first_name, last_name, sex, city, access, password, con_id FROM stu WHERE ins_id = ?'
        res = db_helper.search_allin_table(conn=conn, cursor=cursor, query=query, field=info["user_id"])

        report_info = []

        # Number of quizzes per package for state calculation
        package_quiz_count = {
            "AG": 7,
            "SCL": 4
        }

        if res is not None:
            for stu in res:
                # Resolve consultant name (if any)
                query_con = 'SELECT first_name, last_name FROM con WHERE user_id = ?'
                res_con = db_helper.search_table(conn=conn, cursor=cursor, query=query_con, field=stu.con_id)
                con_name = ""
                if res_con and len(res_con) >= 2:
                    con_name = f"{res_con.first_name} {res_con.last_name}"

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
                                'SELECT state, quiz_id FROM quiz_answer '
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
                    "con_name": con_name,
                    "access_state": access_state,
                }
                report_info.append(info_response)
        token = str(uuid.uuid4())
        return token, report_info
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/sch", "select_sch_management_report", str(e),
                                        request_data,
                                        info)
        return None, []


# this function is add consultant in school
def insert_sch_consultant(conn, cursor, request_data, con_user_id, info):
    try:
        table = "con"
        field = '([first_name], [last_name], [phone], [password], [user_id], [ins_id], [editor_id], [ins_role], [sex])'
        values = (
            request_data["first_name"], request_data["last_name"], request_data["phone"],
            func_helper.encrypt_password(request_data["password"]),
            con_user_id, info["user_id"], info["user_id"], "sch", request_data["sex"])
        db_helper.insert_value(conn=conn, cursor=cursor, table_name=table, fields=field,
                               values=values)
        token = str(uuid.uuid4())
        return token, "مشاور شما با موفقیت ثبت شد."
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/sch", "insert_sch_consultant", str(e), request_data, info)
        return None, "مشکلی در ثبت نهایی اطلاعات مشاور رخ داده است لطفا با پیشیبانی در ارتباط باشید."


# this function is for update the information of consultant
def update_sch_consultant(conn, cursor, request_data, info):
    try:
        db_helper.update_record(conn, cursor, 'con',
                                ['first_name', 'last_name', 'sex', 'editor_id', 'edited_time'],
                                [request_data["first_name"], request_data["last_name"], request_data["sex"],
                                 request_data["user_id"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                'user_id = ?', [str(request_data["consultant_id"])])
        token = str(uuid.uuid4())
        return token, "اطلاعات مشاور شما با موفقیت تغییر کرد."
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/sch", "update_sch_consultant", str(e), request_data, info)
        return None, "مشکلی در ثبت نهایی اطلاعات مشاور رخ داده است لطفا با پیشیبانی در ارتباط باشید."


# this function use for get consultant of sch for list of consultants and add students cons pick filed
def select_sch_consultant(conn, cursor, request_data, info):
    try:
        query = 'SELECT con_id, user_id, phone, first_name, last_name, password, sex FROM con WHERE ins_id = ?'
        res = db_helper.search_allin_table(conn=conn, cursor=cursor, query=query, field=info["user_id"])
        cons_info = []
        if res is not None:
            for con in res:
                info_response = {"con_id": con.con_id, "user_id": con.user_id, "phone": con.phone,
                                 "first_name": con.first_name, "sex": con.sex,
                                 "full_name": con.first_name + " " + con.last_name,
                                 "last_name": con.last_name, "password": func_helper.decrypt_password(con.password)}
                cons_info.append(info_response)
        token = str(uuid.uuid4())
        return token, cons_info
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/sch", "select_sch_consultant", str(e), request_data, info)
        return None, []


# this function for insert student to school
def insert_sch_student(conn, cursor, request_data, stu_user_id, info):
    try:
        table = "stu"
        field = '([first_name], [last_name], [phone], [password], [sex], [city], [con_id], [user_id], [ins_id], [adder_id], [birth_date], [ins_role])'
        values = (
            request_data["first_name"], request_data["last_name"], request_data["phone"],
            func_helper.encrypt_password(request_data['password']),
            request_data["sex"], request_data["city"],
            request_data["con_id"], stu_user_id, info["user_id"], info["user_id"], request_data["birth_date"], "sch",)
        db_helper.insert_value(conn=conn, cursor=cursor, table_name=table, fields=field,
                               values=values)
        token = str(uuid.uuid4())
        return token
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/sch", "insert_sch_student", str(e), request_data, info)
        return None


# this function is for update the information of consultant
def update_sch_student(conn, cursor, request_data, info):
    try:
        db_helper.update_record(conn, cursor, 'stu',
                                ['first_name', 'last_name', 'sex', 'city', 'con_id', 'editor_id',
                                 'birth_date', 'edited_time'],
                                [request_data["first_name"], request_data["last_name"], request_data["sex"],
                                 request_data["city"], request_data["con_id"], info["user_id"],
                                 request_data["birth_date"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                'user_id = ?', [str(request_data["student_id"])])
        token = str(uuid.uuid4())
        return token
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/sch", "update_sch_student", str(e), request_data, info)
        return None


# this function use for get students of sch for list of students
def select_sch_student(conn, cursor, request_data, info):
    try:
        query = 'SELECT stu_id, user_id, phone, first_name, last_name, password, sex, city, birth_date, access, con_id FROM stu WHERE ins_id = ?'
        res = db_helper.search_allin_table(conn=conn, cursor=cursor, query=query, field=info["user_id"])
        stu_info = []
        if len(res) != 0:
            for stu in res:
                query = 'SELECT first_name, last_name FROM con WHERE user_id = ?'
                res_con = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=stu.con_id)
                con_name = ""
                if res_con and len(res_con) >= 2:
                    con_name = f"{res_con.first_name} {res_con.last_name}"
                # query_quiz = 'SELECT state, quiz_id FROM quiz_answer WHERE user_id = ? ORDER BY quiz_id asc'
                # res_quiz = db_helper.search_allin_table(conn=conn, cursor=cursor, query=query_quiz, field=stu.user_id)
                # if len(res_quiz) == 0:
                #     status = "در انتظار شروع آمون"
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
                info_response = {"stu_id": stu.stu_id, "user_id": stu.user_id, "phone": stu.phone,
                                 "first_name": stu.first_name, "full_name": stu.first_name + " " + stu.last_name,
                                 "last_name": stu.last_name, "con_name": con_name,
                                 "con_id": stu.con_id, "password": func_helper.decrypt_password(stu.password), "sex": stu.sex,
                                 "city": stu.city,
                                 "birth_date": stu.birth_date, "access": json.loads(stu.access)}
                stu_info.append(info_response)
        token = str(uuid.uuid4())
        return token, stu_info
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/sch", "select_sch_student", str(e), request_data, info)
        return None, []


def update_sch_user_profile(conn, cursor, request_data, info):
    try:
        db_helper.update_record(conn, cursor, 'sch',
                                ['name', 'edited_time'],
                                [request_data["name"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                'user_id = ?', [str(info["user_id"])])
        token = str(uuid.uuid4())
        return token, {"name": request_data["name"]}
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/sch", "update_sch_user_profile", str(e), request_data,
                                        info)
        return None, {}


def update_user_sch_pic(conn, cursor, request_data, info):
    try:
        method_type = "UPDATE"
        db_helper.update_record(conn, cursor, 'sch',
                                ['name', 'logo', 'edited_time'],
                                [request_data["name"], request_data["pic"],
                                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                'user_id = ?', [str(request_data["user_id"])])
        token = str(uuid.uuid4())
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": {"name": request_data["name"], "pic": request_data["pic"]},
                             "message": "اطلاعات شما با موفقیت تغییر یافت."}}
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/sch", "update_user_sch_pic", str(e), request_data, info)

        return {"status": 200, "tracking_code": None, "method_type": None,
                "response": {"data": {"name": request_data["name"], "pic": request_data["pic"]},
                             "message": "اطلاعات شما با موفقیت تغییر نیافت."}}


def update_user_sch_voice(conn, cursor, request_data, info):
    try:
        method_type = "UPDATE"
        token = str(uuid.uuid4())
        if request_data["setting_id"] == "no setting":
            table = "setting"
            field = '([user_id], [description], [voice], [quiz_id])'
            values = (
                request_data["user_id"], request_data["description"], request_data["voice"], request_data["quiz_id"],)
            db_helper.insert_value(conn=conn, cursor=cursor, table_name=table, fields=field,
                                   values=values)
            return {"status": 200, "tracking_code": token, "method_type": method_type,
                    "response": {"message": "اطلاعات شما با موفقیت تغییر یافت."}}
        else:
            db_helper.update_record(conn, cursor, 'setting',
                                    ['description', 'voice', 'edited_time'],
                                    [request_data["description"], request_data["voice"],
                                     datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                    'setting_id = ?', [str(request_data["setting_id"])])
            return {"status": 200, "tracking_code": token, "method_type": method_type,
                    "response": {"message": "اطلاعات شما با موفقیت تغییر یافت."}}
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/sch", "update_user_sch_voice", str(e), request_data, info)
        return {"status": 200, "tracking_code": None, "method_type": None,
                "response": {"message": "اطلاعات شما با موفقیت تغییر یافت."}}


def update_sch_setting(conn, cursor, request_data, info):
    try:
        if request_data["setting_id"] == "no setting":
            table = "setting"
            field = '([user_id], [description], [voice], [quiz_id])'
            values = (
                request_data["user_id"], request_data["description"], request_data["voice"], request_data["quiz_id"],)
            db_helper.insert_value(conn=conn, cursor=cursor, table_name=table, fields=field,
                                   values=values)
            token = str(uuid.uuid4())
            return token
        else:
            db_helper.update_record(conn, cursor, 'setting',
                                    ['description', 'edited_time'],
                                    [request_data["description"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                    'setting_id = ?', [str(request_data["setting_id"])])
            token = str(uuid.uuid4())
            return token
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/sch", "update_sch_setting", str(e), request_data, info)
        return None


def update_sch_verify(conn, cursor, user_id):
    try:
        db_helper.update_record(conn, cursor, 'sch',
                                ['verify', 'edited_time'],
                                [1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                'user_id = ?', [str(user_id)])
        token = str(uuid.uuid4())
        query = 'SELECT sch_id, name, logo, phone FROM sch WHERE user_id = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=user_id)
        info = {"phone": res.phone, "user_id": user_id, "id": res.sch_id, "name": res.name, "role": "sch",
                "pic": res.logo}
        return token, info
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/sch", "update_sch_verify", str(e), None,
                                        {"user_id": user_id})
        return None, None


def update_sch_student_access(conn, cursor, request_data, info):
    """
    Update student access permissions and manage capacity tracking for school.
    
    Uses the reusable helper function func_helper.update_student_access_and_capacity.
    """
    return func_helper.update_student_access_and_capacity(
        conn=conn,
        cursor=cursor,
        request_data=request_data,
        info=info,
        role_type="sch",
        id_field="ins_id",
        end_point="ag_api/sch"
    )
