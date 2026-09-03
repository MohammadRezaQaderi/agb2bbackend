import string
import random
import json
import logging
from random import randint
from typing import Any, Mapping, Tuple, Optional

from helper.constants import (
    AG_QUIZ_NAME_TITLE,
    PACKAGES_DATA,
    PROVINCES,
    SCL_QUIZ_NAME_TITLE,
    get_kind_name,
)
from helper.auth_context import authorizer
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.auth import (
    update_user_password,
    user_phone_exists,
)
from helper.db.sqlalchemy.queries.other import payment_id_exists
from helper.db.sqlalchemy.queries.students import (
    consume_capacity_package,
    count_student_packages_for_relation,
    get_capacity_package,
    get_student_access_for_relation,
    save_student_package_access,
    update_student_access,
)
from helper.health import health_payload, liveness_payload, readiness_payload
from helper.password_helper import (
    decrypt_password,
    encrypt_password,
    hash_password,
    is_password_hash,
    verify_password,
    verify_password_hash,
)
from helper.service_errors import (
    exception_error_logging,
    exception_error_message_return,
    key_error_logging,
    key_error_message_return,
    not_auth_return,
    not_data_return,
    not_method_access_return,
    service_exception_error_logging,
)
from helper.tracking import get_tracking_code
from helper.validators import check_security_code, is_valid_mobile, password_format_check
from helper import file_helper


logger = logging.getLogger(__name__)


def save_base64_image(pic_value: str | None, last_pic: str | None, storage_dir: str) -> str | None:
    if not pic_value:
        return None

    if not pic_value.startswith("data:image"):
        return pic_value

    image_bytes, extension = file_helper.decode_base64_image(pic_value)
    new_file_name = f"{get_tracking_code()}{extension}"
    file_helper.write_storage_file(storage_dir, new_file_name, image_bytes)
    file_helper.remove_storage_file(storage_dir, last_pic)

    return new_file_name


def upsert_student_package_access(
        stu_user_id: int,
        owner_user_id: int | None,
        consultant_user_id: int | None,
        package_name: str,
        permission: int,
        limit: int,
) -> None:
    try:
        with session_scope() as session:
            save_student_package_access(
                session=session,
                stu_user_id=stu_user_id,
                owner_user_id=owner_user_id,
                consultant_user_id=consultant_user_id,
                package_name=package_name,
                permission=permission,
                limit=limit,
            )
    except Exception:
        # The new table is additive. Keep the old JSON path working if a deployment
        # temporarily runs before the schema migration.
        logger.exception("student_package_access sync skipped")


def get_student_package_access_counts(
        user_id: int,
        relation_column: str,
) -> dict[str, int] | None:
    if relation_column not in {"owner_user_id", "consultant_user_id"}:
        return None

    try:
        with session_scope() as session:
            return count_student_packages_for_relation(
                session=session,
                relation_column=relation_column,
                user_id=user_id,
            )
    except Exception:
        logger.exception("student_package_access count fallback")
        return None


def random_phone_candidate(n: int) -> str:
    """Generate a random phone candidate with prefix '009' and n-digit suffix."""
    range_start = 10 ** (n - 1)
    range_end = (10 ** n) - 1
    return '009' + str(randint(range_start, range_end))


def random_generate_phone(n: int) -> str:
    """Generate a unique random phone number with prefix '009' and n-digit suffix."""
    while True:
        phone = random_phone_candidate(n)
        with session_scope() as session:
            exists = user_phone_exists(session=session, phone=phone)
        if not exists:
            return phone


def random_generate_password(size: int = 6, chars: str = string.digits) -> str:
    """Generate a random password of specified size using the given character set."""
    return ''.join(random.choice(chars) for _ in range(size))


def random_generate_otp_code(n: int) -> int:
    """Generate a random n-digit OTP code."""
    range_start = 10 ** (n - 1)
    range_end = (10 ** n) - 1
    return randint(range_start, range_end)


