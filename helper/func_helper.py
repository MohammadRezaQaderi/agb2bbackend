import os
import string
import random
import json
import logging
import uuid
import re
from datetime import datetime
from random import randint
from typing import Any, Mapping, Tuple, Optional

from sqlalchemy import text

from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.auth import (
    get_user_identity_by_token,
    update_user_password,
    user_phone_exists,
)
from helper.db.sqlalchemy.queries.other import create_api_log, payment_id_exists
from helper.db.sqlalchemy.queries.students import (
    consume_capacity_package,
    count_student_packages_for_relation,
    get_capacity_package,
    get_student_access_for_relation,
    save_student_package_access,
    update_student_access,
)
from helper.log_sanitizer import sanitize_log_data
from helper.password_helper import (
    decrypt_password,
    encrypt_password,
    hash_password,
    is_password_hash,
    verify_password,
    verify_password_hash,
)
from helper import file_helper
from config import DEVELOP_TOKEN, REDIS_DB, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT


logger = logging.getLogger(__name__)


def get_tracking_code() -> str:
    return str(uuid.uuid4())


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


def authorize_admin(token: str | None) -> bool:
    return bool(token and token == DEVELOP_TOKEN)


async def health_payload(service_name: str):
    return await readiness_payload(service_name)


async def liveness_payload(service_name: str):
    instance_name = os.getenv("INSTANCE_NAME", "unknown")
    port = os.getenv("PORT", "unknown")
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": service_name,
        "instance": instance_name,
        "port": port,
        "version": "1.0.0"
    }


async def readiness_payload(service_name: str):
    instance_name = os.getenv("INSTANCE_NAME", "unknown")
    port = os.getenv("PORT", "unknown")
    try:
        with session_scope() as session:
            session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        logger.exception("Database readiness check failed")
        db_status = "error"

    checks = {"database": db_status}
    include_redis = os.getenv("AG_HEALTH_CHECK_REDIS", "").lower() in {"1", "true", "yes"}
    if include_redis:
        checks["redis"] = _redis_health_status()

    healthy = all(value == "connected" for value in checks.values())
    return {
        "status": "healthy" if healthy else "degraded",
        "timestamp": datetime.now().isoformat(),
        "service": service_name,
        "instance": instance_name,
        "port": port,
        "database": db_status,
        "checks": checks,
        "version": "1.0.0"
    }


def _redis_health_status() -> str:
    from walrus import Database

    redis_db = None
    try:
        redis_db = Database(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD if REDIS_PASSWORD else None,
        )
        redis_db.ping()
        return "connected"
    except Exception:
        logger.exception("Redis readiness check failed")
        return "error"
    finally:
        if redis_db is not None:
            try:
                redis_db.close()
            except Exception:
                logger.exception("Error closing Redis health-check connection")

AG_QUIZ_NAME_TITLE = [
    "کتل", "گاردنر", "نئو", "کلیفتون", "هالند",
    "تعهد‌", "پرسشنامه"
]

SCL_QUIZ_NAME_TITLE = [
    "زندگی شخصی", "زندگی روانشناختی", "زندگی تحصیلی", "زندگی اجتماعی"
]

PACKAGES_DATA = {
    "AG": {
        10: 1600000,
        20: 2900000,
        50: 5800000,
        100: 9600000,
        101: 99999999
    },
    "SCL": {
        10: 1600000,
        20: 2900000,
        50: 5800000,
        100: 9600000,
        101: 99999999
    }
}

