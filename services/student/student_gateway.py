import helper.func_helper as func_helper
import services.student.student_service as student_service
from services.gateway_helpers import error_response, service_response


def student_change_user_info(request_data, user_info):
    method_type = "UPDATE"
    is_valid, validation_error = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["first_name", "last_name"],
        method_type=method_type,
    )
    if not is_valid:
        return validation_error
    if user_info["role"] != "stu":
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = student_service.update_stu_user_profile(
        request_data=request_data, info=user_info
    )
    return service_response(method_type, tracking_token, response_data, response_message)


def student_change_password(request_data, user_info):
    method_type = "UPDATE"
    is_valid, validation_error = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["password", "re_password"],
        method_type=method_type,
    )
    if not is_valid:
        return validation_error

    if request_data["password"] != request_data["re_password"]:
        return error_response(method_type, "رمز عبور و تکرار رمز عبور باهم تطابق ندارد.")

    val, message = func_helper.password_format_check(password=request_data["password"])
    if not val:
        return error_response(method_type, message)

    if user_info["role"] != "stu":
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = student_service.update_stu_password(
        request_data=request_data, info=user_info
    )
    return service_response(method_type, tracking_token, response_data, response_message)


def student_get_dashboard(request_data, user_info):
    method_type = "SELECT"
    if user_info["role"] != "stu":
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = student_service.select_stu_dashboard(
        request_data=request_data, info=user_info
    )
    return service_response(method_type, tracking_token, response_data, response_message)


def student_get_quiz_table_info(request_data, user_info):
    method_type = "SELECT"
    is_valid, validation_error = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["kind"],
        method_type=method_type,
    )
    if not is_valid:
        return validation_error
    if user_info["role"] != "stu":
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = student_service.select_stu_quiz_table_info(
        request_data=request_data, info=user_info
    )
    return service_response(method_type, tracking_token, response_data, response_message)


def student_get_quiz_info(request_data, user_info):
    method_type = "SELECT"
    is_valid, validation_error = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["quiz_id", "quiz_kind"],
        method_type=method_type,
    )
    if not is_valid:
        return validation_error
    if user_info["role"] != "stu":
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = student_service.select_stu_quiz_info(
        request_data=request_data, info=user_info
    )
    if not response_data:
        return error_response(method_type, response_message or "آزمون مورد نظر شما در دسترس شما نیست.")
    return service_response(method_type, tracking_token, response_data, response_message)


def student_change_quiz_answer(request_data, user_info):
    method_type = "UPDATE"
    is_valid, validation_error = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["quiz_id", "question_Number", "question_Answer", "last_question_id", "user_id"],
        method_type=method_type,
    )
    if not is_valid:
        return validation_error
    if user_info["role"] != "stu":
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = student_service.submit_quiz_answer(
        request_data=request_data, info=user_info
    )
    return service_response(method_type, tracking_token, response_data, response_message)


def student_get_access_product(request_data, user_info):
    method_type = "SELECT"
    if user_info["role"] != "stu":
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = student_service.select_student_access_info(
        request_data=request_data, info=user_info
    )
    return service_response(method_type, tracking_token, response_data, response_message)
