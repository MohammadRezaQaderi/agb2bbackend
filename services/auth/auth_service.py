from helper.constants import PACKAGES_DATA
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.accounts import create_signup_account
from helper.db.sqlalchemy.queries.auth import (
    create_token,
    delete_token_for_user,
    get_role_verify_status,
    get_token_for_user,
    get_user_auth_by_phone,
    get_user_identity_by_phone,
    token_exists,
    user_phone_exists,
)
from helper.otp.otp_gateway import OtpGateway
from helper.password_helper import encrypt_password, verify_password
from helper.service_errors import service_exception_error_logging
from helper.tracking import get_tracking_code
from helper.validators import check_security_code, is_valid_mobile, password_format_check
import services.consultant.consultant_service as consultant_service
import services.institute.institute_service as institute_service
import services.owner_consultant.owner_consultant_service as owner_consultant_service
import services.school.school_service as school_service
import services.student.student_service as student_service


def _create_token(user_info):
    try:
        user_id = user_info[0]
        with session_scope() as session:
            existing_token = get_token_for_user(session=session, user_id=user_id)
            if existing_token:
                return existing_token

            while True:
                token = get_tracking_code()
                if not token_exists(session=session, token=token):
                    return create_token(session=session, user_id=user_id, token=token)
    except Exception as e:
        service_exception_error_logging("ag_api/auth", "_create_token", str(e), user_info, {})
        return None


def sign_out(request_data, user_info):
    try:
        with session_scope() as session:
            deleted_count = delete_token_for_user(session=session, user_id=user_info["user_id"])
        if deleted_count == 0:
            return None, None, "توکن حذف نشد یا موجود نیست."
        return get_tracking_code(), {}, "توکن حذف شد."
    except Exception as e:
        service_exception_error_logging("ag_api/auth", "sign_out", str(e), request_data, user_info)
        return None, None, "مشکل در اتمام نشست"


def sign_in(request_data):
    try:
        phone = request_data["phone"]
        password = request_data["password"]
        with session_scope() as session:
            res = get_user_auth_by_phone(session=session, phone=phone)
        if res is None:
            return None, None, " کاربری با این شماره تلفن موجود نمی‌باشد."
        db_password = res["password"]
        if verify_password(plain_password=password, stored_password=db_password):
            user_info = [res["user_id"], phone, res["role"]]
            token_user = _create_token(user_info=user_info)
        else:
            return None, None, "رمز عبور شما درست نمی‌باشد."
        if res["role"] == "ins":
            with session_scope() as session:
                verify_status = get_role_verify_status(session=session, user_id=res["user_id"], role=res["role"])
            if verify_status != 1:
                sign_out(
                    request_data={"user_id": res["user_id"]},
                    user_info={"user_id": res["user_id"], "phone": phone},
                )
                return None, None, "شما هنوز احراز هویت انجام نداده‌اید."
            _, user_info, _ = institute_service.get_info(user_id=res["user_id"])
        elif res["role"] == "sch":
            with session_scope() as session:
                verify_status = get_role_verify_status(session=session, user_id=res["user_id"], role=res["role"])
            if verify_status != 1:
                sign_out(
                    request_data={"user_id": res["user_id"]},
                    user_info={"user_id": res["user_id"], "phone": phone},
                )
                return None, None, "شما هنوز احراز هویت انجام نداده‌اید."
            _, user_info, _ = school_service.get_info(user_id=res["user_id"])
        elif res["role"] == "ocon":
            with session_scope() as session:
                verify_status = get_role_verify_status(session=session, user_id=res["user_id"], role=res["role"])
            if verify_status != 1:
                sign_out(
                    request_data={"user_id": res["user_id"]},
                    user_info={"user_id": res["user_id"], "phone": phone},
                )
                return None, None, "شما هنوز احراز هویت انجام نداده‌اید."
            _, user_info, _ = owner_consultant_service.get_info(user_id=res["user_id"])

        elif res["role"] == "con":
            _, user_info, _ = consultant_service.get_info(user_id=res["user_id"])
        elif res["role"] == "stu":
            return None, None, "متاسفانه شما از این سامانه اجازه ورود ندارید."
        return token_user, user_info, ""
    except Exception as e:
        service_exception_error_logging("ag_api/auth", "sign_in", str(e), request_data, {})
        return None, None, "مشکلی در ورود شما رخ داده با پشتیبانی ارتباط بگیرید."


def sign_in_student(request_data):
    try:
        phone = request_data["phone"]
        password = request_data["password"]
        with session_scope() as session:
            res = get_user_auth_by_phone(session=session, phone=phone)
        if res is None:
            return None, None, " کاربری با این شماره تلفن موجود نمی‌باشد."

        if not verify_password(plain_password=password, stored_password=res["password"]):
            return None, None, "رمز عبور شما درست نمی‌باشد."

        if res["role"] != "stu":
            return None, None, "متاسفانه شما از این سامانه اجازه ورود ندارید."

        token_user = _create_token(user_info=[res["user_id"], phone, res["role"]])
        _, user_info, _ = student_service.select_student_info(user_id=res["user_id"])
        return token_user, user_info, ""
    except Exception as e:
        service_exception_error_logging("ags_api/auth", "sign_in_student", str(e), request_data, {})
        return None, None, "مشکلی در ورود شما رخ داده با پشتیبانی ارتباط بگیرید."


