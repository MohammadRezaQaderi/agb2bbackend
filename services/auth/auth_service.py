import json

from config import REDIS_CACHE_OTP
import helper.func_helper as func_helper
import helper.otp.otp_helper as otp_helper
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.auth import (
    create_token,
    create_user,
    delete_token_for_user,
    get_role_verify_status,
    get_token_for_user,
    get_user_auth_by_phone,
    get_user_identity_by_phone,
    token_exists,
    user_phone_exists,
)
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
                token = func_helper.get_tracking_code()
                if not token_exists(session=session, token=token):
                    return create_token(session=session, user_id=user_id, token=token)
    except Exception as e:
        func_helper.service_exception_error_logging(None, None, "ag_api/auth", "_create_token", str(e), user_info, {})
        return None


def remove_token(request_data, user_info):
    try:
        with session_scope() as session:
            deleted_count = delete_token_for_user(session=session, user_id=user_info["user_id"])
        if deleted_count == 0:
            return None, None, "توکن حذف نشد یا موجود نیست."
        return func_helper.get_tracking_code(), {}, "توکن حذف شد."
    except Exception as e:
        func_helper.service_exception_error_logging(None, None, "ag_api/auth", "remove_token", str(e), request_data, user_info)
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
        if func_helper.verify_password(plain_password=password, stored_password=db_password):
            user_info = [res["user_id"], phone, res["role"]]
            token_user = _create_token(user_info=user_info)
        else:
            return None, None, "رمز عبور شما درست نمی‌باشد."
        if res["role"] == "ins":
            with session_scope() as session:
                verify_status = get_role_verify_status(session=session, user_id=res["user_id"], role=res["role"])
            if verify_status != 1:
                remove_token(
                    request_data={"user_id": res["user_id"]},
                    user_info={"user_id": res["user_id"], "phone": phone},
                )
                return None, None, "شما هنوز احراز هویت انجام نداده‌اید."
            _, user_info, _ = institute_service.get_info(conn=None, cursor=None, user_id=res["user_id"])
        elif res["role"] == "sch":
            with session_scope() as session:
                verify_status = get_role_verify_status(session=session, user_id=res["user_id"], role=res["role"])
            if verify_status != 1:
                remove_token(
                    request_data={"user_id": res["user_id"]},
                    user_info={"user_id": res["user_id"], "phone": phone},
                )
                return None, None, "شما هنوز احراز هویت انجام نداده‌اید."
            _, user_info, _ = school_service.get_info(conn=None, cursor=None, user_id=res["user_id"])
        elif res["role"] == "ocon":
            with session_scope() as session:
                verify_status = get_role_verify_status(session=session, user_id=res["user_id"], role=res["role"])
            if verify_status != 1:
                remove_token(
                    request_data={"user_id": res["user_id"]},
                    user_info={"user_id": res["user_id"], "phone": phone},
                )
                return None, None, "شما هنوز احراز هویت انجام نداده‌اید."
            _, user_info, _ = owner_consultant_service.get_info(conn=None, cursor=None, user_id=res["user_id"])

        elif res["role"] == "con":
            _, user_info, _ = consultant_service.get_info(conn=None, cursor=None, user_id=res["user_id"])
        elif res["role"] == "stu":
            return None, None, "متاسفانه شما از این سامانه اجازه ورود ندارید."
        return token_user, user_info, ""
    except Exception as e:
        func_helper.service_exception_error_logging(None, None, "ag_api/auth", "sign_in", str(e), request_data, {})
        return None, None, "مشکلی در ورود شما رخ داده با پشتیبانی ارتباط بگیرید."


def sign_in_student(request_data):
    try:
        phone = request_data["phone"]
        password = request_data["password"]
        with session_scope() as session:
            res = get_user_auth_by_phone(session=session, phone=phone)
        if res is None:
            return None, None, " کاربری با این شماره تلفن موجود نمی‌باشد."

        if not func_helper.verify_password(plain_password=password, stored_password=res["password"]):
            return None, None, "رمز عبور شما درست نمی‌باشد."

        if res["role"] != "stu":
            return None, None, "متاسفانه شما از این سامانه اجازه ورود ندارید."

        token_user = _create_token(user_info=[res["user_id"], phone, res["role"]])
        _, user_info, _ = student_service.select_student_info(conn=None, cursor=None, user_id=res["user_id"])
        return token_user, user_info, ""
    except Exception as e:
        func_helper.service_exception_error_logging(None, None, "ags_api/auth", "sign_in_student", str(e), request_data, {})
        return None, None, "مشکلی در ورود شما رخ داده با پشتیبانی ارتباط بگیرید."


