import base64
import os
import pyodbc
import string
import random
import json
import uuid
import re
from datetime import datetime
from random import randint
from typing import Any, Mapping, Tuple, Optional

from walrus import Database
from cryptography.fernet import Fernet, InvalidToken

import helper.db.db_helper as db_helper
from config import PASSWORD_SECRET_KEY, DB_DRIVER, DB_SERVER, DB_DATABASE, DB_UID, DB_PWD, DB_TRUST_CERT, REDIS_HOST, \
    REDIS_PORT, REDIS_DB, REDIS_PASSWORD

_PASSWORD_FERNET: Optional[Fernet] = None


def get_tracking_code() -> str:
    return str(uuid.uuid4())


def save_base64_image(pic_value: str | None, last_pic: str | None, storage_dir: str) -> str | None:
    if not pic_value:
        return None

    if not pic_value.startswith("data:image") and "," not in pic_value:
        return pic_value

    if "," in pic_value:
        header, encoded_data = pic_value.split(",", 1)
        ext = header.split(";")[0].split("/")[-1] if "/" in header else "jpg"
    else:
        encoded_data = pic_value
        ext = "jpg"

    if ext == "jpeg":
        ext = "jpg"

    os.makedirs(storage_dir, exist_ok=True)
    new_file_name = f"{get_tracking_code()}.{ext}"
    file_path = os.path.join(storage_dir, new_file_name)

    with open(file_path, "wb") as fh:
        fh.write(base64.b64decode(encoded_data))

    if last_pic:
        last_path = os.path.join(storage_dir, os.path.basename(last_pic))
        if os.path.exists(last_path):
            os.remove(last_path)

    return new_file_name

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


def _db_config() -> dict:
    """Return DB connection kwargs, sourcing overrides from environment variables."""
    return {
        "driver": DB_DRIVER,
        "host": DB_SERVER,
        "database": DB_DATABASE,
        "UID": DB_UID,
        "PWD": DB_PWD,
        "TrustServerCertificate": DB_TRUST_CERT,
    }


def _redis_config() -> dict:
    """Return Redis connection kwargs, sourcing overrides from environment variables."""
    return {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "db": REDIS_DB,
        "password": REDIS_PASSWORD if REDIS_PASSWORD else None,
    }


def _get_password_fernet() -> Fernet:
    """Return a singleton Fernet instance configured with PASSWORD_SECRET_KEY."""
    global _PASSWORD_FERNET
    if _PASSWORD_FERNET is None:
        key = PASSWORD_SECRET_KEY.encode("utf-8")
        _PASSWORD_FERNET = Fernet(key)
    return _PASSWORD_FERNET


def encrypt_password(plain_password: str) -> str:
    """
    Encrypt a plain-text password for storage.

    Args:
        plain_password: The user-facing password in plain text.

    Returns:
        Encrypted string suitable for storing in the database.
    """
    if plain_password is None:
        return ""
    fernet = _get_password_fernet()
    token = fernet.encrypt(str(plain_password).encode("utf-8"))
    return token.decode("utf-8")