def get_payment_id() -> int:
    """Generate a unique payment ID that doesn't exist in the database."""
    while True:
        payment_id = randint(1, 999999)
        with session_scope() as session:
            exists = payment_id_exists(session=session, payment_id=payment_id)
        if not exists:
            return payment_id


def get_price_payment(request_data: Mapping[str, int], discount_percentage: float | None) -> Tuple[int, int, int, int]:
    """
    Calculate total price for AG / SCL packages.

    Args:
        request_data: Dictionary containing package counts, e.g. {"AG": 20, "SCL": 10}
        discount_percentage: Optional discount percentage (0.0 to 100.0).

    Returns:
        Tuple of (total_price, discounted_price, ag_count, scl_count) in Rials.
    """
    total = 0

    ag_count = int(request_data.get("AG", 0) or 0)
    if ag_count in PACKAGES_DATA.get("AG", {}):
        total += PACKAGES_DATA["AG"][ag_count]

    scl_count = int(request_data.get("SCL", 0) or 0)
    if scl_count in PACKAGES_DATA.get("SCL", {}):
        total += PACKAGES_DATA["SCL"][scl_count]

    # Convert to final currency unit (kept from original implementation)
    total = total * 10

    # Apply percentage discount if provided (stored as 0–100 in DB)
    if discount_percentage:
        new_value = round(total * (100 - float(discount_percentage)) / 100)
    else:
        new_value = total

    return total, new_value, ag_count, scl_count


def update_user_and_role_password(
        request_data: Mapping[str, Any],
        user_info: Mapping[str, Any],
        role_table: str,
) -> Optional[str]:
    """
    Update password in the canonical `users` table.

    This helper encapsulates the common pattern used by:
    - update_ins_password
    - update_sch_password
    - update_ocon_password
    - update_con_password

    Args:
        request_data: Request payload containing at least the new 'password'.
        user_info: Context information containing 'user_id'.
        role_table: Kept for backward-compatible caller signatures.

    Returns:
        New tracking token (str) on success, or None on failure.
    """
    try:
        encrypted_password = encrypt_password(request_data["password"])
        with session_scope() as session:
            update_user_password(
                session=session,
                user_id=user_info["user_id"],
                encrypted_password=encrypted_password,
            )

        token = get_tracking_code()
        return token
    except Exception as e:
        service_exception_error_logging("ag_api/password", f"update_{role_table}_password",
            str(e), request_data, user_info
        )
        return None


def validate_request_data_fields(
        request_data: Mapping[str, Any],
        required_fields: list[str],
        method_type: str,
):
    """
    Validate that all required fields exist (and are not empty) in request_data.

    Returns:
        (True, None) if all fields are present,
        (False, error_response_dict) if any field is missing.
    """
    for field in required_fields:
        if field not in request_data or request_data[field] in (None, ''):
            return False, key_error_message_return(field, method_type)
    return True, None