def sign_up(redis_db, request_data):
    try:
        phone = request_data["phone"]
        password = request_data["password"]
        re_password = request_data["re_password"]
        role = request_data["role"]

        if not func_helper.is_valid_mobile(phone=phone):
            return None, None, "شماره تلفن شما معتبر نیست."

        if password != re_password:
            return None, None, "رمز عبور و تکرار رمز عبور باهم تطابق ندارد."

        val, message = func_helper.password_format_check(password=password)
        if not val:
            return None, None, message

        with session_scope() as session:
            exists = user_phone_exists(session=session, phone=phone)
        if exists:
            return None, None, "این شماره تلفن موجود می‌باشد."

        with session_scope() as session:
            user_id = create_user(
                session=session,
                phone=phone,
                password=func_helper.encrypt_password(password),
                role=role,
            )
        if role == "ins":
            token, _, _ = institute_service.add_institute(conn=None, cursor=None, request_data=request_data,
                                                          user_id=user_id)

        elif role == "sch":
            token, _, _ = school_service.add_school(conn=None, cursor=None, request_data=request_data,
                                                    user_id=user_id)

        elif role == "ocon":
            token, _, _ = owner_consultant_service.add_owner_consultant(
                conn=None, cursor=None, request_data=request_data, user_id=user_id
            )

        else:
            token = None

        if token is None:
            return None, None, "مشکل در ثبت نام رخ داده با پشتیبانی در ارتباط باشید."

        cache = redis_db.cache(REDIS_CACHE_OTP)
        cache_record = cache.get(phone)
        if cache_record is not None:
            cache.delete(phone)
        code = func_helper.random_generate_otp_code(5)
        # todo here checkout the try/except handle for otp
        res_otp = otp_helper.send_otp_message(code=code, phone=phone, type="VERIFY")
        cache.set(phone, json.dumps({"code": code}), 60 * 60 * 24 * 100)

        return token, None, "ثبت نام شما با موفقیت انجام شد."

    except Exception as e:
        func_helper.service_exception_error_logging(None, None, "ag_api/auth", "sign_up", str(e), request_data, {})
        return None, None, "مشکلی در ثبت نام شما رخ داده با پشتیبانی ارتباط بگیرید."


def send_otp(redis_db, request_data):
    try:
        phone = request_data["phone"]
        type_otp = request_data["type"]

        if not func_helper.is_valid_mobile(phone=phone):
            return None, None, "شماره تلفن شما معتبر نیست."

        if not func_helper.check_security_code(code=request_data["code"], check=request_data["check"]):
            return None, None, "کد امنیتی وارد شده اشتباه است."

        with session_scope() as session:
            res = get_user_identity_by_phone(session=session, phone=phone)
        if res is None:
            return None, None, "کاربری با این شماره تلفن موجود نمی‌باشد."

        if res["role"] == "ins" and type_otp == "verify":
            with session_scope() as session:
                verify_status = get_role_verify_status(session=session, user_id=res["user_id"], role=res["role"])
            if verify_status == 1:
                return None, None, "شما از قبل احراز هویت نموده‌اید."

        if res["role"] == "sch" and type_otp == "verify":
            with session_scope() as session:
                verify_status = get_role_verify_status(session=session, user_id=res["user_id"], role=res["role"])
            if verify_status == 1:
                return None, None, "شما از قبل احراز هویت نموده‌اید."

        if res["role"] == "ocon" and type_otp == "verify":
            with session_scope() as session:
                verify_status = get_role_verify_status(session=session, user_id=res["user_id"], role=res["role"])
            if verify_status == 1:
                return None, None, "شما از قبل احراز هویت نموده‌اید."

        cache = redis_db.cache(REDIS_CACHE_OTP)
        cache_record = cache.get(phone)
        if cache_record is not None:
            cache.delete(phone)
        code = func_helper.random_generate_otp_code(5)
        res_otp = otp_helper.send_otp_message(code=code, phone=phone, type=type_otp.upper())
        cache.set(res["phone"], json.dumps({"code": code}), 60 * 60 * 24 * 100)
        token = func_helper.get_tracking_code()
        return token, {"phone": phone}, ""
    except Exception as e:
        func_helper.service_exception_error_logging(None, None, "ag_api/auth", "send_otp", str(e), request_data, {})
        return None, None, "مشکلی در احراز هویت شما رخ داده با پشتیبانی ارتباط بگیرید."


def check_otp(redis_db, request_data):
    try:
        phone = request_data["phone"]
        code = request_data["code"]
        type_otp = request_data["type"]

        with session_scope() as session:
            res = get_user_auth_by_phone(session=session, phone=phone)

        if res is None:
            return None, None, "کاربری با این شماره تلفن موجود نمی‌باشد."

        cache = redis_db.cache(REDIS_CACHE_OTP)
        cache_record = cache.get(phone)

        if cache_record is None:
            return None, None, "کدی برای این شماره تلفن در سامانه ثبت نشده. لطفا دوباره  درخواست دهید."

        record = json.loads(cache_record)

        if int(code) != record["code"]:
            return None, None, "کد وارد شده صحیح نمی‌باشد."

        user_info = [res["user_id"], phone, res["role"]]
        token_user = _create_token(user_info=user_info)

        if type_otp == "otp":

            if res["role"] == "ins":
                _, user_info, _ = institute_service.get_info(conn=None, cursor=None, user_id=res["user_id"])
            elif res["role"] == "sch":
                _, user_info, _ = school_service.get_info(conn=None, cursor=None, user_id=res["user_id"])
            elif res["role"] == "ocon":
                _, user_info, _ = owner_consultant_service.get_info(conn=None, cursor=None, user_id=res["user_id"])
            elif res["role"] == "con":
                _, user_info, _ = consultant_service.get_info(conn=None, cursor=None, user_id=res["user_id"])
            else:
                return None, None, "شما به این سرویس دسترسی ندارید."
            return token_user, user_info, ""

        else:
            if res["role"] == "ins":
                _, user_info, _ = institute_service.verify_user(conn=None, cursor=None, user_id=res["user_id"])
            elif res["role"] == "sch":
                _, user_info, _ = school_service.verify_user(conn=None, cursor=None, user_id=res["user_id"])
            elif res["role"] == "ocon":
                _, user_info, _ = owner_consultant_service.verify_user(conn=None, cursor=None, user_id=res["user_id"])
            else:
                return None, None, "شما به این سرویس دسترسی ندارید."
            return token_user, user_info, ""

    except Exception as e:
        func_helper.service_exception_error_logging(None, None, "ag_api/auth", "check_otp", str(e), request_data, {})
        return None, None, "مشکلی در احراز هویت شما رخ داده با پشتیبانی ارتباط بگیرید."
