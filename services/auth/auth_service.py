import json

from config import REDIS_CACHE_OTP
import helper.db.db_helper as db_helper
import helper.func_helper as func_helper
import helper.otp.otp_helper as otp_helper
import services.consultant.consultant_service as consultant_service
import services.institute.institute_service as institute_service
import services.owner_consultant.owner_consultant_service as owner_consultant_service
import services.school.school_service as school_service
import services.student.student_service as student_service


def _create_token(conn, cursor, user_info):
    try:
        query = "SELECT token FROM tokens WHERE user_id = ?"
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=user_info[0])
        if res is None:
            while True:
                token = func_helper.get_tracking_code()
                token_check_query = "SELECT token FROM tokens WHERE token = ?"
                token_exists = db_helper.search_table(conn=conn, cursor=cursor, query=token_check_query, field=token)
                if not token_exists:
                    field = '([token], [user_id], [role])'
                    values = (token, user_info[0], user_info[2])
                    db_helper.insert_value(conn=conn, cursor=cursor, table_name="tokens", fields=field, values=values)
                    return token
        else:
            return res[0]
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/auth", "_create_token", str(e), user_info, {})
        return None


def remove_token(conn, cursor, request_data, user_info):
    try:
        res = db_helper.delete_record(
            conn, cursor, "tokens",
            ["user_id"],
            [user_info["user_id"]]
        )
        if not res or (res.get("rowcount") is not None and res.get("rowcount") == 0):
            return None, None, "توکن حذف نشد یا موجود نیست."
        return func_helper.get_tracking_code(), {}, "توکن حذف شد."
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/auth", "remove_token", str(e), request_data, user_info)
        return None, None, "مشکل در اتمام نشست"


def sign_in(conn, cursor, request_data):
    try:
        phone = request_data["phone"]
        password = request_data["password"]
        query = 'SELECT user_id, password, role FROM users WHERE phone = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)
        if res is None:
            return None, None, " کاربری با این شماره تلفن موجود نمی‌باشد."
        db_password = res.password
        if func_helper.verify_password(plain_password=password, stored_password=db_password):
            user_info = [res.user_id, phone, res.role]
            token_user = _create_token(conn=conn, cursor=cursor, user_info=user_info)
        else:
            return None, None, "رمز عبور شما درست نمی‌باشد."
        if res.role == "ins":
            query = 'SELECT verify FROM ins WHERE user_id = ?'
            res_verify = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=res.user_id)
            if res_verify.verify == 0:
                remove_token(conn=conn, cursor=cursor, request_data={"user_id": res.user_id},
                             user_info={"user_id": res.user_id, "phone": phone})
                return None, None, "شما هنوز احراز هویت انجام نداده‌اید."
            _, user_info, _ = institute_service.get_info(conn=conn, cursor=cursor, user_id=res.user_id)
        elif res.role == "sch":
            query = 'SELECT verify FROM sch WHERE user_id = ?'
            res_verify = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=res.user_id)
            if res_verify.verify == 0:
                remove_token(conn=conn, cursor=cursor, request_data={"user_id": res.user_id},
                             user_info={"user_id": res.user_id, "phone": phone})
                return None, None, "شما هنوز احراز هویت انجام نداده‌اید."
            _, user_info, _ = school_service.get_info(conn=conn, cursor=cursor, user_id=res.user_id)
        elif res.role == "ocon":
            query = 'SELECT verify FROM ocon WHERE user_id = ?'
            res_verify = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=res.user_id)
            if res_verify.verify == 0:
                remove_token(conn=conn, cursor=cursor, request_data={"user_id": res.user_id},
                             user_info={"user_id": res.user_id, "phone": phone})
                return None, None, "شما هنوز احراز هویت انجام نداده‌اید."
            _, user_info, _ = owner_consultant_service.get_info(conn=conn, cursor=cursor, user_id=res.user_id)

        elif res.role == "con":
            _, user_info, _ = consultant_service.get_info(conn=conn, cursor=cursor, user_id=res.user_id)
        elif res.role == "stu":
            return None, None, "متاسفانه شما از این سامانه اجازه ورود ندارید."
        return token_user, user_info, ""
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/auth", "sign_in", str(e), request_data, {})
        return None, None, "مشکلی در ورود شما رخ داده با پشتیبانی ارتباط بگیرید."


