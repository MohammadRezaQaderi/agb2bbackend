import helper.quiz.quiz_data_extractor as quiz_data_extractor
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.settings import get_setting_for_user_quiz
from helper.request_validation import validate_request_data_fields
from helper.tracking import get_tracking_code
from services.gateway_helpers import error_response, service_response


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
    with session_scope() as session:
        res = get_setting_for_user_quiz(
            session=session,
            user_id=int(user_info["user_id"]),
            quiz_id=int(quiz_id),
        )
    token = get_tracking_code()
    if not res:
        quiz_info = quiz_data_extractor.get_quiz_info(quiz_id=quiz_id)
        info_data = {"voice": quiz_info["voice"], "description": quiz_info["description"], "setting_id": "no setting"}
        return service_response(method_type, token, info_data)

    info_data = {"voice": res["voice"], "description": res["description"], "setting_id": res["setting_id"]}
    return service_response(method_type, token, info_data)


def get_quiz_info(request_data, user_info):
    method_type = "SELECT"
    if user_info["role"] not in ["ins", "sch", "ocon", "con"]:
        return error_response(method_type, "متاسفانه شما از این سامانه به این سرویس دسترسی ندارید.")

    tracking_token = get_tracking_code()
    response_data = quiz_data_extractor.get_quiz_table_info()
    return service_response(method_type, tracking_token, response_data, "")
