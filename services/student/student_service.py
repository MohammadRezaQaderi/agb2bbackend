import json
import uuid
from datetime import datetime

import redis

import helper.db.db_helper as db_helper
import helper.func_helper as func_helper
from helper.func_helper import service_exception_error_logging
from helper.quiz.ag_quiz_data_info import ag_quiz_info
from helper.quiz.scl_quiz_data_info import scl_quiz_info
from helper.quiz.quiz_data_extractor import get_quiz_table_info, get_quiz_info
from config import REDIS_QUEUE_NAME, REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB

AG_REPORT_INFO = {
    "t_state": {"name": "تجربی", "title": "t_state"},
    "r_state": {"name": "ریاضی", "title": "r_state"},
    "e_state": {"name": "انسانی", "title": "e_state"},
    "a_state": {"name": "هنر", "title": "a_state"},
    "m_state": {"name": "مدیریت", "title": "m_state"},
    "f_state": {"name": "کشاورزی", "title": "f_state"},
    "i_state": {"name": "صنعت", "title": "i_state"}
}


def _empty_access():
    return {"AG": {"permission": 0, "limit": 0}, "SCL": {"permission": 0, "limit": 0}}


def _load_access_from_json(raw_access):
    if not raw_access:
        return {}
    try:
        parsed = json.loads(raw_access) if isinstance(raw_access, str) else raw_access
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _load_student_access(conn, cursor, user_id):
    try:
        query = """
            SELECT package_name, permission, [limit]
            FROM student_package_access
            WHERE stu_user_id = ?
        """
        rows = db_helper.search_fetchall(conn=conn, cursor=cursor, query=query, field=user_id)
        if rows:
            access = {}
            for row in rows:
                access[str(row.get("package_name", "")).upper()] = {
                    "permission": int(row.get("permission") or 0),
                    "limit": int(row.get("limit") or 0),
                }
            return access
    except Exception as e:
        print(f"[student_package_access] student fallback: {e}")

    query_stu = 'SELECT access FROM stu WHERE user_id = ?'
    res_stu = db_helper.search_table(conn=conn, cursor=cursor, query=query_stu, field=user_id)
    return _load_access_from_json(getattr(res_stu, "access", None))


def _package_permission(access, kind):
    access_value = access.get(kind, {})
    if isinstance(access_value, dict):
        return int(access_value.get("permission") or 0), int(access_value.get("limit") or 0)
    if isinstance(access_value, bool):
        return (1 if access_value else 0), 0
    try:
        permission = int(access_value or 0)
    except (TypeError, ValueError):
        permission = 0
    return permission, permission


def select_student_info(conn, cursor, user_id):
    try:
        query = 'SELECT stu_id, user_id, phone, first_name, last_name, sex, city, access, ins_id, con_id, birth_date, ins_role FROM stu WHERE user_id = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=user_id)
        token = str(uuid.uuid4())
        if res.ins_role in ["ins", "sch"]:
            if res.ins_role == "ins":
                query_ins = 'SELECT name, logo, user_id FROM ins WHERE user_id = ?'
                res_ins = db_helper.search_table(conn=conn, cursor=cursor, query=query_ins, field=res.ins_id)
            else:
                query_ins = 'SELECT name, logo, user_id FROM sch WHERE user_id = ?'
                res_ins = db_helper.search_table(conn=conn, cursor=cursor, query=query_ins, field=res.ins_id)
            query_con = 'SELECT first_name, last_name FROM con WHERE user_id = ?'
            res_con = db_helper.search_table(conn=conn, cursor=cursor, query=query_con, field=res.con_id)
            con_name = ""
            if res_con and len(res_con) >= 2:
                con_name = f"{res_con.first_name} {res_con.last_name}"
            return token, {"phone": res.phone, "user_id": user_id, "id": res.stu_id, "first_name": res.first_name,
                           "last_name": res.last_name, "sex": res.sex, "city": res.city,
                           "access": res.access, "role": "stu", "name": res_ins.name, "con_name": con_name,
                           "pic": res_ins.logo, "ins_id": res_ins.user_id, }
        else:
            query_con = 'SELECT first_name, last_name FROM ocon WHERE user_id = ?'
            res_con = db_helper.search_table(conn=conn, cursor=cursor, query=query_con, field=res.con_id)
            con_name = ""
            if res_con and len(res_con) >= 2:
                con_name = f"{res_con.first_name} {res_con.last_name}"
            return token, {"phone": res.phone, "user_id": user_id, "id": res.stu_id, "first_name": res.first_name,
                           "last_name": res.last_name, "sex": res.sex, "city": res.city,
                           "access": res.access, "role": "stu", "name": "هدایت تحصیلی", "con_name": con_name,
                           "pic": None, "ins_id": res.con_id}
    except Exception as e:
        conn.rollback()
        service_exception_error_logging(conn, cursor, "ags_api/stu", "select_student_info", str(e), {},
                                        {"user_id": user_id})
        return None, {}


