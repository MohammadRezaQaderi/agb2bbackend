"""
Migrate legacy quiz_answer rows into quiz_attempt and quiz_question_answer.

This script is additive and idempotent:
- creates the new quiz tables if they do not exist,
- reads legacy quiz_answer.answers JSON blobs,
- upserts one quiz_attempt per user/kind/quiz,
- upserts one quiz_question_answer per attempt/question.

It intentionally keeps the legacy quiz_answer table in place.

Usage:
    python3 helper/db/migrate_quiz_answers.py --dry-run
    python3 helper/db/migrate_quiz_answers.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pyodbc

from config import DB_CONN_STRING
from helper.db.architecture_migration import ensure_quiz_attempt_tables, table_exists


def normalize_quiz_kind(value: Any) -> str:
    return str(value or "AG").upper()


def encode_answer_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def parse_answers(raw: Any) -> dict[int, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(parsed, dict):
        return {}

    answers: dict[int, Any] = {}
    for question_id, answer_value in parsed.items():
        try:
            answers[int(question_id)] = answer_value
        except (TypeError, ValueError):
            continue
    return answers


def get_or_create_attempt(cursor, row, dry_run: bool) -> int | None:
    if dry_run:
        return None

    quiz_kind = normalize_quiz_kind(row.quiz_kind)
    cursor.execute(
        """
        SELECT id
        FROM quiz_attempt
        WHERE user_id = ? AND quiz_kind = ? AND quiz_id = ?
        """,
        row.user_id,
        quiz_kind,
        row.quiz_id,
    )
    existing = cursor.fetchone()
    if existing:
        if not dry_run:
            cursor.execute(
                """
                UPDATE quiz_attempt
                SET state = ?, ins_id = ?, con_id = ?, edited_time = ?
                WHERE id = ?
                """,
                row.state,
                row.ins_id,
                row.con_id,
                row.edited_time,
                existing.id,
            )
        return existing.id

    cursor.execute(
        """
        INSERT INTO quiz_attempt
            ([user_id], [quiz_kind], [quiz_id], [state], [ins_id], [con_id], [created_time], [edited_time])
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        row.user_id,
        quiz_kind,
        row.quiz_id,
        row.state,
        row.ins_id,
        row.con_id,
        row.created_time,
        row.edited_time,
    )
    return cursor.fetchone()[0]


def upsert_question_answer(cursor, attempt_id: int, row, question_id: int, answer_value: Any, dry_run: bool) -> None:
    if dry_run:
        return

    quiz_kind = normalize_quiz_kind(row.quiz_kind)
    stored_value = encode_answer_value(answer_value)
    cursor.execute(
        """
        SELECT id
        FROM quiz_question_answer
        WHERE attempt_id = ? AND question_id = ?
        """,
        attempt_id,
        question_id,
    )
    existing = cursor.fetchone()
    if existing:
        cursor.execute(
            """
            UPDATE quiz_question_answer
            SET answer_value = ?, edited_time = ?
            WHERE id = ?
            """,
            stored_value,
            row.edited_time,
            existing.id,
        )
        return

    cursor.execute(
        """
        INSERT INTO quiz_question_answer
            ([attempt_id], [user_id], [quiz_kind], [quiz_id], [question_id], [answer_value], [created_time], [edited_time])
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        attempt_id,
        row.user_id,
        quiz_kind,
        row.quiz_id,
        question_id,
        stored_value,
        row.created_time,
        row.edited_time,
    )


def migrate(dry_run: bool) -> None:
    conn = pyodbc.connect(DB_CONN_STRING)
    cursor = conn.cursor()
    try:
        if not table_exists(cursor, "quiz_answer"):
            print("SKIP: legacy quiz_answer table does not exist")
            return

        ensure_quiz_attempt_tables(conn, cursor, dry_run)
        if dry_run:
            print("DRY RUN: table creation checked; no quiz data will be written")

        cursor.execute(
            """
            SELECT user_id, quiz_id, quiz_kind, answers, state, ins_id, con_id, created_time, edited_time
            FROM quiz_answer
            WHERE user_id IS NOT NULL AND quiz_id IS NOT NULL
            ORDER BY user_id, quiz_kind, quiz_id
            """
        )
        rows = cursor.fetchall()

        attempts = 0
        question_answers = 0
        for row in rows:
            answers = parse_answers(row.answers)
            if not answers:
                continue

            attempt_id = get_or_create_attempt(cursor, row, dry_run)
            attempts += 1
            if attempt_id is None:
                question_answers += len(answers)
                continue

            for question_id, answer_value in answers.items():
                upsert_question_answer(cursor, attempt_id, row, question_id, answer_value, dry_run)
                question_answers += 1

        if dry_run:
            conn.rollback()
            print(f"DRY RUN: would migrate attempts={attempts}, question_answers={question_answers}")
        else:
            conn.commit()
            print(f"APPLIED: migrated attempts={attempts}, question_answers={question_answers}")
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate quiz_answer blobs to quiz_attempt/question rows.")
    parser.add_argument("--dry-run", action="store_true", help="Print intended actions without writing quiz data.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    migrate(dry_run=args.dry_run)