def decrypt_password(stored_password: str) -> Optional[str]:
    """
    Decrypt a stored password back to plain text.

    If decryption fails (e.g., value is already plain text or corrupted),
    returns the original value as a fallback, or None on fatal error.
    """
    if not stored_password:
        return None
    fernet = _get_password_fernet()
    try:
        return fernet.decrypt(stored_password.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # Probably already plain text or from a previous scheme
        return stored_password
    except Exception as e:
        print(f"[Password] Error decrypting password: {e}")
        return None


def verify_password(plain_password: str, stored_password: str) -> bool:
    """
    Verify that a plain-text password matches the stored (encrypted) password.
    """
    decrypted = decrypt_password(stored_password)
    if decrypted is None:
        return False
    return str(plain_password) == str(decrypted)


async def db_connection() -> tuple[pyodbc.Connection, pyodbc.Cursor]:
    """Establish and return a SQL Server connection and cursor."""
    conn = pyodbc.connect(**_db_config())
    return conn, conn.cursor()


async def close_db_connection(conn: pyodbc.Connection | None, cursor: pyodbc.Cursor | None) -> None:
    """Safely close the SQL Server connection and cursor."""
    try:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    except pyodbc.Error as e:
        print(f"[DB] Error closing connection: {e}")


async def redis_connection() -> Database:
    """Establish and return a Redis connection."""
    cfg = _redis_config()
    try:
        redis_db: Database = Database(
            host=cfg["host"],
            port=cfg["port"],
            db=cfg["db"],
            password=cfg["password"],
        )
        redis_db.ping()
        return redis_db
    except Exception as e:
        print(f"[Redis] Connection failed: {e}")
        raise


async def close_redis_connection(redis_db: Database | None) -> None:
    """Safely close the Redis connection."""
    try:
        if redis_db is not None:
            redis_db.close()
    except Exception as e:
        print(f"[Redis] Error closing connection: {e}")


async def authorizer(conn: pyodbc.Connection | None, cursor: pyodbc.Cursor | None, request_data: Mapping[str, Any]):
    try:
        if request_data.get("token"):
            if request_data["token"] is not None:
                query = "SELECT user_id, phone, role FROM tokens WHERE token = ?"
                res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=request_data["token"])
                if res is None:
                    return False, "نشست شما به پایان رسیده  لطفا یکبار خروج کرده و سپس ورود شوید.", None
                elif request_data.get("user_id"):
                    if not request_data["user_id"] == res.user_id:
                        return False, "اطلاعات دریافتی شما دچار مشکل شده لطفا یکبار خروج کرده و سپس ورود شوید.", None
                    else:
                        return True, "", {"user_id": res.user_id, "phone": res.phone, "role": res.role}
                else:
                    return False, "اطلاعات دریافتی شما دچار مشکل شده لطفا یکبار خروج کرده و سپس ورود شوید.", None
            else:
                return False, "اطلاعات دریافتی شما دچار مشکل شده لطفا یکبار خروج کرده و سپس ورود شوید.", None
        else:
            return False, "اطلاعات دریافتی شما دچار مشکل شده لطفا یکبار خروج کرده و سپس ورود شوید.", None
    except Exception as e:
        service_exception_error_logging(conn, cursor, "ag_api/check", "check", str(e), request_data, {})
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
    conn, cursor = None, None
    try:
        conn, cursor = await db_connection()
        field_log = '([user_id], [phone], [end_point], [func_name], [data], [error_p])'
        values_log = (
            None, None, end_point, func_name,
            None, f"{error_message} با اطلاعات شما ارسال نشده است."
        )
        db_helper.insert_value(
            conn=conn,
            cursor=cursor,
            table_name='api_logs',
            fields=field_log,
            values=values_log
        )
    except Exception as e:
        print(f"[Logging Error] key_error_logging failed: {e}")
    finally:
        if conn or cursor:
            await close_db_connection(conn, cursor)

    return key_error_message_return(error_message, method_type)


async def exception_error_logging(
        end_point: str,
        func_name: str,
        error_message: str,
        method_type: str,
) -> dict:
    """Log unexpected errors to the database and return a generic error response."""
    conn, cursor = None, None
    try:
        conn, cursor = await db_connection()
        field_log = '([user_id], [phone], [end_point], [func_name], [data], [error_p])'
        values_log = (
            None, None, end_point, func_name,
            None, str(error_message)
        )
        db_helper.insert_value(
            conn=conn,
            cursor=cursor,
            table_name='api_logs',
            fields=field_log,
            values=values_log
        )
    except Exception as e:
        print(f"[Logging Error] exception_error_logging failed: {e}")
    finally:
        if conn or cursor:
            await close_db_connection(conn, cursor)

    return exception_error_message_return(error_message, method_type)


def service_exception_error_logging(
        conn: pyodbc.Connection,
        cursor: pyodbc.Cursor,
        end_point: str,
        func_name: str,
        error_message: str,
        data: Mapping[str, Any],
        info: Mapping[str, Any],
) -> None:
    """Log service-level exceptions using an existing connection."""
    try:
        field_log = '([user_id], [phone], [end_point], [func_name], [data], [error_p])'
        values_log = (
            info.get("user_id"), info.get("phone"), end_point, func_name,
            json.dumps(data, ensure_ascii=False), str(error_message))
        db_helper.insert_value(conn=conn, cursor=cursor, table_name='api_logs', fields=field_log,
                               values=values_log)
    except Exception as e:
        print(f"[Logging Error] service_exception_error_logging failed: {e}")


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


def random_generate_phone(conn: pyodbc.Connection, cursor: pyodbc.Cursor, n: int) -> str:
    """Generate a unique random phone number with prefix '009' and n-digit suffix."""
    range_start = 10 ** (n - 1)
    range_end = (10 ** n) - 1
    phone = '009' + str(randint(range_start, range_end))
    query = 'SELECT * FROM users WHERE phone = ?'
    res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)
    if res is None:
        return phone
    else:
        return random_generate_phone(conn=conn, cursor=cursor, n=n)


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


