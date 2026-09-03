import helper.func_helper as func_helper
import services.consultant.consultant_service as consultant_service
import services.institute.institute_service as institute_service
import services.owner_consultant.owner_consultant_service as owner_consultant_service
import services.school.school_service as school_service
from services.gateway_helpers import ACCESS_DENIED_MESSAGE, error_response, role_handler, service_response


def change_user_info(request_data, user_info):
    method_type = "UPDATE"
    result = role_handler(user_info, {
        "ins": lambda: institute_service.change_user_info(request_data=request_data, user_info=user_info),
        "sch": lambda: school_service.change_user_info(request_data=request_data, user_info=user_info),
        "con": lambda: consultant_service.change_user_info(request_data=request_data, user_info=user_info),
        "ocon": lambda: owner_consultant_service.change_user_info(request_data=request_data, user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return service_response(method_type, tracking_token, response_data, response_message)


def change_password(request_data, user_info):
    method_type = "UPDATE"
    is_valid, validation_error = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["password", "re_password"],
        method_type=method_type,
    )
    if not is_valid:
        return validation_error

    password = request_data["password"]
    re_password = request_data["re_password"]
    val, message = func_helper.password_format_check(password=password)
    if password != re_password:
        return error_response(method_type, "رمز عبور و تکرار رمز عبور باهم تطابق ندارد.")
    if not val:
        return error_response(method_type, message)

    role_table_map = {
        "ins": "ins",
        "sch": "sch",
        "ocon": "ocon",
        "con": "con",
    }
    role_table = role_table_map.get(user_info.get("role"))
    if not role_table:
        return func_helper.not_method_access_return()

    tracking_token = func_helper.update_user_and_role_password(
        request_data=request_data,
        user_info=user_info,
        role_table=role_table,
    )
    return service_response(method_type, tracking_token, None, "رمز عبور شما با موفقیت تغییر کرد.")


def change_setting(request_data, user_info):
    method_type = "UPDATE"
    if user_info["role"] == "con":
        return error_response(method_type, ACCESS_DENIED_MESSAGE)

    result = role_handler(user_info, {
        "ins": lambda: institute_service.change_setting(request_data=request_data, user_info=user_info),
        "sch": lambda: school_service.change_setting(request_data=request_data, user_info=user_info),
        "ocon": lambda: owner_consultant_service.change_setting(request_data=request_data, user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return service_response(method_type, tracking_token, response_data, response_message)


def change_student_access(request_data, user_info):
    method_type = "UPDATE"
    is_valid, validation_error = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["stu_id", "limit", "permission", "kind"],
        method_type=method_type,
    )
    if not is_valid:
        return validation_error
    if user_info["role"] == "con":
        return error_response(method_type, ACCESS_DENIED_MESSAGE)

    result = role_handler(user_info, {
        "ins": lambda: institute_service.change_student_access(request_data=request_data, user_info=user_info),
        "sch": lambda: school_service.change_student_access(request_data=request_data, user_info=user_info),
        "ocon": lambda: owner_consultant_service.change_student_access(request_data=request_data, user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return service_response(method_type, tracking_token, response_data, response_message)


def change_user_quiz_setting(request_data, user_info):
    return change_setting(request_data=request_data, user_info=user_info)


def get_dashboard(request_data, user_info):
    method_type = "SELECT"
    result = role_handler(user_info, {
        "ins": lambda: institute_service.get_dashboard(request_data=request_data, user_info=user_info),
        "sch": lambda: school_service.get_dashboard(request_data=request_data, user_info=user_info),
        "ocon": lambda: owner_consultant_service.get_dashboard(request_data=request_data, user_info=user_info),
        "con": lambda: consultant_service.get_dashboard(request_data=request_data, user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return service_response(method_type, tracking_token, response_data, response_message)


def get_consultants(request_data, user_info):
    method_type = "SELECT"
    result = role_handler(user_info, {
        "ins": lambda: institute_service.get_consultants(request_data=request_data, user_info=user_info),
        "sch": lambda: school_service.get_consultants(request_data=request_data, user_info=user_info),
    })
    if result is None:
        return error_response(method_type, ACCESS_DENIED_MESSAGE)

    tracking_token, response_data, response_message = result
    return service_response(
        method_type,
        tracking_token,
        response_data,
        response_message,
        error_message="اطلاعات مشاورین مشکل دارد، با پشتیبانی در ارتباط باشید.",
    )


def change_consultant(request_data, user_info):
    method_type = "UPDATE"
    result = role_handler(user_info, {
        "ins": lambda: institute_service.change_consultant(request_data=request_data, user_info=user_info),
        "sch": lambda: school_service.change_consultant(request_data=request_data, user_info=user_info),
    })
    if result is None:
        return error_response(method_type, ACCESS_DENIED_MESSAGE)

    tracking_token, response_data, response_message = result
    return service_response(method_type, tracking_token, response_data, response_message)


def get_students(request_data, user_info):
    method_type = "SELECT"
    result = role_handler(user_info, {
        "ins": lambda: institute_service.get_students(request_data=request_data, user_info=user_info),
        "sch": lambda: school_service.get_students(request_data=request_data, user_info=user_info),
        "con": lambda: consultant_service.get_students(request_data=request_data, user_info=user_info),
        "ocon": lambda: owner_consultant_service.get_students(request_data=request_data, user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return service_response(method_type, tracking_token, response_data, response_message)


def change_student(request_data, user_info):
    method_type = "UPDATE"
    required_fields = ["first_name", "last_name", "sex", "city", "birth_date", "student_id"]
    if user_info["role"] in ["ins", "sch"]:
        required_fields.append("con_id")
    is_valid, validation_error = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=required_fields,
        method_type=method_type,
    )
    if not is_valid:
        return validation_error

    result = role_handler(user_info, {
        "ins": lambda: institute_service.change_student(request_data=request_data, user_info=user_info),
        "sch": lambda: school_service.change_student(request_data=request_data, user_info=user_info),
        "ocon": lambda: owner_consultant_service.change_student(request_data=request_data, user_info=user_info),
        "con": lambda: consultant_service.change_student(request_data=request_data, user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return service_response(method_type, tracking_token, response_data, response_message)


def change_comment(request_data, user_info):
    method_type = "UPDATE"
    result = role_handler(user_info, {
        "con": lambda: consultant_service.change_comment(request_data=request_data, user_info=user_info),
        "ocon": lambda: owner_consultant_service.change_comment(request_data=request_data, user_info=user_info),
    })
    if result is None:
        return error_response(method_type, "متاسفانه شما از این سامانه به این سرویس دسترسی ندارید.")

    tracking_token, response_data, response_message = result
    return service_response(method_type, tracking_token, response_data, response_message)


def get_report(request_data, user_info):
    method_type = "SELECT"
    result = role_handler(user_info, {
        "ins": lambda: institute_service.get_report(request_data=request_data, user_info=user_info),
        "sch": lambda: school_service.get_report(request_data=request_data, user_info=user_info),
        "ocon": lambda: owner_consultant_service.get_report(request_data=request_data, user_info=user_info),
        "con": lambda: consultant_service.get_report(request_data=request_data, user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return service_response(method_type, tracking_token, response_data, response_message)


def get_management_report(request_data, user_info):
    method_type = "SELECT"
    if user_info["role"] == "stu":
        return error_response(method_type, "متاسفانه شما از این سامانه به این سرویس دسترسی ندارید.")

    result = role_handler(user_info, {
        "ins": lambda: institute_service.get_management_report(request_data=request_data, user_info=user_info),
        "sch": lambda: school_service.get_management_report(request_data=request_data, user_info=user_info),
        "ocon": lambda: owner_consultant_service.get_management_report(request_data=request_data, user_info=user_info),
        "con": lambda: consultant_service.get_management_report(request_data=request_data, user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return service_response(method_type, tracking_token, response_data, response_message)
