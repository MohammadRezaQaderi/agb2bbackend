from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SENSITIVE_LOG_KEYS = {
    "authorization",
    "check",
    "code",
    "otp",
    "password",
    "re_password",
    "refresh_token",
    "security_code",
    "token",
}

REDACTED_VALUE = "***REDACTED***"


def sanitize_log_data(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: REDACTED_VALUE if str(key).lower() in SENSITIVE_LOG_KEYS else sanitize_log_data(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_log_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_log_data(item) for item in value)
    return value
