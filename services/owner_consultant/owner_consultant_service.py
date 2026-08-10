import json
from datetime import datetime

import config
import helper.db.db_helper as db_helper
import helper.func_helper as func_helper


def get_info(conn, cursor, user_id):
    try:
        query = 'SELECT wCon_id, phone, first_name, last_name, logo FROM wCon WHERE user_id = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=user_id)
        token = func_helper.get_tracking_code()
        user_info = {"phone": res.phone, "user_id": user_id, "id": res.wCon_id, "first_name": res.first_name, "role": "wCon",
                "last_name": res.last_name, "pic": res.logo}
        return token, user_info
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/wCon", "get_info", str(e), {},
                                        {"user_id": user_id})
        return None, None


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
            "stu_count": "SELECT COUNT(*) AS total FROM stu WHERE con_id = ?"
        }

        results = {key: db_helper.search_fetchall(conn, cursor, query, field=user_id) for key, query in queries.items()}

        stu_count = results["stu_count"][0]["total"] if results["stu_count"] else 0

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

        quiz_report = {}
        for package_name in ["AG", "SCL"]:
            total_quizzes = package_quiz_count.get(package_name, 0)

            query_finish_quiz = """
                SELECT COUNT(DISTINCT user_id) AS total 
                FROM quiz_answer 
                WHERE con_id = ? AND quiz_kind = ? AND state = 2 AND quiz_id = ?
            """
            res_finish_quiz = db_helper.search_fetchall(conn, cursor, query_finish_quiz,
                                                        field=(user_id, package_name, total_quizzes))
            finish_quiz = res_finish_quiz[0]["total"] if res_finish_quiz and res_finish_quiz[0]["total"] else 0

            query_started_quiz = """
                SELECT COUNT(DISTINCT user_id) AS total 
                FROM quiz_answer 
                WHERE con_id = ? AND quiz_kind = ?
            """
            res_started_quiz = db_helper.search_fetchall(conn, cursor, query_started_quiz,
                                                         field=(user_id, package_name))
            started_quiz = res_started_quiz[0]["total"] if res_started_quiz and res_started_quiz[0]["total"] else 0

            query_c_quiz = """
                SELECT COUNT(*) AS total 
                FROM quiz_answer 
                WHERE con_id = ? AND quiz_kind = ? AND state = 2
            """
            res_c_quiz = db_helper.search_fetchall(conn, cursor, query_c_quiz, field=(user_id, package_name))
            c_quiz = res_c_quiz[0]["total"] if res_c_quiz and res_c_quiz[0]["total"] else 0

            query_total_first = """
                SELECT COUNT(*) AS total 
                FROM quiz_answer 
                WHERE con_id = ? AND quiz_kind = ?
            """
            res_total_first = db_helper.search_fetchall(conn, cursor, query_total_first, field=(user_id, package_name))
            total_first = res_total_first[0]["total"] if res_total_first and res_total_first[0]["total"] else 0

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
            WHERE (roles LIKE '%ownerConsultant%' OR roles LIKE '%all%' OR user_id = ?)
            ORDER BY created_time DESC
        """
        cursor.execute(notifications_query, (user_id,))
        columns = [col[0] for col in cursor.description]
        notifications = [dict(zip(columns, row)) for row in cursor.fetchall()]

        token = func_helper.get_tracking_code()
        cons_info = {
            "capacity": capacity_info,
            "stu_count": stu_count,
            "stu": stu_package_count,
            "quiz_report": quiz_report
        }

        return token, cons_info, notifications

    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/wCon", "get_dashboard", str(e), request_data,
                                        user_info)
        return None, {}, []


def add_owner_consultant(conn, cursor, request_data, user_id):
    try:
        table = "wCon"
        sex = request_data.get("sex")
        if not sex:
            sex = 1
        field = '([first_name], [last_name], [phone], [password], [user_id], [sex])'
        values = (
            request_data["first_name"], request_data["last_name"], request_data["phone"],
            func_helper.encrypt_password(request_data["password"]),
            user_id, sex)
        db_helper.insert_value(conn=conn, cursor=cursor, table_name=table, fields=field,
                               values=values)
        func_helper.add_capacity_signup(conn, cursor, user_id, request_data["phone"])
        token = func_helper.get_tracking_code()
        return token
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/wCon", "add_owner_consultant", str(e), request_data,
                                        {"user_id": user_id, "phone": request_data["phone"]})
        return None


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
        return token, report_info
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/wCon", "get_report", str(e), request_data, user_info)
        return None, []


def get_management_report(conn, cursor, request_data, user_info):
    try:
        query = 'SELECT stu_id, user_id, phone, first_name, last_name, sex, city, access, password FROM stu WHERE con_id = ?'
        res = db_helper.search_allin_table(conn=conn, cursor=cursor, query=query, field=user_info["user_id"])

        report_info = []

        package_quiz_count = {
            "AG": 7,
            "SCL": 4
        }

        if res is not None:
            for stu in res:
                raw_access = getattr(stu, "access", None) or "{}"
                try:
                    access_data = json.loads(raw_access) if isinstance(raw_access, str) else (raw_access or {})
                except (json.JSONDecodeError, TypeError):
                    access_data = {}

                access_state = {}
                for package_name in func_helper.PACKAGES_DATA.keys():
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
                    "access_state": access_state,
                }
                report_info.append(info_response)
        token = func_helper.get_tracking_code()
        return token, report_info
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/wCon", "get_management_report", str(e),
                                        request_data, user_info)
        return None, None


def add_student(conn, cursor, request_data, stu_user_id, user_info):
    try:
        table = "stu"
        field = '([user_id], [first_name], [last_name], [phone], [password], [sex], [city], [ins_id], [con_id], [adder_id], [editor_id], [birth_date], [ins_role])'
        values = (
            stu_user_id, request_data["first_name"], request_data["last_name"], request_data["phone"],
            func_helper.encrypt_password(request_data["password"]), request_data["sex"], request_data["city"],
            request_data["user_id"],
            user_info["user_id"], user_info["user_id"], user_info["user_id"], request_data["birth_date"], "wCon",)
        db_helper.insert_value(conn=conn, cursor=cursor, table_name=table, fields=field,
                               values=values)
        token = func_helper.get_tracking_code()
        return token
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/wCon", "add_student", str(e), request_data, user_info)
        return None


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
        return token
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/wCon", "change_student", str(e), request_data, user_info)
        return None


def change_comment(conn, cursor, request_data, user_info):
    try:
        db_helper.update_record(conn, cursor, 'stu',
                                ['comment', 'editor_id', 'edited_time'],
                                [request_data["consultant_comment"], user_info["user_id"],
                                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                'user_id = ?', [str(request_data["student_id"])])
        token = func_helper.get_tracking_code()
        return token
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/wCon", "change_comment", str(e), request_data, user_info)
        return None


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

        db_helper.update_record(conn, cursor, 'wCon',
                                update_fields,
                                update_values,
                                'user_id = ?', [str(user_info["user_id"])])
        token = func_helper.get_tracking_code()
        response = {"first_name": request_data["first_name"], "last_name": request_data["last_name"]}
        if pic is not None:
            response["pic"] = pic
        return token, response
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/wCon", "change_user_info", str(e), request_data,
                                        user_info)
        return None, {}


def get_students(conn, cursor, request_data, user_info):
    try:
        query = 'SELECT first_name, last_name FROM wCon WHERE user_id = ?'
        res_con = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=user_info["user_id"])
        con_name = ""
        if res_con and len(res_con) >= 2:
            con_name = f"{res_con.first_name} {res_con.last_name}"
        query = 'SELECT stu_id, user_id, phone, first_name, last_name, password, sex, city, birth_date, access, con_id FROM stu WHERE con_id = ?'
        res = db_helper.search_allin_table(conn=conn, cursor=cursor, query=query, field=user_info["user_id"])
        stu_info = []
        if res is not None:
            for stu in res:
                user_info = {"stu_id": stu.stu_id, "user_id": stu.user_id, "phone": stu.phone, "first_name": stu.first_name,
                        "last_name": stu.last_name, "con_name": con_name,
                        "con_id": stu.con_id, "password": func_helper.decrypt_password(stu.password), "sex": stu.sex,
                        "city": stu.city, "full_name": stu.first_name + " " + stu.last_name,
                        "birth_date": stu.birth_date, "access": json.loads(stu.access)}
                stu_info.append(user_info)
        token = func_helper.get_tracking_code()
        return token, stu_info
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/wCon", "get_students", str(e), request_data, user_info)
        return None, []


def change_user_voice(conn, cursor, request_data, user_info):
    try:
        method_type = "UPDATE"
        token = func_helper.get_tracking_code()
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
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/wCon", "change_user_voice", str(e), request_data,
                                        user_info)
        return {"status": 200, "tracking_code": None, "method_type": None,
                "response": {"message": "اطلاعات شما با موفقیت تغییر یافت."}}


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
            return token
        else:
            db_helper.update_record(conn, cursor, 'setting',
                                    ['description', 'edited_time'],
                                    [request_data["description"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                    'setting_id = ?', [str(request_data["setting_id"])])
            token = func_helper.get_tracking_code()
            return token
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/wCon", "change_setting", str(e), request_data, user_info)
        return None


def verify_user(conn, cursor, user_id):
    try:
        db_helper.update_record(conn, cursor, 'wCon',
                                ['verify', 'edited_time'],
                                [1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                'user_id = ?', [str(user_id)])
        token = func_helper.get_tracking_code()
        query = 'SELECT wCon_id, phone, first_name, last_name, logo FROM wCon WHERE user_id = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=user_id)
        user_info = {"phone": res.phone, "user_id": user_id, "id": res.wCon_id, "first_name": res.first_name, "role": "wCon",
                "last_name": res.last_name, "pic": res.logo}
        return token, user_info
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/wCon", "verify_user", str(e), None,
                                        {"user_id": user_id})
        return None, None


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
        role_type="wCon",
        id_field="ins_id",
        end_point="ag_api/wCon"
    )