def select_stu_dashboard(conn, cursor, request_data, info):
    try:
        user_id = info["user_id"]

        def _safe_json_load(value):
            try:
                return json.loads(value) if value else value
            except Exception:
                return value

        stu_access = _load_student_access(conn, cursor, user_id)

        # Helper function to check if a product kind has access (permission and limit both 1)
        def _has_access(kind):
            """Check if user has access to a product kind. Returns (has_permission, has_limit)"""
            permission, limit = _package_permission(stu_access, kind)
            return permission == 1, limit == 1

        # Check access for AG and SCL
        ag_has_permission, ag_has_limit = _has_access("AG")
        scl_has_permission, scl_has_limit = _has_access("SCL")

        # Quiz progress (completed vs remaining) - calculate for each product kind separately
        quiz_progress = {}

        if ag_has_permission:
            ag_completed_query = """
                SELECT COUNT(*) AS completed
                FROM quiz_answer
                WHERE user_id = ? AND quiz_kind = ? AND state = 2
            """
            ag_completed_res = db_helper.search_fetchall(conn=conn, cursor=cursor, query=ag_completed_query,
                                                         field=(user_id, "AG"))
            ag_completed_count = ag_completed_res[0]["completed"] if ag_completed_res else 0
            ag_total_quizzes = len(get_quiz_table_info(kind="AG"))
            quiz_progress["AG"] = {
                "completed": ag_completed_count,
                "remaining": max(ag_total_quizzes - ag_completed_count, 0),
                "total": ag_total_quizzes,
            }

        if scl_has_permission:
            scl_completed_query = """
                SELECT COUNT(*) AS completed
                FROM quiz_answer
                WHERE user_id = ? AND quiz_kind = ? AND state = 2
            """
            scl_completed_res = db_helper.search_fetchall(conn=conn, cursor=cursor, query=scl_completed_query,
                                                          field=(user_id, "SCL"))
            scl_completed_count = scl_completed_res[0]["completed"] if scl_completed_res else 0
            scl_total_quizzes = len(get_quiz_table_info(kind="SCL"))
            quiz_progress["SCL"] = {
                "completed": scl_completed_count,
                "remaining": max(scl_total_quizzes - scl_completed_count, 0),
                "total": scl_total_quizzes,
            }

        # Latest computed scores (if any) - only if AG permission and limit is 1
        scores_info = None
        if ag_has_permission and ag_has_limit:
            scores_query = """
                SELECT TOP 1 brain_categories, brain_branches
                FROM scores
                WHERE user_id = ?
                ORDER BY edited_time DESC
            """
            scores_res = db_helper.search_fetchall(conn=conn, cursor=cursor, query=scores_query, field=user_id)
            if scores_res:
                score_row = scores_res[0]
                scores_info = {
                    "brain_categories": _safe_json_load(score_row.get("brain_categories")),
                    "brain_branches": _safe_json_load(score_row.get("brain_branches")),
                }

        # Result state (single row per user) - only if AG permission and limit is 1
        result_state_info = None
        if ag_has_permission and ag_has_limit:
            result_state_query = """
                SELECT t_state, r_state, e_state, a_state, m_state, f_state, i_state, edited_time
                FROM result_state
                WHERE user_id = ?
            """
            result_state_res = db_helper.search_fetchall(conn=conn, cursor=cursor, query=result_state_query,
                                                         field=user_id)
            if result_state_res:
                db_row = result_state_res[0]
                result_state_info = {}
                # Transform using AG_REPORT_INFO and add values from database
                for state_key in AG_REPORT_INFO.keys():
                    result_state_info[state_key] = {
                        **AG_REPORT_INFO[state_key],
                        "value": db_row.get(state_key)
                    }
                # Add edited_time separately
                result_state_info["edited_time"] = db_row.get("edited_time")

        # Guidance fields (hedayat_fields)
        # hedayat_fields_query = """
        #     SELECT TOP 1 suggested, other, created_time, edited_time
        #     FROM hedayat_fields
        #     WHERE user_id = ?
        #     ORDER BY edited_time DESC
        # """
        # hedayat_fields_res = db_helper.search_fetchall(conn=conn, cursor=cursor, query=hedayat_fields_query,
        #                                                field=user_id)
        # hedayat_fields_info = None
        # if hedayat_fields_res:
        #     hedayat_row = hedayat_fields_res[0]
        #     hedayat_fields_info = {
        #         "suggested": _safe_json_load(hedayat_row.get("suggested")),
        #         "other": _safe_json_load(hedayat_row.get("other")),
        #         "created_time": hedayat_row.get("created_time"),
        #         "edited_time": hedayat_row.get("edited_time"),
        #     }

        # Notifications for the user or for the student role
        notifications_query = """
            SELECT TOP 10 title, description, added_by, priority, persian_date, fullText, created_time
            FROM notifications
            WHERE (user_id = ? OR roles LIKE ?)
            ORDER BY created_time DESC
        """
        notif_params = (user_id, f"%{info.get('role', 'stu')}%")
        notifications_res = db_helper.search_fetchall(conn=conn, cursor=cursor, query=notifications_query,
                                                      field=notif_params)

        dashboard_info = {
            "quiz": quiz_progress,
            "scores": scores_info,
            "result_state": result_state_info,
            # "hedayat_fields": hedayat_fields_info,
            "notifications": notifications_res,
        }
        token = str(uuid.uuid4())
        return token, dashboard_info
    except Exception as e:
        conn.rollback()
        service_exception_error_logging(conn, cursor, "ags_api/stu", "select_stu_dashboard", str(e), request_data, info)
        return None, {}


