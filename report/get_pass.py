from cryptography.fernet import Fernet, InvalidToken
from typing import Any, Mapping, Tuple, Optional

_PASSWORD_FERNET: Optional[Fernet] = None


def _get_password_fernet() -> Fernet:
    """Return a singleton Fernet instance configured with PASSWORD_SECRET_KEY."""
    global _PASSWORD_FERNET
    if _PASSWORD_FERNET is None:
        key = "8q2F8J7x1a6F1C5B8L3q6N2v9R4s7W0yF1z3X6C8q2M=".encode("utf-8")
        _PASSWORD_FERNET = Fernet(key)
    return _PASSWORD_FERNET


def decrypt_password(stored_password: str):
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
        return stored_password
    except Exception as e:
        print(f"[Password] Error decrypting password: {e}")
        return None


print(decrypt_password("gAAAAABplq4MFaY4NDqvnewbJ-H-CgnB4dlZqljxe4p8SqixMFzsM9bsqgRvUbpKXl6mkL8y5uQT-P4RO2Cb8Z9cq4ztQiOtZw=="))