PROVINCES = [
    {
        "id": 1,
        "name": "آذربایجان شرقی",
        "slug": "آذربایجان-شرقی"
    },
    {
        "id": 2,
        "name": "آذربایجان غربی",
        "slug": "آذربایجان-غربی"
    },
    {
        "id": 3,
        "name": "اردبیل",
        "slug": "اردبیل"
    },
    {
        "id": 4,
        "name": "اصفهان",
        "slug": "اصفهان"
    },
    {
        "id": 5,
        "name": "البرز",
        "slug": "البرز"
    },
    {
        "id": 6,
        "name": "ایلام",
        "slug": "ایلام"
    },
    {
        "id": 7,
        "name": "بوشهر",
        "slug": "بوشهر"
    },
    {
        "id": 8,
        "name": "تهران",
        "slug": "تهران"
    },
    {
        "id": 9,
        "name": "چهارمحال و بختیاری",
        "slug": "چهارمحال-بختیاری"
    },
    {
        "id": 10,
        "name": "خراسان جنوبی",
        "slug": "خراسان-جنوبی"
    },
    {
        "id": 11,
        "name": "خراسان رضوی",
        "slug": "خراسان-رضوی"
    },
    {
        "id": 12,
        "name": "خراسان شمالی",
        "slug": "خراسان-شمالی"
    },
    {
        "id": 13,
        "name": "خوزستان",
        "slug": "خوزستان"
    },
    {
        "id": 14,
        "name": "زنجان",
        "slug": "زنجان"
    },
    {
        "id": 15,
        "name": "سمنان",
        "slug": "سمنان"
    },
    {
        "id": 16,
        "name": "سیستان و بلوچستان",
        "slug": "سیستان-بلوچستان"
    },
    {
        "id": 17,
        "name": "فارس",
        "slug": "فارس"
    },
    {
        "id": 18,
        "name": "قزوین",
        "slug": "قزوین"
    },
    {
        "id": 19,
        "name": "قم",
        "slug": "قم"
    },
    {
        "id": 20,
        "name": "کردستان",
        "slug": "کردستان"
    },
    {
        "id": 21,
        "name": "کرمان",
        "slug": "کرمان"
    },
    {
        "id": 22,
        "name": "کرمانشاه",
        "slug": "کرمانشاه"
    },
    {
        "id": 23,
        "name": "کهگیلویه و بویراحمد",
        "slug": "کهگیلویه-بویراحمد"
    },
    {
        "id": 24,
        "name": "گلستان",
        "slug": "گلستان"
    },
    {
        "id": 25,
        "name": "لرستان",
        "slug": "لرستان"
    },
    {
        "id": 26,
        "name": "گیلان",
        "slug": "گیلان"
    },
    {
        "id": 27,
        "name": "مازندران",
        "slug": "مازندران"
    },
    {
        "id": 28,
        "name": "مرکزی",
        "slug": "مرکزی"
    },
    {
        "id": 29,
        "name": "هرمزگان",
        "slug": "هرمزگان"
    },
    {
        "id": 30,
        "name": "همدان",
        "slug": "همدان"
    },
    {
        "id": 31,
        "name": "یزد",
        "slug": "یزد"
    }
]

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


async def authorizer(request_data: Mapping[str, Any]):
    try:
        token = request_data.get("token")
        if not token:
            return False, "اطلاعات دریافتی شما دچار مشکل شده لطفا یکبار خروج کرده و سپس ورود شوید.", None

        with session_scope() as session:
            res = get_user_identity_by_token(session=session, token=token)

        if res is None:
            return False, "نشست شما به پایان رسیده  لطفا یکبار خروج کرده و سپس ورود شوید.", None

        request_user_id = request_data.get("user_id")
        if request_user_id is None or str(request_user_id) != str(res["user_id"]):
            return False, "اطلاعات دریافتی شما دچار مشکل شده لطفا یکبار خروج کرده و سپس ورود شوید.", None

        return True, "", {"user_id": res["user_id"], "phone": res["phone"], "role": res["role"]}
    except Exception as e:
        service_exception_error_logging("ag_api/check", "check", str(e), request_data, {})
        return False, "اطلاعات دریافتی شما دچار مشکل شده لطفا یکبار خروج کرده و سپس ورود شوید.", None


