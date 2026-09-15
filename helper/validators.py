import re
from typing import Tuple


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
    return False


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
    return val, message