def sign_in_student(conn, cursor, request_data):
    try:
        phone = request_data["phone"]
        password = request_data["password"]
        query = 'SELECT user_id, password, role FROM users WHERE phone = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)
        if res is None:
            return None, None, " کاربری با این شماره تلفن موجود نمی‌باشد."

        if not func_helper.verify_password(plain_password=password, stored_password=res.password):
            return None, None, "رمز عبور شما درست نمی‌باشد."

        if res.role != "stu":
            return None, None, "متاسفانه شما از این سامانه اجازه ورود ندارید."

        token_user = _create_token(conn=conn, cursor=cursor, user_info=[res.user_id, phone, res.role])
        _, user_info, _ = student_service.select_student_info(conn=conn, cursor=cursor, user_id=res.user_id)
        return token_user, user_info, ""
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ags_api/auth", "sign_in_student", str(e), request_data, {})
        return None, None, "مشکلی در ورود شما رخ داده با پشتیبانی ارتباط بگیرید."


def sign_up(conn, cursor, redis_db, request_data):
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
        if val is None:
            return None, None, message

        query = 'SELECT user_id FROM users WHERE phone = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)
        if res is not None:
            return None, None, "این شماره تلفن موجود می‌باشد."

        field = '([phone], [password], [role])'
        values = (phone, func_helper.encrypt_password(password), role,)
        db_helper.insert_value(conn=conn, cursor=cursor, table_name="users", fields=field,
                               values=values)

        query = 'SELECT user_id FROM users WHERE phone = ?'
        res_user = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)
        if role == "ins":
            token, _, _ = institute_service.add_institute(conn=conn, cursor=cursor, request_data=request_data,
                                                          user_id=res_user.user_id)

        elif role == "sch":
            token, _, _ = school_service.add_school(conn=conn, cursor=cursor, request_data=request_data,
                                                    user_id=res_user.user_id)

        elif role == "ocon":
            token, _, _ = owner_consultant_service.add_owner_consultant(
                conn=conn, cursor=cursor, request_data=request_data, user_id=res_user.user_id
            )

        else:
            token = None

        if token is None:
            conn.rollback()
            return None, None, "مشکل در ثبت نام رخ داده با پشتیبانی در ارتباط باشید."

        cache = redis_db.cache(REDIS_CACHE_OTP)
        cache_record = cache.get(phone)
        if cache_record is not None:
            cache.delete(phone)
        code = func_helper.random_generate_otp_code(5)
        # todo here checkout the try/except handle for otp
        res_otp = otp_helper.send_otp_message(conn=conn, cursor=cursor, code=code, phone=phone, type="VERIFY")
        cache.set(phone, json.dumps({"code": code}), 60 * 60 * 24 * 100)

        return token, None, "ثبت نام شما با موفقیت انجام شد."

    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/auth", "sign_up", str(e), request_data, {})
        return None, None, "مشکلی در ثبت نام شما رخ داده با پشتیبانی ارتباط بگیرید."


