import helper.func_helper as func_helper
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.accounts import create_consultant_account, create_student_account
from helper.db.sqlalchemy.queries.auth import user_phone_exists
from services.gateway_helpers import ACCESS_DENIED_MESSAGE, error_response, service_response


def _generate_available_student_phone(session, attempts=20):
    for _ in range(attempts):
        phone = func_helper.random_phone_candidate(8)
        if not user_phone_exists(session=session, phone=phone):
            return phone
    raise ValueError("Could not generate a unique student phone.")


def add_consultant(request_data, user_info):
    method_type = "INSERT"
    is_valid, validation_error = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone"],
        method_type=method_type,
    )
    if not is_valid:
        return validation_error

    if user_info["role"] in ["con", "ocon"]:
        return error_response(method_type, ACCESS_DENIED_MESSAGE)
    if user_info["role"] not in ["ins", "sch"]:
        return func_helper.not_method_access_return()

    try:
        with session_scope() as session:
            if user_phone_exists(session=session, phone=request_data["phone"]):
                return error_response(
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

        return service_response(
            method_type,
            func_helper.get_tracking_code(),
            None,
            "مشاور شما با موفقیت ثبت شد.",
        )
    except Exception as exc:
        func_helper.service_exception_error_logging(
            "ag_api/service",
            "add_consultant",
            str(exc),
            request_data,
            user_info,
        )
        return error_response(
            method_type,
            "مشکلی در ثبت نهایی اطلاعات مشاور رخ داده است لطفا با پیشیبانی در ارتباط باشید.",
        )


def add_student(request_data, user_info):
    method_type = "INSERT"
    if user_info["role"] not in ["ins", "sch", "ocon"]:
        return error_response(method_type, ACCESS_DENIED_MESSAGE)

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

        return service_response(
            method_type,
            func_helper.get_tracking_code(),
            None,
            "دانش‌آموز شما با موفقیت ثبت شد.",
        )
    except Exception as exc:
        func_helper.service_exception_error_logging(
            "ag_api/service",
            "add_student",
            str(exc),
            request_data,
            user_info,
        )
        return error_response(method_type, "مشکلی در افزودن دانش‌آموز رخ داده است.")
