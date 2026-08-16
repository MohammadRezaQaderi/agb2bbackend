from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import helper.db.db_helper as db_helper


def normalize_quiz_kind(kind: Any) -> str:
    return str(kind or "").upper()


def encode_answer_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def decode_answer_value(value: Any) -> Any:
    if value is None:
        return []
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        if "," in value:
            return [item for item in value.split(",") if item != ""]
        return [value] if value != "" else []


def normalize_answer_value(value: Any) -> Any:
    if isinstance(value, list):
        return [item for item in value if item is not None]
    return value


def get_attempts(conn, cursor, user_id: int, quiz_kind: str):
    query = """
        SELECT id, user_id, quiz_kind, quiz_id, state, remain_time,
               owner_user_id, consultant_user_id,
               owner_user_id AS ins_id, consultant_user_id AS con_id,
               created_time, edited_time
        FROM quiz_attempt
        WHERE user_id = ? AND quiz_kind = ?
        ORDER BY quiz_id ASC
    """
    return db_helper.search_fetchall(conn=conn, cursor=cursor, query=query, field=(user_id, normalize_quiz_kind(quiz_kind)))


def get_attempt(conn, cursor, user_id: int, quiz_kind: str, quiz_id: int):
    query = """
        SELECT id, user_id, quiz_kind, quiz_id, state, remain_time,
               owner_user_id, consultant_user_id,
               owner_user_id AS ins_id, consultant_user_id AS con_id,
               created_time, edited_time
        FROM quiz_attempt
        WHERE user_id = ? AND quiz_kind = ? AND quiz_id = ?
    """
    rows = db_helper.search_fetchall(
        conn=conn,
        cursor=cursor,
        query=query,
        field=(user_id, normalize_quiz_kind(quiz_kind), quiz_id),
    )
    return rows[0] if rows else None


def upsert_attempt(conn, cursor, user_id: int, quiz_kind: str, quiz_id: int, state: int,
                   owner_user_id: int | None, consultant_user_id: int | None, remain_time: int | None = None):
    quiz_kind = normalize_quiz_kind(quiz_kind)
    attempt = get_attempt(conn, cursor, user_id, quiz_kind, quiz_id)
    edited_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if attempt:
        fields = ["state", "edited_time"]
        values = [state, edited_time]
        if remain_time is not None:
            fields.insert(1, "remain_time")
            values.insert(1, remain_time)
        db_helper.update_record(
            conn,
            cursor,
            "quiz_attempt",
            fields,
            values,
            "id = ?",
            [attempt["id"]],
        )
        attempt.update({"state": state, "edited_time": edited_time})
        if remain_time is not None:
            attempt["remain_time"] = remain_time
        return attempt

    fields = '([user_id], [quiz_kind], [quiz_id], [state], [remain_time], [owner_user_id], [consultant_user_id])'
    values = (user_id, quiz_kind, quiz_id, state, remain_time, owner_user_id, consultant_user_id)
    result = db_helper.insert_value(conn, cursor, "quiz_attempt", fields, values, id_column="id")
    attempt_id = result.get("id") if result else None
    return {
        "id": attempt_id,
        "user_id": user_id,
        "quiz_kind": quiz_kind,
        "quiz_id": quiz_id,
        "state": state,
        "remain_time": remain_time,
        "owner_user_id": owner_user_id,
        "consultant_user_id": consultant_user_id,
        "ins_id": owner_user_id,
        "con_id": consultant_user_id,
    }


def finish_attempt(conn, cursor, user_id: int, quiz_kind: str, quiz_id: int):
    return db_helper.update_record(
        conn,
        cursor,
        "quiz_attempt",
        ["state", "edited_time"],
        [2, datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "user_id = ? AND quiz_kind = ? AND quiz_id = ?",
        [user_id, normalize_quiz_kind(quiz_kind), quiz_id],
    )


def upsert_question_answer(conn, cursor, attempt: dict, question_id: int, answer_value: Any):
    stored_value = encode_answer_value(normalize_answer_value(answer_value))
    query = "SELECT id FROM quiz_question_answer WHERE attempt_id = ? AND question_id = ?"
    rows = db_helper.search_fetchall(conn=conn, cursor=cursor, query=query, field=(attempt["id"], question_id))
    edited_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if rows:
        return db_helper.update_record(
            conn,
            cursor,
            "quiz_question_answer",
            ["answer_value", "edited_time"],
            [stored_value, edited_time],
            "attempt_id = ? AND question_id = ?",
            [attempt["id"], question_id],
        )

    fields = '([attempt_id], [user_id], [quiz_kind], [quiz_id], [question_id], [answer_value])'
    values = (
        attempt["id"],
        attempt["user_id"],
        normalize_quiz_kind(attempt["quiz_kind"]),
        attempt["quiz_id"],
        question_id,
        stored_value,
    )
    return db_helper.insert_value(conn, cursor, "quiz_question_answer", fields, values)


def get_answers_for_attempt(conn, cursor, attempt_id: int) -> dict[str, Any]:
    query = """
        SELECT question_id, answer_value
        FROM quiz_question_answer
        WHERE attempt_id = ?
        ORDER BY question_id ASC
    """
    rows = db_helper.search_fetchall(conn=conn, cursor=cursor, query=query, field=attempt_id)
    return {str(row["question_id"]): decode_answer_value(row.get("answer_value")) for row in rows}


def get_answers_for_user_kind(conn, cursor, user_id: int, quiz_kind: str) -> dict[str, Any]:
    query = """
        SELECT question_id, answer_value
        FROM quiz_question_answer
        WHERE user_id = ? AND quiz_kind = ?
        ORDER BY quiz_id ASC, question_id ASC
    """
    rows = db_helper.search_fetchall(conn=conn, cursor=cursor, query=query, field=(user_id, normalize_quiz_kind(quiz_kind)))
    return {str(row["question_id"]): decode_answer_value(row.get("answer_value")) for row in rows}


def get_completed_count(conn, cursor, user_id: int, quiz_kind: str) -> int:
    query = """
        SELECT COUNT(*) AS completed
        FROM quiz_attempt
        WHERE user_id = ? AND quiz_kind = ? AND state = 2
    """
    rows = db_helper.search_fetchall(conn=conn, cursor=cursor, query=query, field=(user_id, normalize_quiz_kind(quiz_kind)))
    return int(rows[0]["completed"] or 0) if rows else 0