def insert_user(
        conn: pyodbc.Connection,
        cursor: pyodbc.Cursor,
        request_data: Mapping[str, Any],
        info: Mapping[str, Any],
) -> Tuple[Optional[int], Optional[str], str]:
    """Insert a new consultant user into the database with a randomly generated password."""
    try:
        query = 'SELECT phone FROM users WHERE phone = ?'
        res_check_user_phone = db_helper.search_table(conn=conn, cursor=cursor, query=query,
                                                      field=request_data["phone"])
        if res_check_user_phone is not None:
            return None, None, "شماره تلفن وارد شده در سامانه موجود می‌باشد لطفا شماره تلفن دیگری وارد نمایید."
        password = random_generate_password()
        field = '([phone], [password], [role])'
        values = (request_data["phone"], encrypt_password(password), 'con',)
        response = db_helper.insert_value(conn=conn, cursor=cursor, table_name="users", fields=field,
                                          values=values, id_column="user_id")
        return response["id"], password, ""
    except Exception as e:
        # todo use the func_helper for logs
        conn.rollback()
        field_log = '([user_id], [phone], [end_point], [func_name], [data], [error_p])'
        values_log = (
            info.get("user_id"), info.get("phone"), "ag_api/func_helper", "insert_user",
            json.dumps(request_data), str(e))
        db_helper.insert_value(conn=conn, cursor=cursor, table_name='api_logs', fields=field_log,
                               values=values_log)
        return None, None, "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."


def insert_user_student(
        conn: pyodbc.Connection,
        cursor: pyodbc.Cursor,
        info: Mapping[str, Any],
) -> Tuple[Optional[int], Optional[str], Optional[str], str]:
    """Insert a new student user with a randomly generated phone number and password."""
    try:
        phone = random_generate_phone(conn, cursor, 8)
        password = random_generate_password()
        field = '([phone], [password], [role])'
        values = (phone, encrypt_password(password), 'stu',)
        response = db_helper.insert_value(conn=conn, cursor=cursor, table_name="users", fields=field,
                                          values=values, id_column="user_id")
        return response["id"], password, phone, ""
    except Exception as e:
        # todo use the func_helper for logs
        conn.rollback()
        field_log = '([user_id], [phone], [end_point], [func_name], [data], [error_p])'
        values_log = (
            info.get("user_id"), info.get("phone"), "ag_api/func_helper", "insert_user",
            None, str(e))
        db_helper.insert_value(conn=conn, cursor=cursor, table_name='api_logs', fields=field_log,
                               values=values_log)
        return None, None, None, "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."


def get_payment_id(conn: pyodbc.Connection, cursor: pyodbc.Cursor) -> int:
    """Generate a unique payment ID that doesn't exist in the database."""
    payment_id = randint(1, 999999)
    query = 'SELECT * FROM payment WHERE payment_id = ?'
    res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=payment_id)
    if res is None:
        return payment_id
    else:
        return get_payment_id(conn=conn, cursor=cursor)


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


def add_capacity_signup(
        conn: pyodbc.Connection,
        cursor: pyodbc.Cursor,
        user_id: int,
        phone: str,
) -> Optional[int]:
    """Create a capacity record and associated package entries for a new user signup."""
    field = '([user_id], [phone])'
    values = (user_id, phone)
    response = db_helper.insert_value(
        conn=conn,
        cursor=cursor,
        table_name="capacity",
        fields=field,
        values=values,
        id_column="capacity_id"
    )
    if not response or not response.get("id"):
        print("Error: capacity insert failed")
        return None

    capacity_id = response["id"]

    field_package = '([capacity_id], [user_id], [phone], [package_name], [allowed])'
    for package_name in PACKAGES_DATA.keys():
        values_package = (capacity_id, user_id, phone, package_name, 1)
        db_helper.insert_value(
            conn=conn,
            cursor=cursor,
            table_name="capacity_package",
            fields=field_package,
            values=values_package
        )

    return capacity_id


