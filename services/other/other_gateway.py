import logging

from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.students import get_student_access_for_relation
from helper.request_validation import validate_request_data_fields
from helper.service_errors import not_method_access_return
import services.other.other_service as other_service
from services.gateway_helpers import DEFAULT_SERVICE_ERROR, error_response, service_response


logger = logging.getLogger(__name__)


def check_student_access(student_user_id, user_info):
    """
    Check if the current user has access to the specified student.
    For ins/sch roles: check if student's owner_user_id matches user_id.
    For con/ocon roles: check if student's consultant_user_id matches user_id.
    Returns True if access is granted, False otherwise.
    """
    try:
        with session_scope() as session:
            res = get_student_access_for_relation(session=session, stu_user_id=int(student_user_id))
        if not res:
            return False

        role = user_info.get("role")
        user_id = user_info.get("user_id")

        if role in ["ins", "sch"]:
            return res["owner_user_id"] == user_id
        if role in ["con", "ocon"]:
            return res["consultant_user_id"] == user_id

        return False
    except Exception:
        logger.exception("Error checking student access")
        return False


def get_report_data(request_data, user_info):
    method_type = "SELECT"
    is_valid, validation_error = validate_request_data_fields(
        request_data=request_data,
        required_fields=["student_id", "report_type"],
        method_type=method_type,
    )
    if not is_valid:
        return validation_error

    if user_info["role"] not in ["ins", "sch", "con", "ocon"]:
        return not_method_access_return()

    student_id = request_data.get("student_id")
    if not check_student_access(student_user_id=student_id, user_info=user_info):
        return error_response(method_type, "شما به این دانش‌آموز دسترسی ندارید.")

    tracking_token, response_data, response_message = other_service.get_report_data(
        request_data=request_data,
        user_info=user_info,
    )
    return service_response(
        method_type,
        tracking_token,
        response_data,
        response_message,
        error_message="خطا در دریافت اطلاعات گزارش.",
    )


def get_transactions(request_data, user_info):
    method_type = "SELECT"
    if user_info["role"] in ["ocon", "ins", "sch"]:
        tracking_token, response_data, response_message = other_service.get_transactions(request_data, user_info)
        return service_response(method_type, tracking_token, response_data, response_message)
    return not_method_access_return()


def apply_discount(request_data, user_info):
    method_type = "SELECT"
    is_valid, validation_error = validate_request_data_fields(
        request_data=request_data,
        required_fields=["discount_code", "total_value"],
        method_type=method_type,
    )
    if not is_valid:
        return validation_error

    tracking_token, response_data, response_message = other_service.apply_discount(
        request_data=request_data,
        user_info=user_info,
    )
    return service_response(method_type, tracking_token, response_data, response_message)


def add_payment_order(request_data, user_info):
    method_type = "INSERT"
    # Validation is intentionally deferred because legacy clients send package
    # fields inconsistently here.
    if user_info["role"] in ["ocon", "ins", "sch"]:
        tracking_token, response_data, response_message = other_service.order_payment(
            request_data=request_data,
            user_info=user_info,
        )
        return service_response(method_type, tracking_token, response_data, response_message)
    return error_response(method_type, DEFAULT_SERVICE_ERROR)


def get_comments():
    method_type = "SELECT"
    tracking_token, response_data, response_message = other_service.get_comments()
    return service_response(method_type, tracking_token, response_data, response_message)


def add_comment(request_data):
    method_type = "INSERT"
    tracking_token, response_data, response_message = other_service.add_comment(
        request_data=request_data
    )
    return service_response(method_type, tracking_token, response_data, response_message)


def mark_notification_read(request_data, user_info):
    method_type = "INSERT"
    is_valid, validation_error = validate_request_data_fields(
        request_data=request_data,
        required_fields=["notification_id"],
        method_type=method_type,
    )
    if not is_valid:
        return validation_error

    tracking_token, response_data, response_message = other_service.mark_notification_read(
        request_data=request_data,
        user_info=user_info,
    )
    return service_response(method_type, tracking_token, response_data, response_message)