def sign_up(redis_db, request_data):
    try:
        phone = request_data["phone"]
        password = request_data["password"]
        re_password = request_data["re_password"]
        role = request_data["role"]

        if not is_valid_mobile(phone=phone):
            return None, None, "شماره تلفن شما معتبر نیست."

        if password != re_password:
            return None, None, "رمز عبور و تکرار رمز عبور باهم تطابق ندارد."

        val, message = password_format_check(password=password)
        if not val:
            return None, None, message

        with session_scope() as session:
            exists = user_phone_exists(session=session, phone=phone)
        if exists:
            return None, None, "این شماره تلفن موجود می‌باشد."

        if role not in {"ins", "sch", "ocon"}:
            return None, None, "نقش کاربری معتبر نیست."

        with session_scope() as session:
            create_signup_account(
                session=session,
                phone=phone,
                encrypted_password=encrypt_password(password),
                role=role,
                request_data=request_data,
                package_names=list(PACKAGES_DATA.keys()),
            )

        if not OtpGateway(redis_db).issue(phone, "verify"):
            return None, None, "حساب ثبت شد اما پیامک ارسال نشد؛ از بخش ارسال مجدد کد استفاده کنید."

        return get_tracking_code(), None, "ثبت نام شما با موفقیت انجام شد."

    except Exception as e:
        service_exception_error_logging("ag_api/auth", "sign_up", str(e), request_data, {})
        return None, None, "مشکلی در ثبت نام شما رخ داده با پشتیبانی ارتباط بگیرید."


def send_otp(redis_db, request_data):
    try:
        phone = request_data["phone"]
        type_otp = request_data["type"]

        if not is_valid_mobile(phone=phone):
            return None, None, "شماره تلفن شما معتبر نیست."

        if not check_security_code(code=request_data["code"], check=request_data["check"]):
            return None, None, "کد امنیتی وارد شده اشتباه است."

        if type_otp not in {"otp", "verify"}:
            return None, None, "نوع کد معتبر نیست."

        with session_scope() as session:
            res = get_user_identity_by_phone(session=session, phone=phone)
        if res is None:
            return None, None, "کاربری با این شماره تلفن موجود نمی‌باشد."

        if type_otp == "verify" and res["role"] not in {"ins", "sch", "ocon"}:
            return None, None, "شما به این سرویس دسترسی ندارید."
        if type_otp == "otp" and res["role"] not in {"ins", "sch", "ocon", "con"}:
            return None, None, "شما به این سرویس دسترسی ندارید."

        if type_otp == "verify":
            with session_scope() as session:
                verify_status = get_role_verify_status(session=session, user_id=res["user_id"], role=res["role"])
            if verify_status == 1:
                return None, None, "شما از قبل احراز هویت نموده‌اید."
        if not OtpGateway(redis_db).issue(res["phone"], type_otp):
            return None, None, "پیامک ارسال نشد؛ لطفا دوباره تلاش کنید."
        token = get_tracking_code()
        return token, {"phone": phone}, ""
    except Exception as e:
        service_exception_error_logging("ag_api/auth", "send_otp", str(e), request_data, {})
        return None, None, "مشکلی در احراز هویت شما رخ داده با پشتیبانی ارتباط بگیرید."


def check_otp(redis_db, request_data):
    try:
        phone = request_data["phone"]
        code = request_data["code"]
        type_otp = request_data["type"]

        if type_otp not in {"otp", "verify"}:
            return None, None, "نوع کد معتبر نیست."

        with session_scope() as session:
            res = get_user_auth_by_phone(session=session, phone=phone)

        if res is None:
            return None, None, "کاربری با این شماره تلفن موجود نمی‌باشد."

        if type_otp == "otp" and res["role"] not in {"ins", "sch", "ocon", "con"}:
            return None, None, "شما به این سرویس دسترسی ندارید."
        if type_otp == "verify" and res["role"] not in {"ins", "sch", "ocon"}:
            return None, None, "شما به این سرویس دسترسی ندارید."

        result = OtpGateway(redis_db).consume(phone, code, type_otp)
        if result == "missing":
            return None, None, "کدی برای این شماره تلفن ثبت نشده یا منقضی شده است. لطفا دوباره درخواست دهید."
        if result == "invalid":
            return None, None, "کد وارد شده صحیح نمی‌باشد."

        if type_otp == "otp":

            if res["role"] == "ins":
                _, user_info, _ = institute_service.get_info(user_id=res["user_id"])
            elif res["role"] == "sch":
                _, user_info, _ = school_service.get_info(user_id=res["user_id"])
            elif res["role"] == "ocon":
                _, user_info, _ = owner_consultant_service.get_info(user_id=res["user_id"])
            elif res["role"] == "con":
                _, user_info, _ = consultant_service.get_info(user_id=res["user_id"])
        elif type_otp == "verify":
            if res["role"] == "ins":
                _, user_info, _ = institute_service.verify_user(user_id=res["user_id"])
            elif res["role"] == "sch":
                _, user_info, _ = school_service.verify_user(user_id=res["user_id"])
            elif res["role"] == "ocon":
                _, user_info, _ = owner_consultant_service.verify_user(user_id=res["user_id"])

        if user_info is None:
            return None, None, "اطلاعات کاربر یافت نشد. لطفا دوباره درخواست دهید."
        token_user = _create_token(user_info=[res["user_id"], phone, res["role"]])
        if token_user is None:
            return None, None, "مشکلی در ورود شما رخ داده؛ لطفا دوباره درخواست دهید."
        return token_user, user_info, ""

    except Exception as e:
        service_exception_error_logging("ag_api/auth", "check_otp", str(e), request_data, {})
        return None, None, "مشکلی در احراز هویت شما رخ داده با پشتیبانی ارتباط بگیرید."
