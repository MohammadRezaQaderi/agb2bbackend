import json
import logging
import uuid

import redis

import helper.func_helper as func_helper
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.students import (
    create_redis_log,
    get_latest_ag_score_summary,
    get_quiz_setting,
    get_result_state,
    get_student_access_comment,
    get_student_legacy_access,
    get_student_owner_consultant_ids,
    get_student_owner_user_id,
    get_student_profile,
    list_student_notifications,
    list_student_package_access,
    update_student_name,
    update_user_password,
)
from helper.func_helper import service_exception_error_logging
from helper.quiz import answer_store
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


logger = logging.getLogger(__name__)


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


def _load_student_access(user_id):
    try:
        with session_scope() as session:
            rows = list_student_package_access(session=session, user_id=user_id)
        if rows:
            access = {}
            for row in rows:
                access[str(row.get("package_name", "")).upper()] = {
                    "permission": int(row.get("permission") or 0),
                    "limit": int(row.get("limit") or 0),
                }
            return access
    except Exception:
        logger.exception("student_package_access student fallback")

    with session_scope() as session:
        access = get_student_legacy_access(session=session, user_id=user_id)
    return _load_access_from_json(access)


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


def select_student_info(user_id):
    try:
        with session_scope() as session:
            res = get_student_profile(session=session, user_id=user_id)
        if not res:
            raise ValueError("student not found")
        token = str(uuid.uuid4())
        if res.get("owner_role") in ["ins", "sch"]:
            if res.get("owner_role") == "ins":
                owner_name = res.get("institute_name")
                owner_logo = res.get("institute_logo")
                owner_user_id = res.get("institute_user_id")
            else:
                owner_name = res.get("school_name")
                owner_logo = res.get("school_logo")
                owner_user_id = res.get("school_user_id")

            con_name = ""
            if res.get("consultant_first_name") or res.get("consultant_last_name"):
                con_name = f"{res.get('consultant_first_name') or ''} {res.get('consultant_last_name') or ''}".strip()
            return token, {"phone": res.get("phone"), "user_id": user_id, "id": res.get("stu_id"),
                           "first_name": res.get("first_name"), "last_name": res.get("last_name"),
                           "sex": res.get("sex"), "city": res.get("city"), "access": res.get("access"),
                           "role": "stu", "name": owner_name, "con_name": con_name, "pic": owner_logo,
                           "owner_user_id": owner_user_id, "ins_id": owner_user_id}, ""
        else:
            con_name = ""
            if res.get("ocon_first_name") or res.get("ocon_last_name"):
                con_name = f"{res.get('ocon_first_name') or ''} {res.get('ocon_last_name') or ''}".strip()
            return token, {"phone": res.get("phone"), "user_id": user_id, "id": res.get("stu_id"),
                           "first_name": res.get("first_name"), "last_name": res.get("last_name"),
                           "sex": res.get("sex"), "city": res.get("city"), "access": res.get("access"),
                           "role": "stu", "name": "هدایت تحصیلی", "con_name": con_name,
                           "pic": None, "owner_user_id": res.get("owner_user_id"),
                           "ins_id": res.get("owner_user_id")}, ""
    except Exception as e:
        service_exception_error_logging("ags_api/stu", "select_student_info", str(e), {},
                                        {"user_id": user_id})
        return None, None, "اطلاعات دانش‌آموز یافت نشد."


