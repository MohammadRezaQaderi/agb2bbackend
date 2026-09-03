import random
import string
from random import randint

from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.auth import user_phone_exists


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
