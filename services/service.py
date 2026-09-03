import logging

import helper.func_helper as func_helper
import helper.quiz.quiz_data_extractor as quiz_data_extractor
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.accounts import create_consultant_account, create_student_account
from helper.db.sqlalchemy.queries.auth import user_phone_exists
from helper.db.sqlalchemy.queries.settings import get_setting_for_user_quiz
from helper.db.sqlalchemy.queries.students import get_student_access_for_relation
from services.admin.admin_gateway import (
    admin_change_capacity,
    admin_check_student_quiz_answer,
    admin_get_user_info,
)
from services.auth.auth_gateway import (
    check_otp,
    send_otp,
    sign_in,
    sign_out,
    sign_up,
    student_sign_in,
)
import services.consultant.consultant_service as consultant_service
import services.institute.institute_service as institute_service
import services.other.other_service as other_service
import services.owner_consultant.owner_consultant_service as owner_consultant_service
import services.school.school_service as school_service
from services.student.student_gateway import (
    student_change_password,
    student_change_quiz_answer,
    student_change_user_info,
    student_get_access_product,
    student_get_dashboard,
    student_get_quiz_info,
    student_get_quiz_table_info,
)
from services.gateway_helpers import (
    ACCESS_DENIED_MESSAGE,
    DEFAULT_SERVICE_ERROR,
    error_response as _error_response,
    role_handler as _role_handler,
    service_response as _service_response,
)


logger = logging.getLogger(__name__)


def service_response(method_type, tracking_token, response_data=None, response_message="", error_message=None,
                     **extra_response):
    return _service_response(method_type, tracking_token, response_data, response_message, error_message,
                             **extra_response)


def _generate_available_student_phone(session, attempts=20):
    for _ in range(attempts):
        phone = func_helper.random_phone_candidate(8)
        if not user_phone_exists(session=session, phone=phone):
            return phone
    raise ValueError("Could not generate a unique student phone.")


