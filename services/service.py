import helper.func_helper as func_helper
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.accounts import create_consultant_account, create_student_account
from helper.db.sqlalchemy.queries.auth import user_phone_exists
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
from services.other.other_gateway import (
    add_comment,
    add_payment_order,
    apply_discount,
    check_student_access,
    get_comments,
    get_report_data,
    get_transactions,
    mark_notification_read,
)
from services.quiz.quiz_gateway import get_quiz_info, get_quiz_setting, student_get_quiz_setting
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
    error_response as _error_response,
    service_response as _service_response,
)
from services.management_gateway import (
    change_comment,
    change_consultant,
    change_password,
    change_setting,
    change_student,
    change_student_access,
    change_user_info,
    change_user_quiz_setting,
    get_consultants,
    get_dashboard,
    get_management_report,
    get_report,
    get_students,
)


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
