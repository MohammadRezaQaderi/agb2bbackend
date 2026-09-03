from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from config import PASSWORD_SECRET_KEY

PASSWORD_HASH_PREFIX = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 260000

_PASSWORD_FERNET: Optional[Fernet] = None
logger = logging.getLogger(__name__)


def _get_password_fernet() -> Fernet:
    global _PASSWORD_FERNET
    if _PASSWORD_FERNET is None:
        if not PASSWORD_SECRET_KEY:
            raise RuntimeError("AG_PASSWORD_SECRET_KEY must be set before password encryption/decryption")
        _PASSWORD_FERNET = Fernet(PASSWORD_SECRET_KEY.encode("utf-8"))
    return _PASSWORD_FERNET


def hash_password(plain_password: str) -> str:
    if plain_password is None:
        return ""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        str(plain_password).encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return f"{PASSWORD_HASH_PREFIX}${PASSWORD_HASH_ITERATIONS}${salt}${digest}"


def is_password_hash(stored_password: str | None) -> bool:
    return bool(stored_password and str(stored_password).startswith(f"{PASSWORD_HASH_PREFIX}$"))


def verify_password_hash(plain_password: str, stored_password: str) -> bool:
    try:
        prefix, iterations, salt, expected_digest = str(stored_password).split("$", 3)
        if prefix != PASSWORD_HASH_PREFIX:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            str(plain_password).encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(digest, expected_digest)
    except Exception:
        return False


def encrypt_password(plain_password: str) -> str:
    if plain_password is None:
        return ""
    return _get_password_fernet().encrypt(str(plain_password).encode("utf-8")).decode("utf-8")


def decrypt_password(stored_password: str) -> Optional[str]:
    if not stored_password:
        return None
    if is_password_hash(stored_password):
        return None

    try:
        return _get_password_fernet().decrypt(stored_password.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return stored_password
    except Exception:
        logger.exception("Error decrypting password")
        return None


def verify_password(plain_password: str, stored_password: str) -> bool:
    if is_password_hash(stored_password):
        return verify_password_hash(plain_password, stored_password)

    decrypted = decrypt_password(stored_password)
    if decrypted is None:
        return False
    return str(plain_password) == str(decrypted)
