from typing import Any, Mapping, Optional

from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.auth import update_user_password
from helper.password_helper import encrypt_password
from helper.service_errors import service_exception_error_logging
from helper.tracking import get_tracking_code


def update_user_and_role_password(
        request_data: Mapping[str, Any],
        user_info: Mapping[str, Any],
        role_table: str,
) -> Optional[str]:
    """
    Update password in the canonical `users` table.

    `role_table` is kept for backward-compatible caller signatures and logging.
    """
    try:
        encrypted_password = encrypt_password(request_data["password"])
        with session_scope() as session:
            update_user_password(
                session=session,
                user_id=user_info["user_id"],
                encrypted_password=encrypted_password,
            )

        return get_tracking_code()
    except Exception as e:
        service_exception_error_logging(
            "ag_api/password",
            f"update_{role_table}_password",
            str(e),
            request_data,
            user_info,
        )
        return None
