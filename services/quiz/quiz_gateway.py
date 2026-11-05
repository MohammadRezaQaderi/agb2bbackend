import helper.quiz.quiz_data_extractor as quiz_data_extractor
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.settings import get_setting_for_user_quiz
from helper.request_validation import validate_request_data_fields
from helper.tracking import get_tracking_code
from services.gateway_helpers import error_response, service_response


def _request_package_name(request_data):
    return str(
        request_data.get("package_name")
        or request_data.get("quiz_kind")
        or request_data.get("kind")
        or "AG"
    ).strip().upper()


def student_get_quiz_setting(request_data, user_info):
    method_type = "SELECT"
    is_valid, validation_error = validate_request_data_fields(
        request_data=request_data,
        required_fields=["quiz_id"],
        method_type=method_type,
    )
    if not is_valid:
        return validation_error
    return get_quiz_setting(request_data=request_data, user_info=user_info)


def get_quiz_setting(request_data, user_info):
    method_type = "SELECT"
    is_valid, validation_error = validate_request_data_fields(
        request_data=request_data,
        required_fields=["quiz_id"],
        method_type=method_type,
    )
    if not is_valid:
        return validation_error

    quiz_id = request_data["quiz_id"]
    package_name = _request_package_name(request_data)
    if quiz_data_extractor.get_definition_version(package_name) is None:
        return error_response(method_type, "نوع آزمون معتبر نیست.")
    with session_scope() as session:
        res = get_setting_for_user_quiz(
            session=session,
            user_id=int(user_info["user_id"]),
            package_name=package_name,
            quiz_id=int(quiz_id),
        )
    token = get_tracking_code()
    if not res:
        quiz_info = quiz_data_extractor.get_quiz_info(quiz_id=quiz_id, kind=package_name)
        if not quiz_info:
            return error_response(method_type, "آزمون مورد نظر یافت نشد.")
        info_data = {
            "voice": quiz_info["voice"],
            "description": quiz_info["description"],
            "setting_id": "no setting",
            "package_name": package_name,
        }
        return service_response(method_type, token, info_data)

    info_data = {
        "voice": res["voice"],
        "description": res["description"],
        "setting_id": res["setting_id"],
        "package_name": res["package_name"],
    }
    return service_response(method_type, token, info_data)


def get_quiz_info(request_data, user_info):
    method_type = "SELECT"
    if user_info["role"] not in ["ins", "sch", "ocon", "con"]:
        return error_response(method_type, "متاسفانه شما از این سامانه به این سرویس دسترسی ندارید.")

    tracking_token = get_tracking_code()
    response_data = quiz_data_extractor.get_quiz_table_info()
    return service_response(method_type, tracking_token, response_data, "")