def change_user_info(request_data, user_info):
    method_type = "UPDATE"
    result = _role_handler(user_info, {
        "ins": lambda: institute_service.change_user_info(request_data=request_data,
                                                          user_info=user_info),
        "sch": lambda: school_service.change_user_info(request_data=request_data,
                                                       user_info=user_info),
        "con": lambda: consultant_service.change_user_info(request_data=request_data, user_info=user_info),
        "ocon": lambda: owner_consultant_service.change_user_info(request_data=request_data, user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


def change_password(request_data, user_info):
    method_type = "UPDATE"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["password", "re_password"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    password = request_data["password"]
    re_password = request_data["re_password"]
    val, message = func_helper.password_format_check(password=password)
    if password != re_password:
        return _error_response(method_type, "رمز عبور و تکرار رمز عبور باهم تطابق ندارد.")
    if not val:
        return _error_response(method_type, message)
    role = user_info.get("role")
    role_table_map = {
        "ins": "ins",
        "sch": "sch",
        "ocon": "ocon",
        "con": "con",
    }

    role_table = role_table_map.get(role)
    if not role_table:
        return func_helper.not_method_access_return()

    tracking_token = func_helper.update_user_and_role_password(
        request_data=request_data,
        user_info=user_info,
        role_table=role_table,
    )
    response_data = None
    response_message = "رمز عبور شما با موفقیت تغییر کرد."
    return _service_response(method_type, tracking_token, response_data, response_message)


def student_get_quiz_setting(request_data, user_info):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["quiz_id"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response
    return get_quiz_setting(request_data=request_data, user_info=user_info)


def change_setting(request_data, user_info):
    method_type = "UPDATE"
    if user_info["role"] == "con":
        return _error_response(method_type, ACCESS_DENIED_MESSAGE)

    result = _role_handler(user_info, {
        "ins": lambda: institute_service.change_setting(request_data=request_data,
                                                        user_info=user_info),
        "sch": lambda: school_service.change_setting(request_data=request_data,
                                                     user_info=user_info),
        "ocon": lambda: owner_consultant_service.change_setting(request_data=request_data,
                                                                user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


def change_student_access(request_data, user_info):
    method_type = "UPDATE"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["stu_id", "limit", "permission", "kind"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response
    if user_info["role"] == "con":
        return _error_response(method_type, ACCESS_DENIED_MESSAGE)

    result = _role_handler(user_info, {
        "ins": lambda: institute_service.change_student_access(request_data=request_data,
                                                               user_info=user_info),
        "sch": lambda: school_service.change_student_access(request_data=request_data,
                                                            user_info=user_info),
        "ocon": lambda: owner_consultant_service.change_student_access(request_data=request_data, user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


def change_user_quiz_setting(request_data, user_info):
    return change_setting(request_data=request_data, user_info=user_info)


# The users functionality

def get_dashboard(request_data, user_info):
    method_type = "SELECT"
    result = _role_handler(user_info, {
        "ins": lambda: institute_service.get_dashboard(request_data=request_data,
                                                       user_info=user_info),
        "sch": lambda: school_service.get_dashboard(request_data=request_data,
                                                    user_info=user_info),
        "ocon": lambda: owner_consultant_service.get_dashboard(request_data=request_data,
                                                               user_info=user_info),
        "con": lambda: consultant_service.get_dashboard(request_data=request_data, user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


# this gateway is for get the consultants list of roles
def get_consultants(request_data, user_info):
    method_type = "SELECT"
    result = _role_handler(user_info, {
        "ins": lambda: institute_service.get_consultants(request_data=request_data,
                                                         user_info=user_info),
        "sch": lambda: school_service.get_consultants(request_data=request_data,
                                                      user_info=user_info),
    })
    if result is None:
        return _error_response(method_type, ACCESS_DENIED_MESSAGE)

    tracking_token, response_data, response_message = result
    return _service_response(
        method_type,
        tracking_token,
        response_data,
        response_message,
        error_message="اطلاعات مشاورین مشکل دارد، با پشتیبانی در ارتباط باشید.",
    )


# this gateway for insert consultant for user role
def add_consultant(request_data, user_info):
    method_type = "INSERT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    if user_info["role"] in ["con", "ocon"]:
        return _error_response(method_type, ACCESS_DENIED_MESSAGE)
    if user_info["role"] not in ["ins", "sch"]:
        return func_helper.not_method_access_return()

    try:
        with session_scope() as session:
            if user_phone_exists(session=session, phone=request_data["phone"]):
                return _error_response(
                    method_type,
                    "شماره تلفن وارد شده در سامانه موجود می‌باشد لطفا شماره تلفن دیگری وارد نمایید.",
                )

            password = func_helper.random_generate_password()
            create_consultant_account(
                session=session,
                phone=request_data["phone"],
                encrypted_password=func_helper.encrypt_password(password),
                request_data=request_data,
                owner_user_id=user_info["user_id"],
            )

        return _service_response(
            method_type,
            func_helper.get_tracking_code(),
            None,
            "مشاور شما با موفقیت ثبت شد.",
        )
    except Exception as e:
        func_helper.service_exception_error_logging("ag_api/service", "add_consultant", str(e), request_data, user_info
        )
        return _error_response(
            method_type,
            "مشکلی در ثبت نهایی اطلاعات مشاور رخ داده است لطفا با پیشیبانی در ارتباط باشید.",
        )


# this gateway for update the consultant information from user role
def change_consultant(request_data, user_info):
    method_type = "UPDATE"
    result = _role_handler(user_info, {
        "ins": lambda: institute_service.change_consultant(request_data=request_data,
                                                           user_info=user_info),
        "sch": lambda: school_service.change_consultant(request_data=request_data,
                                                        user_info=user_info),
    })
    if result is None:
        return _error_response(method_type, ACCESS_DENIED_MESSAGE)

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


# this gateway for get list of student from user role
def get_students(request_data, user_info):
    method_type = "SELECT"
    result = _role_handler(user_info, {
        "ins": lambda: institute_service.get_students(request_data=request_data,
                                                      user_info=user_info),
        "sch": lambda: school_service.get_students(request_data=request_data,
                                                   user_info=user_info),
        "con": lambda: consultant_service.get_students(request_data=request_data, user_info=user_info),
        "ocon": lambda: owner_consultant_service.get_students(request_data=request_data,
                                                              user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)

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
        elif role in ["con", "ocon"]:
            return res["consultant_user_id"] == user_id
        
        return False
    except Exception:
        logger.exception("Error checking student access")
        return False


def get_report_data(request_data, user_info):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["student_id", "report_type"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response
    
    if user_info["role"] in ["ins", "sch", "con", "ocon"]:
        student_id = request_data.get("student_id")
        # Check if user has access to this student
        if not check_student_access(student_user_id=student_id, user_info=user_info):
            return _error_response(method_type, "شما به این دانش‌آموز دسترسی ندارید.")
        
        tracking_token, response_data, response_message = other_service.get_report_data(
            request_data=request_data,
            user_info=user_info,
        )
        return _service_response(
            method_type, tracking_token, response_data, response_message, error_message="خطا در دریافت اطلاعات گزارش."
        )
    else:
        return func_helper.not_method_access_return()

# this gateway for insert student for user role
def add_student(request_data, user_info):
    method_type = "INSERT"
    if user_info["role"] not in ["ins", "sch", "ocon"]:
        return _error_response(method_type, ACCESS_DENIED_MESSAGE)

    try:
        password = func_helper.random_generate_password()
        with session_scope() as session:
            phone = _generate_available_student_phone(session=session)
            create_student_account(
                session=session,
                phone=phone,
                encrypted_password=func_helper.encrypt_password(password),
                request_data=request_data,
                user_info=user_info,
            )

        return _service_response(
            method_type,
            func_helper.get_tracking_code(),
            None,
            "دانش‌آموز شما با موفقیت ثبت شد.",
        )
    except Exception as e:
        func_helper.service_exception_error_logging("ag_api/service", "add_student", str(e), request_data, user_info
        )
        return _error_response(method_type, "مشکلی در افزودن دانش‌آموز رخ داده است.")


# this gateway for update the student information from user role
def change_student(request_data, user_info):
    method_type = "UPDATE"
    required_fields = ["first_name", "last_name", "sex", "city", "birth_date", "student_id"]
    if user_info["role"] in ["ins", "sch"]:
        required_fields.append("con_id")
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=required_fields,
        method_type=method_type,
    )
    if not is_valid:
        return error_response
    result = _role_handler(user_info, {
        "ins": lambda: institute_service.change_student(request_data=request_data,
                                                        user_info=user_info),
        "sch": lambda: school_service.change_student(request_data=request_data,
                                                     user_info=user_info),
        "ocon": lambda: owner_consultant_service.change_student(request_data=request_data,
                                                                user_info=user_info),
        "con": lambda: consultant_service.change_student(request_data=request_data, user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


# this gateway is for make or update the comment of the student
def change_comment(request_data, user_info):
    method_type = "UPDATE"
    result = _role_handler(user_info, {
        "con": lambda: consultant_service.change_comment(request_data=request_data, user_info=user_info),
        "ocon": lambda: owner_consultant_service.change_comment(request_data=request_data,
                                                                user_info=user_info),
    })
    if result is None:
        return _error_response(method_type, "متاسفانه شما از این سامانه به این سرویس دسترسی ندارید.")

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


def get_quiz_setting(request_data, user_info):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["quiz_id"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    quiz_id = request_data["quiz_id"]
    with session_scope() as session:
        res = get_setting_for_user_quiz(
            session=session,
            user_id=int(user_info["user_id"]),
            quiz_id=int(quiz_id),
        )
    token = func_helper.get_tracking_code()
    if not res:
        quiz_info = quiz_data_extractor.get_quiz_info(quiz_id=quiz_id)
        info_data = {"voice": quiz_info["voice"], "description": quiz_info["description"], "setting_id": "no setting"}
        return _service_response(method_type, token, info_data)

    info_data = {"voice": res["voice"], "description": res["description"], "setting_id": res["setting_id"]}
    return _service_response(method_type, token, info_data)


def get_report(request_data, user_info):
    method_type = "SELECT"
    result = _role_handler(user_info, {
        "ins": lambda: institute_service.get_report(request_data=request_data,
                                                    user_info=user_info),
        "sch": lambda: school_service.get_report(request_data=request_data,
                                                 user_info=user_info),
        "ocon": lambda: owner_consultant_service.get_report(request_data=request_data,
                                                            user_info=user_info),
        "con": lambda: consultant_service.get_report(request_data=request_data, user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


def get_management_report(request_data, user_info):
    method_type = "SELECT"
    if user_info["role"] == "stu":
        return _error_response(method_type, "متاسفانه شما از این سامانه به این سرویس دسترسی ندارید.")

    result = _role_handler(user_info, {
        "ins": lambda: institute_service.get_management_report(request_data=request_data,
                                                               user_info=user_info),
        "sch": lambda: school_service.get_management_report(request_data=request_data,
                                                            user_info=user_info),
        "ocon": lambda: owner_consultant_service.get_management_report(request_data=request_data,
                                                                       user_info=user_info),
        "con": lambda: consultant_service.get_management_report(request_data=request_data, user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


# get the information of quiz (quiz id, quiz description, quiz voice, quiz sections, quiz name)
def get_quiz_info(request_data, user_info):
    method_type = "SELECT"
    if user_info["role"] not in ["ins", "sch", "ocon", "con"]:
        return _error_response(method_type, "متاسفانه شما از این سامانه به این سرویس دسترسی ندارید.")

    tracking_token = func_helper.get_tracking_code()
    response_data = quiz_data_extractor.get_quiz_table_info()
    return _service_response(method_type, tracking_token, response_data, "")


# transactions and payments
def get_transactions(request_data, user_info):
    method_type = "SELECT"
    if user_info["role"] in ["ocon", "ins", "sch"]:
        tracking_token, response_data, response_message = other_service.get_transactions(request_data, user_info)
        return _service_response(method_type, tracking_token, response_data, response_message)
    return func_helper.not_method_access_return()


def apply_discount(request_data, user_info):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["discount_code", "total_value"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    tracking_token, response_data, response_message = other_service.apply_discount(
        request_data=request_data,
        user_info=user_info,
    )
    return _service_response(method_type, tracking_token, response_data, response_message)

def add_payment_order(request_data, user_info):
    method_type = "INSERT"
    # is_valid, error_response = func_helper.validate_request_data_fields(
    #     request_data=request_data,
    #     required_fields=["price", "discount_code", "AG", "SCL"],
    #     method_type=method_type,
    # )
    # if not is_valid:
    #     return error_response
    if user_info["role"] in ["ocon", "ins", "sch"]:
        tracking_token, response_data, response_message = other_service.order_payment(
            request_data=request_data,
            user_info=user_info,
        )
        return _service_response(method_type, tracking_token, response_data, response_message)
    return _error_response(method_type, DEFAULT_SERVICE_ERROR)

def get_comments():
    method_type = "SELECT"
    tracking_token, response_data, response_message = other_service.get_comments()
    return _service_response(method_type, tracking_token, response_data, response_message)


def add_comment(request_data):
    method_type = "INSERT"
    tracking_token, response_data, response_message = other_service.add_comment(
        request_data=request_data
    )
    return _service_response(method_type, tracking_token, response_data, response_message)


def mark_notification_read(request_data, user_info):
    method_type = "INSERT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["notification_id"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    tracking_token, response_data, response_message = other_service.mark_notification_read(
        request_data=request_data,
        user_info=user_info,
    )
    return _service_response(method_type, tracking_token, response_data, response_message)