def select_stu_dashboard(request_data, info):
    try:
        user_id = info["user_id"]

        def _safe_json_load(value):
            try:
                return json.loads(value) if value else value
            except Exception:
                return value

        stu_access = _load_student_access(user_id)

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
            ag_completed_count = answer_store.get_completed_count(user_id, "AG")
            ag_total_quizzes = len(get_quiz_table_info(kind="AG"))
            quiz_progress["AG"] = {
                "completed": ag_completed_count,
                "remaining": max(ag_total_quizzes - ag_completed_count, 0),
                "total": ag_total_quizzes,
            }

        if scl_has_permission:
            scl_completed_count = answer_store.get_completed_count(user_id, "SCL")
            scl_total_quizzes = len(get_quiz_table_info(kind="SCL"))
            quiz_progress["SCL"] = {
                "completed": scl_completed_count,
                "remaining": max(scl_total_quizzes - scl_completed_count, 0),
                "total": scl_total_quizzes,
            }

        # Latest computed scores (if any) - only if AG permission and limit is 1
        scores_info = None
        if ag_has_permission and ag_has_limit:
            with session_scope() as session:
                score_row = get_latest_ag_score_summary(session=session, user_id=user_id)
            if score_row:
                scores_info = {
                    "brain_categories": _safe_json_load(score_row.get("brain_categories")),
                    "brain_branches": _safe_json_load(score_row.get("brain_branches")),
                }

        # Result state (single row per user) - only if AG permission and limit is 1
        result_state_info = None
        if ag_has_permission and ag_has_limit:
            with session_scope() as session:
                db_row = get_result_state(session=session, user_id=user_id)
            if db_row:
                result_state_info = {}
                # Transform using AG_REPORT_INFO and add values from database
                for state_key in AG_REPORT_INFO.keys():
                    result_state_info[state_key] = {
                        **AG_REPORT_INFO[state_key],
                        "value": db_row.get(state_key)
                    }
                # Add edited_time separately
                result_state_info["edited_time"] = db_row.get("edited_time")

        # Notifications for the user or for the student role
        with session_scope() as session:
            notifications_res = list_student_notifications(
                session=session,
                user_id=user_id,
                role=info.get("role", "stu"),
            )

        dashboard_info = {
            "quiz": quiz_progress,
            "scores": scores_info,
            "result_state": result_state_info,
            "notifications": notifications_res,
        }
        token = str(uuid.uuid4())
        return token, dashboard_info, ""
    except Exception as e:
        service_exception_error_logging("ags_api/stu", "select_stu_dashboard", str(e), request_data, info)
        return None, None, "اطلاعات داشبورد دریافت نشد."


def update_stu_user_profile(request_data, info):
    # TODO log for update the profile with the some attribute
    try:
        with session_scope() as session:
            update_student_name(
                session=session,
                user_id=info["user_id"],
                first_name=request_data["first_name"],
                last_name=request_data["last_name"],
            )
        token = str(uuid.uuid4())
        return token, {"first_name": request_data["first_name"], "last_name": request_data["last_name"]}, "اطلاعات شما با موفقیت تغییر یافت."
    except Exception as e:
        service_exception_error_logging("ags_api/stu", "update_stu_user_profile", str(e), request_data,
                                        info)
        return None, None, "اطلاعات شما با موفقیت تغییر نیافت."


def update_stu_password(request_data, info):
    try:
        encrypted_password = func_helper.encrypt_password(request_data["password"])
        with session_scope() as session:
            update_user_password(session=session, user_id=info["user_id"], encrypted_password=encrypted_password)
        token = str(uuid.uuid4())
        return token, None, "رمز عبور شما با موفقیت تغییر کرد."
    except Exception as e:
        service_exception_error_logging("ags_api/stu", "update_stu_password", str(e), request_data, info)
        return None, None, "رمز عبور شما تغییر نیافت."


def select_stu_quiz_table_info(request_data, info):
    try:
        # Product kind (e.g. AG, SCL) for this quiz pack
        kind = (request_data.get("kind") or "").upper()
        # If kind is not provided, we cannot determine which quiz pack to use
        if not kind:
            token = str(uuid.uuid4())
            return token, [], ""
        stu_access = _load_student_access(info["user_id"])
        permission, _ = _package_permission(stu_access, kind)
        has_access = permission == 1

        if not has_access:
            return None, None, "شما به این محصول دسترسی ندارید."

        quiz_info = get_quiz_table_info(kind=kind) or []

        if not quiz_info:
            token = str(uuid.uuid4())
            return token, [], ""

        # Use quiz_kind column (per-pack quizzes start from id 1)
        # Support legacy rows where quiz_kind might be NULL.
        all_attempts = answer_store.get_attempts(info["user_id"], kind)
        student_quiz_info = []

        def _build_quiz_item(q, status=0, can_start=0):
            item = dict(q)  # avoid mutating global quiz table config
            item["status"] = status  # 0: not started, 1: in-progress, 2: finished
            item["can_start"] = can_start
            return item

        if not all_attempts:
            for index, q in enumerate(quiz_info):
                can_start = 1 if index == 0 else 0
                student_quiz_info.append(_build_quiz_item(q, status=0, can_start=can_start))
        else:
            last_attempt = all_attempts[-1]
            last_quiz_id = last_attempt["quiz_id"]
            last_quiz_state = last_attempt["state"]

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
        return token, student_quiz_info, ""
    except Exception as e:
        service_exception_error_logging("ags_api/stu", "select_stu_quiz_table_info", str(e), request_data,
                                        info)
        return None, None, "اطلاعات آزمون دریافت نشد."