def update_student_access_and_capacity(
        request_data: Mapping[str, Any],
        user_info: Mapping[str, Any],
        role_type: str,
        id_field: str,
        end_point: str,
) -> Tuple[Optional[str], Optional[dict], str]:
    """
    Update student access permissions and manage capacity tracking.

    This is a reusable function for institute, school, and owner_consultant roles.

    Args:
        request_data: Request data containing:
            - stu_id: Student ID (user_id from stu table)
            - kind: Package name (key from PACKAGES_DATA, e.g., "AG", "SCL")
            - permission: Permission flag (1 or 0) indicating grant/revoke access
            - limit: Limit flag (1 or 0) for the package
        user_info: Context user_info containing user_id
        role_type: Role type ("ins", "sch", or "ocon") for error logging
        id_field: Field name to check ownership ("owner_user_id" or "consultant_user_id")
        end_point: API endpoint for error logging

    Returns:
        Tuple of (tracking_token, response_data, response_message) on success/failure.

    Note:
        Access is stored in format: {"AG": {"permission": 1, "limit": 1}}
        If kind exists in student access, only limit is updated.
        If kind doesn't exist, it's added with both permission and limit.
    """
    try:
        user_id = user_info["user_id"]
        stu_id = request_data.get("stu_id")

        if not stu_id:
            return None, None, "شناسه دانش‌آموز ارسال نشده است."

        with session_scope() as session:
            res_stu = get_student_access_for_relation(session=session, stu_user_id=int(stu_id))

        if res_stu is None:
            return None, None, "دانش‌آموز یافت نشد."

        org_id = res_stu.get(id_field)
        if org_id != user_id:
            return None, None, "این دانش‌آموز به شما تعلق ندارد."

        current_access_str = res_stu.get("access") or '{}'
        try:
            current_access = json.loads(current_access_str) if current_access_str else {}
        except (json.JSONDecodeError, TypeError):
            current_access = {}

        kind = str(request_data.get("kind") or "").upper()
        if not kind:
            return None, None, "نوع بسته (kind) ارسال نشده است."

        if kind not in PACKAGES_DATA:
            valid_packages = "، ".join(f"{package} ({get_kind_name(package)})" for package in PACKAGES_DATA.keys())
            return None, None, f"نوع بسته {kind} معتبر نیست. بسته‌های معتبر: {valid_packages}"

        permission = request_data.get("permission", 0)
        limit = request_data.get("limit", 0)

        if isinstance(permission, bool):
            permission = 1 if permission else 0
        else:
            permission = int(permission) if permission else 0

        if isinstance(limit, bool):
            limit = 1 if limit else 0
        else:
            limit = int(limit) if limit else 0

        package_exists = kind in current_access

        was_granted = False
        if package_exists:
            prev_data = current_access.get(kind, {})
            if isinstance(prev_data, dict):
                was_granted = bool(prev_data.get("permission", 0))
            else:
                was_granted = bool(prev_data)

        if package_exists:
            current_package_data = current_access[kind]
            if isinstance(current_package_data, dict):
                current_package_data["limit"] = limit
                current_package_data["permission"] = permission
            else:
                current_access[kind] = {
                    "permission": permission,
                    "limit": limit
                }
        else:
            current_access[kind] = {
                "permission": permission,
                "limit": limit
            }

        updated_access_json = json.dumps(current_access, ensure_ascii=False)
        with session_scope() as session:
            is_granting = bool(permission)
            if is_granting != was_granted:
                res_capacity = get_capacity_package(session=session, user_id=user_id, package_name=kind)
                if not res_capacity:
                    return None, None, f"بسته {get_kind_name(kind=kind)} برای شما تعریف نشده است."

                allowed = int(res_capacity.get("allowed") or 0)
                if is_granting:
                    if allowed <= 0:
                        return None, None, f"ظرفیت بسته {get_kind_name(kind=kind)} تکمیل شده است."

                    consume_result = consume_capacity_package(session=session, user_id=user_id, package_name=kind)
                    if consume_result == -1:
                        return None, None, f"ظرفیت بسته {get_kind_name(kind=kind)} تکمیل شده است."
                    if consume_result == 0:
                        return None, None, f"بسته {get_kind_name(kind=kind)} برای شما تعریف نشده است."

            update_student_access(session=session, stu_user_id=int(stu_id), access_json=updated_access_json)
            save_student_package_access(
                session=session,
                stu_user_id=int(stu_id),
                owner_user_id=res_stu.get("owner_user_id"),
                consultant_user_id=res_stu.get("consultant_user_id"),
                package_name=kind,
                permission=permission,
                limit=limit,
            )

        token = get_tracking_code()
        return token, None, "دسترسی دانش‌آموز با موفقیت به‌روزرسانی شد."

    except Exception as e:
        service_exception_error_logging(end_point,
            f"update_student_access_and_capacity_{role_type}",
            str(e), request_data, user_info
        )
        return None, None, "مشکلی در به‌روزرسانی دسترسی دانش‌آموز رخ داده است."


def get_quiz_name(kind, quiz_id) -> str | None:
    if quiz_id == 0:
        return None
    if kind == "AG":
        return AG_QUIZ_NAME_TITLE[quiz_id - 1]
    if kind == "SCL":
        return SCL_QUIZ_NAME_TITLE[quiz_id - 1]
    else:
        return None
