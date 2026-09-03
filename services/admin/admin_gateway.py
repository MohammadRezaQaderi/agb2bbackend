import helper.func_helper as func_helper
import services.admin.admin_service as admin_service
from services.gateway_helpers import service_response


def _log_admin_response(admin_context, action_type, request_data, response):
    admin_service.log_admin_action(
        admin_context=admin_context,
        action_type=action_type,
        request_data=request_data,
        response=response,
    )
    return response


def admin_change_capacity(request_data, admin_context=None, action_type="ag_change_capacity"):
    method_type = "UPDATE"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone", "kind", "count"],
        method_type=method_type,
    )
    if not is_valid:
        return _log_admin_response(admin_context, action_type, request_data, error_response)

    tracking_token, response_data, response_message = admin_service.change_capacity(request_data=request_data)
    response = service_response(method_type, tracking_token, response_data, response_message)
    return _log_admin_response(admin_context, action_type, request_data, response)


def admin_get_user_info(request_data, admin_context=None, action_type="ag_get_user_info"):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone"],
        method_type=method_type,
    )
    if not is_valid:
        return _log_admin_response(admin_context, action_type, request_data, error_response)

    tracking_token, response_data, response_message = admin_service.get_user_info(request_data=request_data)
    response = service_response(method_type, tracking_token, response_data, response_message)
    return _log_admin_response(admin_context, action_type, request_data, response)


def admin_check_student_quiz_answer(request_data, admin_context=None, action_type="ag_check_student_quiz_answer"):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone"],
        method_type=method_type,
    )
    if not is_valid:
        return _log_admin_response(admin_context, action_type, request_data, error_response)

    tracking_token, response_data, response_message = admin_service.check_student_quiz_answer(
        request_data=request_data
    )
    response = service_response(method_type, tracking_token, response_data, response_message)
    return _log_admin_response(admin_context, action_type, request_data, response)