def update_user_and_role_password(
        conn: pyodbc.Connection,
        cursor: pyodbc.Cursor,
        request_data: Mapping[str, Any],
        info: Mapping[str, Any],
        role_table: str,
) -> Optional[str]:
    """
    Update password in both `users` table and a role-specific table.

    This helper encapsulates the common pattern used by:
    - update_ins_password
    - update_sch_password
    - update_wcon_password
    - update_con_password

    Args:
        conn: Active database connection.
        cursor: Active database cursor.
        request_data: Request payload containing at least the new 'password'.
        info: Context information containing 'user_id'.
        role_table: Name of the role-specific table ('ins', 'sch', 'wCon', 'con').

    Returns:
        New tracking token (str) on success, or None on failure.
    """
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_id = str(info["user_id"])
        encrypted_password = encrypt_password(request_data["password"])
        # Update main users table
        db_helper.update_record(
            conn, cursor, 'users',
            ['password', 'edited_time'],
            [encrypted_password, now_str],
            'user_id = ?', [user_id]
        )

        # Update role-specific table
        db_helper.update_record(
            conn, cursor, role_table,
            ['password', 'edited_time'],
            [encrypted_password, now_str],
            'user_id = ?', [user_id]
        )

        token = get_tracking_code()
        return token
    except Exception as e:
        conn.rollback()
        service_exception_error_logging(
            conn, cursor, "ag_api/password", f"update_{role_table}_password",
            str(e), request_data, info
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
        conn: pyodbc.Connection,
        cursor: pyodbc.Cursor,
        request_data: Mapping[str, Any],
        info: Mapping[str, Any],
        role_type: str,
        id_field: str,
        end_point: str,
) -> Tuple[Optional[str], str]:
    """
    Update student access permissions and manage capacity tracking.

    This is a reusable function for institute, school, and owner_consultant roles.

    Args:
        conn: Active database connection
        cursor: Active database cursor
        request_data: Request data containing:
            - stu_id: Student ID (user_id from stu table)
            - kind: Package name (key from PACKAGES_DATA, e.g., "AG", "SCL")
            - permission: Permission flag (1 or 0) indicating grant/revoke access
            - limit: Limit flag (1 or 0) for the package
        info: Context info containing user_id
        role_type: Role type ("ins", "sch", or "wCon") for error logging
        id_field: Field name to check ownership ("ins_id" for all three)
        end_point: API endpoint for error logging

    Returns:
        Tuple of (token, message) on success, (None, error_message) on failure

    Note:
        Access is stored in format: {"AG": {"permission": 1, "limit": 1}}
        If kind exists in student access, only limit is updated.
        If kind doesn't exist, it's added with both permission and limit.
    """
    try:
        user_id = info["user_id"]
        stu_id = request_data.get("stu_id")

        if not stu_id:
            return None, "شناسه دانش‌آموز ارسال نشده است."

        query_check = f'SELECT {id_field}, access FROM stu WHERE user_id = ?'
        res_stu = db_helper.search_table(conn=conn, cursor=cursor, query=query_check, field=stu_id)

        if res_stu is None:
            return None, "دانش‌آموز یافت نشد."

        org_id = getattr(res_stu, id_field, None)
        if org_id != user_id:
            return None, "این دانش‌آموز به شما تعلق ندارد."

        current_access_str = res_stu.access or '{}'
        try:
            current_access = json.loads(current_access_str) if current_access_str else {}
        except (json.JSONDecodeError, TypeError):
            current_access = {}

        kind = request_data.get("kind")
        if not kind:
            return None, "نوع بسته (kind) ارسال نشده است."

        if kind not in PACKAGES_DATA:
            valid_packages = "، ".join(f"{package} ({get_kind_name(package)})" for package in PACKAGES_DATA.keys())
            return None, f"نوع بسته {kind} معتبر نیست. بسته‌های معتبر: {valid_packages}"

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

        is_granting = bool(permission)

        if is_granting != was_granted:
            query_capacity = """
                SELECT allowed, used
                FROM capacity_package
                WHERE user_id = ? AND package_name = ?
            """
            res_capacity = db_helper.search_fetchall(
                conn=conn, cursor=cursor,
                query=query_capacity,
                field=(user_id, kind)
            )

            if not res_capacity:
                return None, f"بسته {get_kind_name(kind=kind)} برای شما تعریف نشده است."

            capacity_info = res_capacity[0]
            allowed = capacity_info.get("allowed", 0)
            used = capacity_info.get("used", 0)

            if is_granting:
                if allowed <= 0:
                    return None, f"ظرفیت بسته {get_kind_name(kind=kind)} تکمیل شده است."

                db_helper.update_record(
                    conn, cursor, 'capacity_package',
                    ['used', 'allowed', 'edited_time'],
                    [used + 1, allowed - 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    'user_id = ? AND package_name = ?',
                    [str(user_id), kind]
                )
            # else:
            #     # Decrement used count (but don't go below 0)
            #     new_used = max(0, used - 1)
            #     db_helper.update_record(
            #         conn, cursor, 'capacity_package',
            #         ['used', 'edited_time'],
            #         [new_used, datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            #         'user_id = ? AND package_name = ?',
            #         [str(user_id), kind]
            #     )

        updated_access_json = json.dumps(current_access, ensure_ascii=False)
        db_helper.update_record(
            conn, cursor, 'stu',
            ['access', 'edited_time'],
            [updated_access_json, datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            'user_id = ?',
            [str(stu_id)]
        )

        token = get_tracking_code()
        return token, "دسترسی دانش‌آموز با موفقیت به‌روزرسانی شد."

    except Exception as e:
        conn.rollback()
        service_exception_error_logging(
            conn, cursor, end_point,
            f"update_student_access_and_capacity_{role_type}",
            str(e), request_data, info
        )
        return None, "مشکلی در به‌روزرسانی دسترسی دانش‌آموز رخ داده است."


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