def update_stu_user_profile(conn, cursor, request_data, info):
    # TODO log for update the profile with the some attribute
    try:
        db_helper.update_record(conn, cursor, 'stu', ['first_name', 'last_name', 'edited_time'],
                                [request_data["first_name"], request_data["last_name"],
                                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                'user_id = ?', [str(info["user_id"])])
        token = str(uuid.uuid4())
        return token, {"first_name": request_data["first_name"], "last_name": request_data["last_name"]},
    except Exception as e:
        conn.rollback()
        service_exception_error_logging(conn, cursor, "ags_api/stu", "update_stu_user_profile", str(e), request_data,
                                        info)
        return None, {}


def update_stu_password(conn, cursor, request_data, info):
    try:
        encrypted_password = func_helper.encrypt_password(request_data["password"])
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db_helper.update_record(
            conn,
            cursor,
            "users",
            ["password", "edited_time"],
            [encrypted_password, now_str],
            "user_id = ?",
            [str(info["user_id"])],
        )
        token = str(uuid.uuid4())
        return token
    except Exception as e:
        conn.rollback()
        service_exception_error_logging(conn, cursor, "ags_api/stu", "update_stu_password", str(e), request_data, info)
        return None


def select_stu_quiz_table_info(conn, cursor, request_data, info):
    try:
        # Product kind (e.g. AG, SCL) for this quiz pack
        kind = (request_data.get("kind") or "").upper()
        # If kind is not provided, we cannot determine which quiz pack to use
        if not kind:
            token = str(uuid.uuid4())
            return token, []
        stu_access = _load_student_access(conn, cursor, info["user_id"])
        permission, _ = _package_permission(stu_access, kind)
        has_access = permission == 1

        if not has_access:
            return None, []

        quiz_info = get_quiz_table_info(kind=kind) or []

        if not quiz_info:
            token = str(uuid.uuid4())
            return token, []

        # Use quiz_kind column (per-pack quizzes start from id 1)
        # Support legacy rows where quiz_kind might be NULL.
        query = (
            "SELECT * FROM quiz_answer "
            "WHERE user_id = ? AND (quiz_kind = ?) "
            "ORDER BY quiz_id ASC"
        )
        all_answers = db_helper.search_allin_table(
            conn=conn,
            cursor=cursor,
            query=query,
            field=(info["user_id"], kind),
        )
        student_quiz_info = []

        def _build_quiz_item(q, status=0, can_start=0):
            item = dict(q)  # avoid mutating global quiz table config
            item["status"] = status  # 0: not started, 1: in-progress, 2: finished
            item["can_start"] = can_start
            return item

        if not all_answers:
            for index, q in enumerate(quiz_info):
                can_start = 1 if index == 0 else 0
                student_quiz_info.append(_build_quiz_item(q, status=0, can_start=can_start))
        else:
            # quiz_answer schema (see helper/db_schemas.py):
            # [0]=quiz_answer_id, [1]=user_id, [2]=quiz_id, [3]=quiz_kind,
            # [4]=answers(JSON), [5]=state, [6]=ins_id, [7]=con_id, ...
            last_answer_row = all_answers[-1]
            last_quiz_id = last_answer_row[2]
            last_quiz_state = last_answer_row[5]

            for q in quiz_info:
                q_id = q["id"]

                if q_id < last_quiz_id:
                    student_quiz_info.append(_build_quiz_item(q, status=2, can_start=0))
                elif q_id == last_quiz_id:
                    if last_quiz_state == 2:
                        student_quiz_info.append(_build_quiz_item(q, status=2, can_start=0))
                    else:
                        student_quiz_info.append(_build_quiz_item(q, status=last_quiz_state, can_start=1))
                elif q_id == last_quiz_id + 1:
                    can_start = 1 if last_quiz_state == 2 else 0
                    student_quiz_info.append(_build_quiz_item(q, status=0, can_start=can_start))
                else:
                    student_quiz_info.append(_build_quiz_item(q, status=0, can_start=0))
        token = str(uuid.uuid4())
        return token, student_quiz_info
    except Exception as e:
        conn.rollback()
        service_exception_error_logging(conn, cursor, "ags_api/stu", "select_stu_quiz_table_info", str(e), request_data,
                                        info)
        return None, []


def select_stu_quiz_info(conn, cursor, request_data, info):
    try:
        token = str(uuid.uuid4())
        quiz_id = request_data["quiz_id"]

        # Determine product kind directly from request (per-pack quiz ids start from 1)
        quiz_kind = request_data.get("quiz_kind").upper()
        if not quiz_kind:
            return None, [], {}

        query_stu = 'SELECT ins_id FROM stu WHERE user_id = ?'
        res_stu = db_helper.search_table(conn=conn, cursor=cursor, query=query_stu, field=info["user_id"])
        stu_access = _load_student_access(conn, cursor, info["user_id"])
        permission, _ = _package_permission(stu_access, quiz_kind)
        has_access = permission == 1

        if not has_access:
            return None, [], {}
        # Limit answers to this user and this quiz kind (support legacy NULL quiz_kind)
        query = (
            "SELECT * FROM quiz_answer "
            "WHERE user_id = ? AND (quiz_kind = ?) "
            "ORDER BY quiz_id ASC"
        )
        all_answers = db_helper.search_allin_table(
            conn=conn,
            cursor=cursor,
            query=query,
            field=(info["user_id"], quiz_kind),
        )

        query_quiz = 'SELECT * FROM setting WHERE user_id = ' + str(res_stu.ins_id) + ' and quiz_id = ' + str(
            quiz_id) + ''
        response_quiz_setting = cursor.execute(query_quiz)
        res_quiz_setting = response_quiz_setting.fetchone()
        # All answers already limited to this product kind (AG, SCL, ...)
        quiz_ids_for_kind = {q["id"] for q in get_quiz_table_info(kind=quiz_kind)}

        # Helper to load quiz metadata from the appropriate data file
        def _load_quiz_info():
            return get_quiz_info(quiz_id=quiz_id, kind=quiz_kind)

        # Helper to apply optional custom description/voice from setting table
        def _apply_setting_overrides(quiz_info_obj, res_quiz_setting):
            if res_quiz_setting is not None:
                # NOTE: column indexes 2 and 3 are used here based on existing implementation
                if len(res_quiz_setting) > 2 and res_quiz_setting[2] is not None:
                    quiz_info_obj["description"] = res_quiz_setting[2]
                if len(res_quiz_setting) > 3 and res_quiz_setting[3] is not None:
                    quiz_info_obj["voice"] = res_quiz_setting[3]
            return quiz_info_obj

        # If no answer for this product yet, only the first quiz of this product is allowed
        if not all_answers:
            first_quiz_id = min(quiz_ids_for_kind) if quiz_ids_for_kind else None
            if quiz_id != first_quiz_id:
                return None, [], {}

            quiz_info_obj = _apply_setting_overrides(_load_quiz_info(), res_quiz_setting)
            return token, quiz_info_obj, {}

        # There is at least one answered quiz for this product
        last_answer_row = all_answers[-1]
        # quiz_answer schema (see helper/db_schemas.py):
        # [0]=quiz_answer_id, [1]=user_id, [2]=quiz_id, [3]=quiz_kind,
        # [4]=answers(JSON), [5]=state, [6]=ins_id, [7]=con_id, ...
        last_quiz_id = last_answer_row[2]
        last_quiz_state = last_answer_row[5]

        # If requesting the same quiz as the last one
        if last_quiz_id == quiz_id:
            if last_quiz_state == 2:
                # Finished quiz cannot be reopened
                return None, [], {}
            elif last_quiz_state == 1:
                # In-progress quiz can be continued with existing answers
                quiz_info_obj = _apply_setting_overrides(_load_quiz_info(), res_quiz_setting)
                answers_json = last_answer_row[4] if len(last_answer_row) > 4 else None
                quiz_answer = json.loads(answers_json) if answers_json else {}
                return token, quiz_info_obj, quiz_answer

        # If requesting the next quiz in sequence
        if last_quiz_id + 1 == quiz_id:
            if last_quiz_state == 2:
                # Previous quiz finished -> allow starting new quiz with empty answers
                quiz_info_obj = _apply_setting_overrides(_load_quiz_info(), res_quiz_setting)
                return token, quiz_info_obj, {}
            else:
                # Previous quiz not finished -> cannot start next quiz
                return None, [], {}

        # Any other quiz_id (skipping ahead or going back) is not allowed
        return None, [], {}
    except Exception as e:
        conn.rollback()
        service_exception_error_logging(conn, cursor, "ags_api/stu", "select_stu_quiz_info", str(e), request_data, info)
        return None, [], {}


# Pre-compute the last AG question id once (used for Redis enqueue condition)
AG_LAST_QUESTION_ID = max(
    q.get("question_id", 0)
    for quiz in ag_quiz_info
    for section in quiz.get("sections", [])
    for q in section.get("questions", [])
)

SCL_LAST_QUESTION_ID = max(
    q.get("question_id", 0)
    for quiz in scl_quiz_info
    for section in quiz.get("sections", [])
    for q in section.get("questions", [])
)


def _enqueue_result_generation(conn, cursor, user_id, phone, kind: str):
    """
    Push user to Redis queue and log in redis_log table.

    kind: Product kind (e.g., AG, SCL). Used by scheduler to choose correct flow.
    """
    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD if REDIS_PASSWORD else None,
        db=REDIS_DB,
        decode_responses=True,
    )

    # Push JSON payload so scheduler can distinguish product kind (AG, SCL, ...)
    payload = json.dumps(
        {
            "user_id": str(user_id),
            "kind": (kind or "").upper(),
        },
        ensure_ascii=False,
    )
    r.rpush(REDIS_QUEUE_NAME, payload)

    # Log enqueue operation in redis_log with kind
    field = '([user_id], [kind], [result], [phone])'
    values = (user_id, (kind or "").upper(), "user add to queue to create", phone)
    db_helper.insert_value(conn=conn, cursor=cursor, table_name="redis_log", fields=field, values=values)


