import json
import logging
from typing import Any, Mapping

from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.other import create_api_log
from helper.log_sanitizer import sanitize_log_data


logger = logging.getLogger(__name__)


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