def select_stu_quiz_info(request_data, info):
    try:
        token = str(uuid.uuid4())
        quiz_id = request_data["quiz_id"]

        # Determine product kind directly from request (per-pack quiz ids start from 1)
        quiz_kind = request_data.get("quiz_kind").upper()
        if not quiz_kind:
            return None, None, "quiz_kind is required"

        with session_scope() as session:
            owner_user_id = get_student_owner_user_id(session=session, user_id=info["user_id"])
        stu_access = _load_student_access(info["user_id"])
        permission, _ = _package_permission(stu_access, quiz_kind)
        has_access = permission == 1

        if not has_access:
            return None, None, "شما به این محصول دسترسی ندارید."
        # Limit answers to this user and this quiz kind (support legacy NULL quiz_kind)
        all_attempts = answer_store.get_attempts(info["user_id"], quiz_kind)

        with session_scope() as session:
            res_quiz_setting = get_quiz_setting(session=session, owner_user_id=owner_user_id, quiz_id=quiz_id)
        # All attempts already limited to this product kind (AG, SCL, ...)
        quiz_ids_for_kind = {q["id"] for q in get_quiz_table_info(kind=quiz_kind)}

        # Helper to load quiz metadata from the appropriate data file
        def _load_quiz_info():
            return get_quiz_info(quiz_id=quiz_id, kind=quiz_kind)

        # Helper to apply optional custom description/voice from setting table
        def _apply_setting_overrides(quiz_info_obj, res_quiz_setting):
            if res_quiz_setting is not None:
                if res_quiz_setting.get("description") is not None:
                    quiz_info_obj["description"] = res_quiz_setting["description"]
                if res_quiz_setting.get("voice") is not None:
                    quiz_info_obj["voice"] = res_quiz_setting["voice"]
            return quiz_info_obj

        # If no answer for this product yet, only the first quiz of this product is allowed
        if not all_attempts:
            first_quiz_id = min(quiz_ids_for_kind) if quiz_ids_for_kind else None
            if quiz_id != first_quiz_id:
                return None, None, "آزمون مورد نظر شما در دسترس شما نیست."

            quiz_info_obj = _apply_setting_overrides(_load_quiz_info(), res_quiz_setting)
            return token, {"data": quiz_info_obj, "quizAnswers": {}}, ""

        # There is at least one attempt for this product
        last_attempt = all_attempts[-1]
        last_quiz_id = last_attempt["quiz_id"]
        last_quiz_state = last_attempt["state"]

        # If requesting the same quiz as the last one
        if last_quiz_id == quiz_id:
            if last_quiz_state == 2:
                # Finished quiz cannot be reopened
                return None, None, "آزمون مورد نظر شما در دسترس شما نیست."
            elif last_quiz_state == 1:
                # In-progress quiz can be continued with existing answers
                quiz_info_obj = _apply_setting_overrides(_load_quiz_info(), res_quiz_setting)
                quiz_answer = answer_store.get_answers_for_attempt(last_attempt["id"])
                return token, {"data": quiz_info_obj, "quizAnswers": quiz_answer}, ""

        # If requesting the next quiz in sequence
        if last_quiz_id + 1 == quiz_id:
            if last_quiz_state == 2:
                # Previous quiz finished -> allow starting new quiz with empty answers
                quiz_info_obj = _apply_setting_overrides(_load_quiz_info(), res_quiz_setting)
                return token, {"data": quiz_info_obj, "quizAnswers": {}}, ""
            else:
                # Previous quiz not finished -> cannot start next quiz
                return None, None, "آزمون مورد نظر شما در دسترس شما نیست."

        # Any other quiz_id (skipping ahead or going back) is not allowed
        return None, None, "آزمون مورد نظر شما در دسترس شما نیست."
    except Exception as e:
        service_exception_error_logging("ags_api/stu", "select_stu_quiz_info", str(e), request_data, info)
        return None, None, "آزمون مورد نظر شما در دسترس شما نیست."


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