def submit_quiz_answer(conn, cursor, request_data, info):
    try:
        token = str(uuid.uuid4())
        # example request_data ==> {"quiz_id": 1, "quiz_kind": "AG", "user_id": 5,
        # "question_Answer": [5, null], "question_Number": 1, "last_question_id": 61,
        # "state": "", "token": "2f674cf6-06bd-4432-bbf3-1cda566537e6"}
        # here in request_data have quiz_kind we should use that to update or insert data
        # first should check out the quiz_kind that if user dosent start any of the quiz of that kind
        # should start form the first (and quiz_id and question_Number is ok for that quiz)
        # sometimes the question_Answer in request data have null we should remove that
        # if question_Number and last_question_id is same should make the state 2 (if line 430)
        # some of the quiz have the time and the state changed something except "" and in that time
        # should finish it (state 2) (if line 405)

        quiz_id = request_data["quiz_id"]
        quiz_kind = (request_data.get("quiz_kind")).upper()
        question_number = request_data["question_Number"]
        last_question_id = request_data.get("last_question_id")
        if not quiz_kind:
            return None, "quiz_kind is required"

        # Normalize / clean answers: drop any nulls from list answers
        question_answer = request_data.get("question_Answer")
        if isinstance(question_answer, list):
            question_answer = [a for a in question_answer if a is not None]

        # If quiz has timed-out on client side, just mark state=2 and exit
        if request_data.get("state") and request_data.get("state") != "":
            db_helper.update_record(
                conn,
                cursor,
                "quiz_answer",
                ["state", "edited_time"],
                [2, datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                "quiz_id = ? AND user_id = ? AND (quiz_kind = ? OR quiz_kind IS NULL)",
                [str(quiz_id), str(info["user_id"]), quiz_kind],
            )
            token = str(uuid.uuid4())
            return token, "آزمون شما به علت اتمام زمان به پایان رسید."

        # Load existing answer row (limited to this user, quiz and kind)
        query_quiz_answer = """
            SELECT quiz_answer_id, user_id, quiz_id, quiz_kind, answers, state, ins_id, con_id
            FROM quiz_answer
            WHERE user_id = ? AND quiz_id = ? AND (quiz_kind = ?)
        """
        rows = db_helper.search_fetchall(
            conn=conn,
            cursor=cursor,
            query=query_quiz_answer,
            field=(info["user_id"], quiz_id, quiz_kind),
        )
        row = rows[0] if rows else None

        message = ""

        if row is None:
            # Validate that first question for this quiz is being answered
            quiz_info_obj = get_quiz_info(quiz_id=quiz_id, kind=quiz_kind)
            if not quiz_info_obj:
                return None, "quiz info not found"

            first_q_id = None
            for section in quiz_info_obj.get("sections", []):
                for q in section.get("questions", []):
                    qid = q.get("question_id")
                    if first_q_id is None or (qid is not None and qid < first_q_id):
                        first_q_id = qid

            if first_q_id is not None and question_number != first_q_id:
                return None, "this question number is not valid reload quiz"

            answers = {question_number: question_answer}
            answers_data = json.dumps(answers, ensure_ascii=False)
            ins_id, con_id = get_stu_other_info(conn=conn, cursor=cursor, user_id=info["user_id"])
            field = '([user_id], [quiz_id], [quiz_kind], [answers], [state], [ins_id], [con_id])'
            values = (
                info["user_id"],
                quiz_id,
                quiz_kind,
                answers_data,
                1,
                ins_id,
                con_id,
            )
            db_helper.insert_value(conn=conn, cursor=cursor, table_name="quiz_answer", fields=field, values=values)
        else:
            # Update existing answers JSON
            existing_answers_json = row.get("answers")
            answers = json.loads(existing_answers_json) if existing_answers_json else {}
            answers[question_number] = question_answer
            answers_data = json.dumps(answers, ensure_ascii=False)

            if last_question_id is not None and question_number == last_question_id:
                # Last question of this quiz -> mark quiz as finished (state=2)
                db_helper.update_record(
                    conn,
                    cursor,
                    "quiz_answer",
                    ["answers", "state", "edited_time"],
                    [answers_data, 2, datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    "quiz_id = ? AND user_id = ? AND (quiz_kind = ? OR quiz_kind IS NULL)",
                    [str(quiz_id), str(info["user_id"]), quiz_kind],
                )
            else:
                # In-progress quiz (state stays as-is or 1)
                db_helper.update_record(
                    conn,
                    cursor,
                    "quiz_answer",
                    ["answers", "edited_time"],
                    [answers_data, datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    "quiz_id = ? AND user_id = ? AND (quiz_kind = ? OR quiz_kind IS NULL)",
                    [str(quiz_id), str(info["user_id"]), quiz_kind],
                )

        # After the whole product is finished, add user to Redis queue.
        # For AG product, this happens when the very last question (global id) is answered.
        if quiz_kind == "AG" and question_number == AG_LAST_QUESTION_ID:
            _enqueue_result_generation(
                conn=conn,
                cursor=cursor,
                user_id=info["user_id"],
                phone=info.get("phone"),
                kind="AG",
            )
            message = "کارنامه شما در حال تولید است ، لطفا کمی صبور باشید."

        if quiz_kind == "SCL" and question_number == SCL_LAST_QUESTION_ID:
            _enqueue_result_generation(
                conn=conn,
                cursor=cursor,
                user_id=info["user_id"],
                phone=info.get("phone"),
                kind="SCL",
            )
            message = "کارنامه شما در حال تولید است ، لطفا کمی صبور باشید."

        return token, message
    except Exception as e:
        conn.rollback()
        service_exception_error_logging(conn, cursor, "ags_api/stu", "submit_quiz_answer", str(e), request_data, info)
        return None, ""


def get_stu_other_info(conn, cursor, user_id):
    query = 'SELECT con_id, ins_id FROM stu WHERE user_id = ?'
    res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=user_id)
    if res.ins_id is None:
        return res.con_id, res.con_id
    return res.ins_id, res.con_id


def select_student_access_info(conn, cursor, request_data, info):
    try:
        query = 'SELECT access, comment FROM stu WHERE user_id = ?'
        res_stu_access = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=info["user_id"])
        stu_access = _load_student_access(conn, cursor, info["user_id"])
        token = str(uuid.uuid4())
        comment = getattr(res_stu_access, "comment", None) if res_stu_access else None
        return token, {"access": stu_access or _empty_access(), "comment": comment}
    except Exception as e:
        conn.rollback()
        service_exception_error_logging(conn, cursor, "ags_api/stu", "select_student_access_info", str(e), request_data,
                                        info)
        return None, {}