def send_otp(conn, cursor, redis_db, request_data):
    try:
        phone = request_data["phone"]
        type_otp = request_data["type"]

        if not func_helper.is_valid_mobile(phone=phone):
            return None, None, "شماره تلفن شما معتبر نیست."

        if not func_helper.check_security_code(code=request_data["code"], check=request_data["check"]):
            return None, None, "کد امنیتی وارد شده اشتباه است."

        query = 'SELECT user_id, phone, role FROM users WHERE phone = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)
        if res is None:
            return None, None, "کاربری با این شماره تلفن موجود نمی‌باشد."

        if res.role == "ins" and type_otp == "verify":
            query = 'SELECT verify FROM ins WHERE user_id = ?'
            res_verify = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=res.user_id)
            if res_verify.verify == 1:
                return None, None, "شما از قبل احراز هویت نموده‌اید."

        if res.role == "sch" and type_otp == "verify":
            query = 'SELECT verify FROM sch WHERE user_id = ?'
            res_verify = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=res.user_id)
            if res_verify.verify == 1:
                return None, None, "شما از قبل احراز هویت نموده‌اید."

        if res.role == "ocon" and type_otp == "verify":
            query = 'SELECT verify FROM ocon WHERE user_id = ?'
            res_verify = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=res.user_id)
            if res_verify.verify == 1:
                return None, None, "شما از قبل احراز هویت نموده‌اید."

        cache = redis_db.cache(REDIS_CACHE_OTP)
        cache_record = cache.get(phone)
        if cache_record is not None:
            cache.delete(phone)
        code = func_helper.random_generate_otp_code(5)
        res_otp = otp_helper.send_otp_message(conn=conn, cursor=cursor, code=code, phone=phone, type=type_otp.upper())
        cache.set(res.phone, json.dumps({"code": code}), 60 * 60 * 24 * 100)
        token = func_helper.get_tracking_code()
        return token, {"phone": phone}, ""
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/auth", "send_otp", str(e), request_data, {})
        return None, None, "مشکلی در احراز هویت شما رخ داده با پشتیبانی ارتباط بگیرید."


def check_otp(conn, cursor, redis_db, request_data):
    try:
        phone = request_data["phone"]
        code = request_data["code"]
        type_otp = request_data["type"]

        query = 'SELECT user_id, password, role FROM users WHERE phone = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)

        if res is None:
            return None, None, "کاربری با این شماره تلفن موجود نمی‌باشد."

        cache = redis_db.cache(REDIS_CACHE_OTP)
        cache_record = cache.get(phone)

        if cache_record is None:
            return None, None, "کدی برای این شماره تلفن در سامانه ثبت نشده. لطفا دوباره  درخواست دهید."

        record = json.loads(cache_record)

        if int(code) != record["code"]:
            return None, None, "کد وارد شده صحیح نمی‌باشد."

        user_info = [res.user_id, phone, res.role]
        token_user = _create_token(conn=conn, cursor=cursor, user_info=user_info)

        if type_otp == "otp":

            if res.role == "ins":
                _, user_info, _ = institute_service.get_info(conn=conn, cursor=cursor, user_id=res.user_id)
            elif res.role == "sch":
                _, user_info, _ = school_service.get_info(conn=conn, cursor=cursor, user_id=res.user_id)
            elif res.role == "ocon":
                _, user_info, _ = owner_consultant_service.get_info(conn=conn, cursor=cursor, user_id=res.user_id)
            elif res.role == "con":
                _, user_info, _ = consultant_service.get_info(conn=conn, cursor=cursor, user_id=res.user_id)
            else:
                return None, None, "شما به این سرویس دسترسی ندارید."
            return token_user, user_info, ""

        else:
            if res.role == "ins":
                _, user_info, _ = institute_service.verify_user(conn=conn, cursor=cursor, user_id=res.user_id)
            elif res.role == "sch":
                _, user_info, _ = school_service.verify_user(conn=conn, cursor=cursor, user_id=res.user_id)
            elif res.role == "ocon":
                _, user_info, _ = owner_consultant_service.verify_user(conn=conn, cursor=cursor, user_id=res.user_id)
            else:
                return None, None, "شما به این سرویس دسترسی ندارید."
            return token_user, user_info, ""

    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/auth", "check_otp", str(e), request_data, {})
        return None, None, "مشکلی در احراز هویت شما رخ داده با پشتیبانی ارتباط بگیرید."