def _enqueue_result_generation(user_id, phone, kind: str):
    """
    Push user to Redis queue and log in redis_logs table.

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

    # Log enqueue operation in redis_logs with kind
    with session_scope() as session:
        create_redis_log(
            session=session,
            user_id=user_id,
            kind=(kind or "").upper(),
            result="user add to queue to create",
            phone=phone,
        )


def submit_quiz_answer(request_data, info):
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

        quiz_id = int(request_data["quiz_id"])
        quiz_kind = answer_store.normalize_quiz_kind(request_data.get("quiz_kind"))
        question_number = int(request_data["question_Number"])
        last_question_id = request_data.get("last_question_id")
        if not quiz_kind:
            return None, None, "quiz_kind is required"

        question_answer = answer_store.normalize_answer_value(request_data.get("question_Answer"))

        # If quiz has timed-out on client side, just mark state=2 and exit
        if request_data.get("state") and request_data.get("state") != "":
            answer_store.finish_attempt(info["user_id"], quiz_kind, quiz_id)
            token = str(uuid.uuid4())
            return token, None, "آزمون شما به علت اتمام زمان به پایان رسید."

        attempt = answer_store.get_attempt(info["user_id"], quiz_kind, quiz_id)

        message = ""

        if attempt is None:
            # Validate that first question for this quiz is being answered
            quiz_info_obj = get_quiz_info(quiz_id=quiz_id, kind=quiz_kind)
            if not quiz_info_obj:
                return None, None, "quiz info not found"

            first_q_id = None
            for section in quiz_info_obj.get("sections", []):
                for q in section.get("questions", []):
                    qid = q.get("question_id")
                    if first_q_id is None or (qid is not None and qid < first_q_id):
                        first_q_id = qid

            if first_q_id is not None and question_number != first_q_id:
                return None, None, "this question number is not valid reload quiz"

            owner_user_id, consultant_user_id = get_stu_other_info(user_id=info["user_id"])
            state = 2 if last_question_id is not None and question_number == last_question_id else 1
            attempt = answer_store.upsert_attempt(
                info["user_id"], quiz_kind, quiz_id, state, owner_user_id, consultant_user_id
            )
        else:
            state = attempt["state"]
            if last_question_id is not None and question_number == last_question_id:
                state = 2
            if state != attempt["state"]:
                attempt = answer_store.upsert_attempt(
                    info["user_id"],
                    quiz_kind,
                    quiz_id,
                    state,
                    attempt.get("owner_user_id"),
                    attempt.get("consultant_user_id"),
                    attempt.get("remain_time"),
                )

        answer_store.upsert_question_answer(attempt, question_number, question_answer)

        # After the whole product is finished, add user to Redis queue.
        # For AG product, this happens when the very last question (global id) is answered.
        if quiz_kind == "AG" and question_number == AG_LAST_QUESTION_ID:
            _enqueue_result_generation(
                user_id=info["user_id"],
                phone=info.get("phone"),
                kind="AG",
            )
            message = "کارنامه شما در حال تولید است ، لطفا کمی صبور باشید."

        if quiz_kind == "SCL" and question_number == SCL_LAST_QUESTION_ID:
            _enqueue_result_generation(
                user_id=info["user_id"],
                phone=info.get("phone"),
                kind="SCL",
            )
            message = "کارنامه شما در حال تولید است ، لطفا کمی صبور باشید."

        return token, None, message
    except Exception as e:
        service_exception_error_logging("ags_api/stu", "submit_quiz_answer", str(e), request_data, info)
        return None, None, ""


def get_stu_other_info(user_id):
    with session_scope() as session:
        result = get_student_owner_consultant_ids(session=session, user_id=user_id)
    if not result:
        return None, None
    return result


def select_student_access_info(request_data, info):
    try:
        with session_scope() as session:
            res_stu_access = get_student_access_comment(session=session, user_id=info["user_id"])
        stu_access = _load_student_access(info["user_id"])
        token = str(uuid.uuid4())
        comment = res_stu_access.get("comment") if res_stu_access else None
        return token, {"access": stu_access or _empty_access(), "comment": comment}, ""
    except Exception as e:
        service_exception_error_logging("ags_api/stu", "select_student_access_info", str(e), request_data,
                                        info)
        return None, None, "اطلاعات دسترسی دانش‌آموز دریافت نشد."
