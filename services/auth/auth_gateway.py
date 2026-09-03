import helper.func_helper as func_helper
import services.auth.auth_service as auth_service
from services.gateway_helpers import service_response


def sign_out(request_data, user_info):
    method_type = "DELETE"
    tracking_token, response_data, response_message = auth_service.sign_out(
        request_data=request_data, user_info=user_info
    )
    return service_response(method_type, tracking_token, response_data, response_message)


def sign_in(request_data):
    method_type = "SIGNIN"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone", "password"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    tracking_token, response_data, response_message = auth_service.sign_in(request_data=request_data)
    return service_response(method_type, tracking_token, response_data, response_message)


def student_sign_in(request_data):
    method_type = "SIGNIN"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone", "password"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    tracking_token, response_data, response_message = auth_service.sign_in_student(request_data=request_data)
    return service_response(method_type, tracking_token, response_data, response_message)


def sign_up(redis_db, request_data):
    method_type = "INSERT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone", "password", "re_password", "role"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    tracking_token, response_data, response_message = auth_service.sign_up(
        redis_db=redis_db, request_data=request_data
    )
    return service_response(method_type, tracking_token, response_data, response_message)


def send_otp(redis_db, request_data):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone", "type", "code", "check"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    tracking_token, response_data, response_message = auth_service.send_otp(
        redis_db=redis_db, request_data=request_data
    )
    return service_response(method_type, tracking_token, response_data, response_message)


def check_otp(redis_db, request_data):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone", "code", "type"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    tracking_token, response_data, response_message = auth_service.check_otp(
        redis_db=redis_db, request_data=request_data
    )
    return service_response(method_type, tracking_token, response_data, response_message)
