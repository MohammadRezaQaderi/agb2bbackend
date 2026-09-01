from __future__ import annotations

from typing import Any


def build_display_password(stored_password: Any) -> str | None:
    if not stored_password:
        return None

    from helper.password_helper import decrypt_password

    return decrypt_password(stored_password)
