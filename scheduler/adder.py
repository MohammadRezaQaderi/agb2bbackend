"""Queue one student's report for the report scheduler.

Examples:
    python scheduler/adder.py --user-id 123 --kind AG
    python scheduler/adder.py --phone 09123456789 --kind SCL
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import redis

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import (  # noqa: E402
    REDIS_DB,
    REDIS_HOST,
    REDIS_PASSWORD,
    REDIS_PORT,
    REDIS_QUEUE_NAME,
)
from helper.db.sqlalchemy import session_scope  # noqa: E402
from helper.db.sqlalchemy.queries.auth import get_user_identity_by_phone  # noqa: E402
from helper.db.sqlalchemy.queries.scheduler_reports import (  # noqa: E402
    get_scheduler_student_context,
    list_completed_attempt_versions,
)
from helper.db.sqlalchemy.queries.students import create_redis_log  # noqa: E402
from helper.quiz.runtime_provider import resolve_attempt_runtime  # noqa: E402

DIGIT_TRANSLATION = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _positive_user_id(value: str) -> int:
    user_id = int(value)
    if user_id <= 0:
        raise argparse.ArgumentTypeError("user ID must be positive")
    return user_id


def phone_candidates(value: str) -> tuple[str, ...]:
    """Return common Iranian phone representations in lookup order."""
    phone = str(value or "").strip().translate(DIGIT_TRANSLATION)
    phone = re.sub(r"[\s\-()]", "", phone)
    candidates = [phone]
    if phone.startswith("+98"):
        candidates.append(f"0{phone[3:]}")
    elif phone.startswith("98") and len(phone) == 12:
        candidates.append(f"0{phone[2:]}")
    elif len(phone) == 10 and phone.startswith("9"):
        candidates.append(f"0{phone}")
    return tuple(dict.fromkeys(candidate for candidate in candidates if candidate))


def build_queue_payload(user_id: int, kind: str) -> str:
    return json.dumps(
        {"user_id": str(user_id), "kind": kind.upper()},
        ensure_ascii=False,
    )


def _resolve_student(session, *, user_id: int | None, phone: str | None) -> dict[str, Any]:
    if phone is not None:
        identity = None
        for candidate in phone_candidates(phone):
            identity = get_user_identity_by_phone(session, candidate)
            if identity:
                break
        if not identity:
            raise ValueError(f"No user found for phone {phone!r}")
        user_id = int(identity["user_id"])

    student = get_scheduler_student_context(session, int(user_id))
    if not student:
        raise ValueError(f"User {user_id} does not have a student profile")
    return student


def enqueue_report(
    *,
    user_id: int | None = None,
    phone: str | None = None,
    kind: str = "AG",
    dry_run: bool = False,
    redis_client=None,
) -> dict[str, Any]:
    """Validate and enqueue one report job."""
    kind = str(kind or "").upper()
    if kind not in {"AG", "SCL"}:
        raise ValueError("kind must be AG or SCL")
    if (user_id is None) == (phone is None):
        raise ValueError("provide exactly one of user_id or phone")

    with session_scope() as session:
        student = _resolve_student(session, user_id=user_id, phone=phone)
        resolved_user_id = int(student["user_id"])
        attempts = list_completed_attempt_versions(
            session=session,
            user_id=resolved_user_id,
            report_kind=kind,
        )
        runtime = resolve_attempt_runtime(kind, attempts)

    result = {
        "user_id": resolved_user_id,
        "phone": student["phone"],
        "student_name": f"{student.get('first_name') or ''} {student.get('last_name') or ''}".strip(),
        "kind": kind,
        "scoring_version": runtime.scoring_version,
        "queue": REDIS_QUEUE_NAME,
        "dry_run": dry_run,
    }
    if dry_run:
        return result

    client = redis_client or redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD if REDIS_PASSWORD else None,
        db=REDIS_DB,
        decode_responses=True,
    )
    result["queue_length"] = int(client.rpush(REDIS_QUEUE_NAME, build_queue_payload(resolved_user_id, kind)))

    with session_scope() as session:
        create_redis_log(
            session=session,
            user_id=resolved_user_id,
            kind=kind,
            result="user manually added to queue to create report",
            phone=student["phone"],
        )
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--user-id", type=_positive_user_id, help="Student users.user_id")
    target.add_argument("--phone", help="Student phone number")
    parser.add_argument("--kind", choices=("AG", "SCL"), default="AG", type=str.upper)
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing to Redis or redis_logs")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = enqueue_report(
            user_id=args.user_id,
            phone=args.phone,
            kind=args.kind,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        print(f"Could not queue report: {exc}", file=sys.stderr)
        return 1

    action = "Validated" if args.dry_run else "Queued"
    print(
        f"{action} {result['kind']} report for user {result['user_id']} "
        f"({result['phone']}, {result['student_name'] or 'unnamed student'}) "
        f"using scoring {result['scoring_version']}."
    )
    if not args.dry_run:
        print(f"Redis queue: {result['queue']} (length: {result['queue_length']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
