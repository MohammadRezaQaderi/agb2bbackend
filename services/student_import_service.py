from __future__ import annotations

from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.accounts import create_student_account
from helper.db.sqlalchemy.queries.auth import user_phone_exists
from helper.db.sqlalchemy.queries.consultants import list_consultants_for_owner
from helper.office.student_import_workbook import (
    StudentImportValidationError,
    normalize_phone,
    parse_student_import_workbook,
)
from helper.password_helper import encrypt_password
from helper.random_generators import random_generate_password, random_phone_candidate

ALLOWED_IMPORT_ROLES = {"ins", "sch", "ocon"}


def _consultant_phone_map(session, user_info: dict) -> dict[str, int]:
    if user_info["role"] == "ocon":
        return {normalize_phone(user_info["phone"]): int(user_info["user_id"])}
    consultants = list_consultants_for_owner(session=session, owner_user_id=int(user_info["user_id"]))
    return {normalize_phone(item["phone"]): int(item["user_id"]) for item in consultants if item.get("phone")}


def get_student_import_consultant_phones(user_info: dict) -> list[str]:
    if user_info.get("role") not in ALLOWED_IMPORT_ROLES:
        return []
    with session_scope() as session:
        return list(_consultant_phone_map(session, user_info))


def _generate_available_student_phone(session, attempts: int = 30) -> str:
    for _ in range(attempts):
        phone = random_phone_candidate(8)
        if not user_phone_exists(session=session, phone=phone):
            return phone
    raise RuntimeError("Could not generate a unique student phone.")


def import_students_from_workbook(content: bytes, user_info: dict) -> int:
    if user_info.get("role") not in ALLOWED_IMPORT_ROLES:
        raise PermissionError("Student import is not available for this role.")

    rows = parse_student_import_workbook(content)
    with session_scope() as session:
        consultant_by_phone = _consultant_phone_map(session, user_info)
        consultant_errors = []
        for row in rows:
            if row["consultant_phone"] not in consultant_by_phone:
                consultant_errors.append(
                    {
                        "row": row["row_number"],
                        "field": "شماره تلفن مشاور",
                        "message": "این مشاور متعلق به حساب شما نیست.",
                    }
                )
        if consultant_errors:
            raise StudentImportValidationError(consultant_errors)

        for row in rows:
            request_data = {
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "sex": row["sex"],
                "city": row["city"],
                "birth_date": row["birth_date"],
                "education_level": row["education_level"],
                "education_field": row["education_field"],
                "con_id": consultant_by_phone[row["consultant_phone"]],
                "user_id": user_info["user_id"],
            }
            password = random_generate_password()
            create_student_account(
                session=session,
                phone=_generate_available_student_phone(session),
                encrypted_password=encrypt_password(password),
                request_data=request_data,
                user_info=user_info,
            )

    return len(rows)