def not_method_access_return():
    return {"status": 405, "tracking_code": None, "method_type": None,
            "error": "سرویس مورد نظر در دسترس نیست."}


def not_data_return(method_type):
    return {"status": 200, "tracking_code": None, "method_type": method_type,
            "error": "اطلاعات از سمت شما ارسال نشده است."}


def not_auth_return(message, method_type="AUTH"):
    return {"status": 404, "tracking_code": None, "method_type": method_type,
            "error": message}


def key_error_message_return(error_message, method_type):
    return {"status": 401, "tracking_code": None, "method_type": method_type,
            "error": "%s با اطلاعات شما ارسال نشده است." % str(error_message)}


def exception_error_message_return(error_message, method_type):
    return {"status": 500, "tracking_code": None, "method_type": method_type,
            "error": "مشکلی در ارتباط با سرویس‌ها پیش آمده است. درحال بررسی هستیم."}


async def key_error_logging(
        end_point: str,
        func_name: str,
        error_message: str,
        method_type: str,
) -> dict:
    """Log missing-key errors to the database and return a standard response."""
    try:
        with session_scope() as session:
            create_api_log(
                session=session,
                user_id=None,
                phone=None,
                end_point=end_point,
                func_name=func_name,
                data=None,
                error_p=f"{error_message} با اطلاعات شما ارسال نشده است.",
            )
    except Exception:
        logger.exception("key_error_logging failed")

    return key_error_message_return(error_message, method_type)


async def exception_error_logging(
        end_point: str,
        func_name: str,
        error_message: str,
        method_type: str,
) -> dict:
    """Log unexpected errors to the database and return a generic error response."""
    try:
        with session_scope() as session:
            create_api_log(
                session=session,
                user_id=None,
                phone=None,
                end_point=end_point,
                func_name=func_name,
                data=None,
                error_p=str(error_message),
            )
    except Exception:
        logger.exception("exception_error_logging failed")

    return exception_error_message_return(error_message, method_type)


def service_exception_error_logging(
        end_point: str,
        func_name: str,
        error_message: str,
        data: Any,
        user_info: Mapping[str, Any] | None,
) -> None:
    """Log service-level exceptions."""
    try:
        user_info = user_info or {}
        with session_scope() as session:
            create_api_log(
                session=session,
                user_id=user_info.get("user_id"),
                phone=user_info.get("phone"),
                end_point=end_point,
                func_name=func_name,
                data=json.dumps(sanitize_log_data(data), ensure_ascii=False),
                error_p=str(error_message),
            )
    except Exception:
        logger.exception("service_exception_error_logging failed")


def is_valid_mobile(phone: str) -> bool:
    if not phone:
        return False

    phone = phone.strip()

    if phone.startswith("+98"):
        phone = "0" + phone[3:]
    elif phone.startswith("98"):
        phone = "0" + phone[2:]

    pattern = r"^09\d{9}$"
    return bool(re.match(pattern, phone))


def check_security_code(code: str | int, check: str | int) -> bool:
    """Verify if the provided security code matches the expected value (case-insensitive)."""
    if str(code) == str(check):
        return True
    if str(code) == str(check).lower():
        return True
    if str(code) == str(check).upper():
        return True
    else:
        return False


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


def password_format_check(password: str) -> Tuple[bool, str]:
    """Validate password format: must be between 6 and 20 characters."""
    val = True
    message = ''
    if len(password) < 6:
        message = 'طول  رمز شما بایستی حداقل 6 کاراکتر باشد.'
        val = False

    if len(password) > 20:
        message = 'طول رمز شما بایستی حداکثر 20 کاراکتر باشد.'
        val = False
    if val:
        return val, ''
    else:
        return val, message


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


def get_kind_name(kind: str) -> str:
    if kind.upper() == "SCL":
        return "SCL دوپامین"
    if kind.upper() == "AG":
        return "AG استعدادسنجی"
    return kind
