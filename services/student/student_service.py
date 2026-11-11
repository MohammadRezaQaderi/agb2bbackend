import json
import logging
import os

import redis

import helper.file_helper as file_helper
from config import REDIS_DB, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT, REDIS_QUEUE_NAME, REPORTS_DIR
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.report_downloads import get_latest_report_queue_status
from helper.db.sqlalchemy.queries.reports import list_quiz_attempts_for_users
from helper.db.sqlalchemy.queries.students import (
    create_redis_log,
    get_latest_ag_score_summary,
    get_latest_scl_score_summary,
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
from helper.password_helper import encrypt_password
from helper.quiz import answer_store
from helper.quiz.quiz_data_extractor import (
    get_last_question_id,
    get_package_quiz_counts,
    get_quiz_info,
    get_quiz_table_info,
)
from helper.quiz_metadata import get_quiz_name
from helper.psy_catalog import build_psy_catalog
from helper.report_catalog import build_student_report_catalog
from helper.service_errors import service_exception_error_logging
from helper.tracking import get_tracking_code

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


def _safe_json_load(value):
    if not value or not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


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
        token = get_tracking_code()
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


def load_student_dashboard_data(
    user_id,
    *,
    notification_role="stu",
    include_notifications=True,
    include_student_info=False,
):
    user_id = int(user_id)
    stu_access = _load_student_access(user_id)
    active_packages = [
        str(package_name).upper()
        for package_name in stu_access
        if _package_permission(stu_access, package_name)[0] == 1
    ]
    package_names = list(dict.fromkeys(["AG", "SCL", *active_packages]))
    quiz_counts = get_package_quiz_counts(package_names)

    with session_scope() as session:
        attempts = list_quiz_attempts_for_users(
            session=session,
            user_ids=[user_id],
            package_names=active_packages,
        )
        ag_score_row = (
            get_latest_ag_score_summary(session=session, user_id=user_id)
            if _package_permission(stu_access, "AG")[0] == 1
            else None
        )
        scl_score_row = (
            get_latest_scl_score_summary(session=session, user_id=user_id)
            if _package_permission(stu_access, "SCL")[0] == 1
            else None
        )
        result_state_row = (
            get_result_state(session=session, user_id=user_id)
            if _package_permission(stu_access, "AG")[0] == 1
            else None
        )
        notifications = (
            list_student_notifications(
                session=session,
                user_id=user_id,
                role=notification_role,
            )
            if include_notifications
            else []
        )
        student_profile = (
            get_student_profile(session=session, user_id=user_id)
            if include_student_info
            else None
        )

    attempts_by_package = {package_name: [] for package_name in active_packages}
    for attempt in attempts:
        package_name = str(attempt.get("quiz_kind") or "").upper()
        attempts_by_package.setdefault(package_name, []).append(attempt)

    quiz_progress = {}
    access_state = {}
    for package_name in package_names:
        permission, report_permission = _package_permission(stu_access, package_name)
        package_attempts = attempts_by_package.get(package_name, [])
        completed = sum(
            1 for attempt in package_attempts if int(attempt.get("state") or 0) == 2
        )
        total = int(quiz_counts.get(package_name) or 0)
        latest_attempt = max(
            package_attempts,
            key=lambda attempt: int(attempt.get("quiz_id") or 0),
            default=None,
        )

        if permission != 1:
            state = "no-access"
        elif total > 0 and completed >= total:
            state = "completed"
        elif package_attempts:
            state = "in-progress"
        else:
            state = "not-started"

        access_state[package_name] = {
            "permission": permission,
            "report_permission": report_permission,
            "state": state,
            "current_quiz_name": (
                get_quiz_name(package_name, latest_attempt.get("quiz_id"))
                if latest_attempt
                else ""
            ),
            "completed": completed,
            "remaining": max(total - completed, 0),
            "total": total,
        }
        if permission == 1:
            quiz_progress[package_name] = {
                "completed": completed,
                "remaining": max(total - completed, 0),
                "total": total,
            }

    scores_info = {}
    if ag_score_row:
        ag_scores = {
            "brain_categories": _safe_json_load(
                ag_score_row.get("brain_categories")
            ),
            "brain_branches": _safe_json_load(ag_score_row.get("brain_branches")),
        }
        scores_info.update(ag_scores)
        scores_info["AG"] = ag_scores
    if scl_score_row:
        scl_scores = _safe_json_load(scl_score_row.get("scl_date"))
        scores_info["scl_date"] = scl_scores
        scores_info["SCL"] = {"scl_date": scl_scores}

    result_state_info = None
    if result_state_row:
        result_state_info = {
            state_key: {
                **state_info,
                "value": result_state_row.get(state_key),
            }
            for state_key, state_info in AG_REPORT_INFO.items()
        }
        result_state_info["edited_time"] = result_state_row.get("edited_time")

    dashboard_info = {
        "quiz": quiz_progress,
        "access_state": access_state,
        "scores": scores_info or None,
        "result_state": result_state_info,
        "notifications": notifications,
    }

    if student_profile:
        consultant_name = " ".join(
            filter(
                None,
                [
                    student_profile.get("consultant_first_name")
                    or student_profile.get("ocon_first_name"),
                    student_profile.get("consultant_last_name")
                    or student_profile.get("ocon_last_name"),
                ],
            )
        )
        dashboard_info["student_info"] = {
            "stu_id": student_profile.get("stu_id"),
            "student_id": user_id,
            "user_id": user_id,
            "phone": student_profile.get("phone"),
            "first_name": student_profile.get("first_name"),
            "last_name": student_profile.get("last_name"),
            "sex": student_profile.get("sex"),
            "city": student_profile.get("city"),
            "birth_date": student_profile.get("birth_date"),
            "education_level": student_profile.get("education_level"),
            "education_field": student_profile.get("education_field"),
            "con_name": consultant_name,
            "access": stu_access,
        }

    active_psy = next(
        (
            (package_name, status)
            for package_name, status in access_state.items()
            if package_name.startswith("PSY_") and status["permission"] == 1
        ),
        None,
    )
    dashboard_info["psy"] = (
        {"package_name": active_psy[0], **active_psy[1]}
        if active_psy
        else None
    )
    return dashboard_info


def select_stu_dashboard(request_data, info):
    try:
        dashboard_info = load_student_dashboard_data(
            info["user_id"],
            notification_role=info.get("role", "stu"),
            include_notifications=True,
        )
        return get_tracking_code(), dashboard_info, ""
    except Exception as e:
        service_exception_error_logging(
            "ags_api/stu",
            "select_stu_dashboard",
            str(e),
            request_data,
            info,
        )
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
        token = get_tracking_code()
        return token, {"first_name": request_data["first_name"], "last_name": request_data["last_name"]}, "اطلاعات شما با موفقیت تغییر یافت."
    except Exception as e:
        service_exception_error_logging("ags_api/stu", "update_stu_user_profile", str(e), request_data,
                                        info)
        return None, None, "اطلاعات شما با موفقیت تغییر نیافت."


def update_stu_password(request_data, info):
    try:
        encrypted_password = encrypt_password(request_data["password"])
        with session_scope() as session:
            update_user_password(session=session, user_id=info["user_id"], encrypted_password=encrypted_password)
        token = get_tracking_code()
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
            token = get_tracking_code()
            return token, [], ""
        stu_access = _load_student_access(info["user_id"])
        permission, _ = _package_permission(stu_access, kind)
        has_access = permission == 1

        if not has_access:
            return None, None, "شما به این محصول دسترسی ندارید."

        quiz_info = get_quiz_table_info(kind=kind) or []

        if not quiz_info:
            token = get_tracking_code()
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
            if last_quiz_state == 1 and last_attempt.get("answer_count", 0) == 0:
                last_quiz_state = 0

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
        token = get_tracking_code()
        return token, student_quiz_info, ""
    except Exception as e:
        service_exception_error_logging("ags_api/stu", "select_stu_quiz_table_info", str(e), request_data,
                                        info)
        return None, None, "اطلاعات آزمون دریافت نشد."


def select_stu_quiz_info(request_data, info):
    try:
        token = get_tracking_code()
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
            res_quiz_setting = get_quiz_setting(
                session=session,
                owner_user_id=owner_user_id,
                package_name=quiz_kind,
                quiz_id=quiz_id,
            )
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
        token = get_tracking_code()
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

        stu_access = _load_student_access(info["user_id"])
        permission, _ = _package_permission(stu_access, quiz_kind)
        if permission != 1:
            return None, None, "شما به این محصول دسترسی ندارید."

        question_answer = answer_store.normalize_answer_value(request_data.get("question_Answer"))

        # If quiz has timed-out on client side, just mark state=2 and exit
        if request_data.get("state") and request_data.get("state") != "":
            answer_store.finish_attempt(info["user_id"], quiz_kind, quiz_id)
            token = get_tracking_code()
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

        # After the whole product is finished, add the user to the report queue.
        package_last_question_id = get_last_question_id(quiz_kind)
        if package_last_question_id is not None and question_number == package_last_question_id:
            _enqueue_result_generation(
                user_id=info["user_id"],
                phone=info.get("phone"),
                kind=quiz_kind,
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
        token = get_tracking_code()
        comment = res_stu_access.get("comment") if res_stu_access else None
        return token, {"access": stu_access or _empty_access(), "comment": comment}, ""
    except Exception as e:
        service_exception_error_logging("ags_api/stu", "select_student_access_info", str(e), request_data,
                                        info)
        return None, None, "اطلاعات دسترسی دانش‌آموز دریافت نشد."


def select_student_report_catalog(request_data, info):
    try:
        access = _load_student_access(info["user_id"])
        package_names = ["AG", "SCL"] + [
            package_name
            for package_name, package_access in access.items()
            if package_name.startswith("PSY_")
            and _package_permission(access, package_name)[0] == 1
        ]
        quiz_counts = {
            package_name: len(get_quiz_table_info(package_name) or [])
            for package_name in package_names
        }
        attempts_by_package = {
            package_name: answer_store.get_attempts(info["user_id"], package_name)
            for package_name in package_names
        }

        with session_scope() as session:
            queue_statuses = {}
            for package_name in package_names:
                queue_info = get_latest_report_queue_status(
                    session=session,
                    user_id=info["user_id"],
                    kind=package_name,
                )
                queue_statuses[package_name] = (
                    queue_info.get("status") if queue_info else None
                )
            comment_row = get_student_access_comment(
                session=session,
                user_id=info["user_id"],
            )

        phone = file_helper.normalize_storage_filename(info.get("phone") or "")
        report_directory = file_helper.safe_storage_path(REPORTS_DIR, phone)

        def _file_available(_package_name, file_name):
            try:
                return os.path.isfile(
                    file_helper.safe_storage_path(
                        report_directory,
                        file_name,
                    )
                )
            except file_helper.FileValidationError:
                return False

        catalog = build_student_report_catalog(
            access=access,
            quiz_counts=quiz_counts,
            attempts_by_package=attempts_by_package,
            queue_statuses=queue_statuses,
            file_available=_file_available,
        )
        catalog["comment"] = comment_row.get("comment") if comment_row else None
        return get_tracking_code(), catalog, ""
    except Exception as e:
        service_exception_error_logging(
            "ags_api/stu",
            "select_student_report_catalog",
            str(e),
            request_data,
            info,
        )
        return None, None, "اطلاعات کارنامه‌ها دریافت نشد."


def select_student_psy_catalog(request_data, info):
    try:
        access = _load_student_access(info["user_id"])
        package_names = [
            package_name
            for package_name, _package_access in access.items()
            if package_name.startswith("PSY_") and _package_permission(access, package_name)[0] == 1
        ]
        catalog = build_psy_catalog({}, package_names=package_names)

        for package in catalog["packages"]:
            package_name = package["package_name"]
            attempts = answer_store.get_attempts(info["user_id"], package_name)
            completed_quizzes = sum(1 for attempt in attempts if int(attempt.get("state") or 0) == 2)
            in_progress_quizzes = sum(1 for attempt in attempts if int(attempt.get("state") or 0) == 1)
            quiz_count = int(package.get("quiz_count") or 0)
            if quiz_count > 0 and completed_quizzes >= quiz_count:
                state = "completed"
            elif attempts:
                state = "in-progress"
            else:
                state = "not-started"

            package["student_progress"] = {
                "state": state,
                "completed_quizzes": completed_quizzes,
                "in_progress_quizzes": in_progress_quizzes,
                "total_quizzes": quiz_count,
                "percentage": round((completed_quizzes / quiz_count) * 100 if quiz_count else 0),
                "report_permission": _package_permission(access, package_name)[1],
            }

        return get_tracking_code(), catalog, ""
    except Exception as e:
        service_exception_error_logging(
            "ags_api/stu",
            "select_student_psy_catalog",
            str(e),
            request_data,
            info,
        )
        return None, None, "اطلاعات آزمون‌های روان‌شناسی دریافت نشد."
