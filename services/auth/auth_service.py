import json

from config import REDIS_CACHE_OTP
import helper.db.db_helper as db_helper
import helper.func_helper as func_helper
import helper.otp.otp_helper as otp_helper
import services.consultant.consultant_service as consultant_service
import services.institute.institute_service as institute_service
import services.owner_consultant.owner_consultant_service as owner_consultant_service
import services.school.school_service as school_service


def create_token(conn, cursor, info):
    try:
        query = "SELECT token FROM tokens WHERE user_id = ?"
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=info[0])
        if res is None:
            while True:
                token = func_helper.get_tracking_code()
                token_check_query = "SELECT token FROM tokens WHERE token = ?"
                token_exists = db_helper.search_table(conn=conn, cursor=cursor, query=token_check_query, field=token)
                if not token_exists:
                    field = '([token], [user_id], [phone], [role])'
                    values = (token, info[0], info[1], info[2])
                    db_helper.insert_value(conn=conn, cursor=cursor, table_name="tokens", fields=field, values=values)
                    return token
        else:
            return res[0]
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/auth", "create_token", str(e), info, {})
        return None


def token_remove(conn, cursor, request_data, info):
    try:
        res = db_helper.delete_record(
            conn, cursor, "tokens",
            ["user_id"],
            [info["user_id"]]
        )
        return res
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/auth", "token_remove", str(e), request_data, info)
        return None


def check_signin(conn, cursor, request_data):
    try:
        phone = request_data["phone"]
        password = request_data["password"]
        query = 'SELECT user_id, password, role FROM users WHERE phone = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)
        if res is None:
            return None, " کاربری با این شماره تلفن موجود نمی‌باشد.", None
        db_password = res.password
        if func_helper.verify_password(plain_password=password, stored_password=db_password):
            info = [res.user_id, phone, res.role]
            token_user = create_token(conn=conn, cursor=cursor, info=info)
        else:
            return None, "رمز عبور شما درست نمی‌باشد.", None
        if res.role == "ins":
            query = 'SELECT verify FROM ins WHERE phone = ?'
            res_verify = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)
            if res_verify.verify == 0:
                token_remove(conn=conn, cursor=cursor, request_data={"user_id": res.user_id},
                             info={"user_id": res.user_id, "phone": phone})
                return None, "شما هنوز احراز هویت انجام نداده‌اید.", None
            ـ, info = institute_service.select_institute_info(conn=conn, cursor=cursor, user_id=res.user_id)
        elif res.role == "sch":
            query = 'SELECT verify FROM sch WHERE phone = ?'
            res_verify = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)
            if res_verify.verify == 0:
                token_remove(conn=conn, cursor=cursor, request_data={"user_id": res.user_id},
                             info={"user_id": res.user_id, "phone": phone})
                return None, "شما هنوز احراز هویت انجام نداده‌اید.", None
            ـ, info = school_service.select_school_info(conn=conn, cursor=cursor, user_id=res.user_id)
        elif res.role == "wCon":
            query = 'SELECT verify FROM wCon WHERE phone = ?'
            res_verify = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)
            if res_verify.verify == 0:
                token_remove(conn=conn, cursor=cursor, request_data={"user_id": res.user_id},
                             info={"user_id": res.user_id, "phone": phone})
                return None, "شما هنوز احراز هویت انجام نداده‌اید.", None
            ـ, info = owner_consultant_service.select_wcon_info(conn=conn, cursor=cursor, user_id=res.user_id)

        elif res.role == "con":
            ـ, info = consultant_service.select_consultant_info(conn=conn, cursor=cursor, user_id=res.user_id)
        elif res.role == "stu":
            return None, "متاسفانه شما از این سامانه اجازه ورود ندارید.", None
        return token_user, "", info
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/auth", "check_signin", str(e), request_data, {})
        return None, "مشکلی در ورود شما رخ داده با پشتیبانی ارتباط بگیرید.", None


def check_signup(conn, cursor, redis_db, request_data):
    try:
        phone = request_data["phone"]
        password = request_data["password"]
        re_password = request_data["re_password"]
        role = request_data["role"]

        if not func_helper.is_valid_mobile(phone=phone):
            return None, None, "شماره تلفن شما معتبر نیست."

        if password != re_password:
            return None, "رمز عبور و تکرار رمز عبور باهم تطابق ندارد."

        val, message = func_helper.password_format_check(password=password)
        if val is None:
            return None, message

        query = 'SELECT user_id FROM users WHERE phone = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)
        if res is not None:
            return None, "این شماره تلفن موجود می‌باشد."

        field = '([phone], [password], [role])'
        values = (phone, func_helper.encrypt_password(password), role,)
        db_helper.insert_value(conn=conn, cursor=cursor, table_name="users", fields=field,
                               values=values)

        query = 'SELECT user_id FROM users WHERE phone = ?'
        res_user = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)
        if role == "ins":
            token = institute_service.insert_institute(conn=conn, cursor=cursor, request_data=request_data, user_id=res_user.user_id)

        elif role == "sch":
            token = school_service.insert_school(conn=conn, cursor=cursor, request_data=request_data, user_id=res_user.user_id)

        elif role == "wCon":
            token = owner_consultant_service.insert_owner_consultant(conn=conn, cursor=cursor, request_data=request_data,
                                            user_id=res_user.user_id)

        else:
            token = None

        if token is None:
            conn.rollback()
            return None, "مشکل در ثبت نام رخ داده با پشتیبانی در ارتباط باشید."

        cache = redis_db.cache(REDIS_CACHE_OTP)
        cache_record = cache.get(phone)
        if cache_record is not None:
            cache.delete(phone)
        code = func_helper.random_generate_otp_code(5)
        # todo here checkout the try/except handle for otp
        res_otp = otp_helper.send_otp_message(conn=conn, cursor=cursor, code=code, phone=phone, type="VERIFY")
        cache.set(phone, json.dumps({"code": code}), 60 * 60 * 24 * 100)

        return token, "ثبت نام شما با موفقیت انجام شد."

    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/auth", "check_signup", str(e), request_data, {})
        return None, "مشکلی در ثبت نام شما رخ داده با پشتیبانی ارتباط بگیرید."


def check_send_sms(conn, cursor, redis_db, request_data):
    try:
        phone = request_data["phone"]
        type_otp = request_data["type"]

        if not func_helper.is_valid_mobile(phone=phone):
            return None, "شماره تلفن شما معتبر نیست.", None

        if not func_helper.check_security_code(code=request_data["code"], check=request_data["check"]):
            return None, "کد امنیتی وارد شده اشتباه است.", None

        query = 'SELECT phone, role FROM users WHERE phone = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)
        if res is None:
            return None, "کاربری با این شماره تلفن موجود نمی‌باشد.", None

        if res.role == "ins" and type_otp == "verify":
            query = 'SELECT verify FROM ins WHERE phone = ?'
            res_verify = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)
            if res_verify.verify == 1:
                return None, "شما از قبل احراز هویت نموده‌اید.", None

        if res.role == "sch" and type_otp == "verify":
            query = 'SELECT verify FROM sch WHERE phone = ?'
            res_verify = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)
            if res_verify.verify == 1:
                return None, "شما از قبل احراز هویت نموده‌اید.", None

        if res.role == "wCon" and type_otp == "verify":
            query = 'SELECT verify FROM wCon WHERE phone = ?'
            res_verify = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)
            if res_verify.verify == 1:
                return None, "شما از قبل احراز هویت نموده‌اید.", None

        cache = redis_db.cache(REDIS_CACHE_OTP)
        cache_record = cache.get(phone)
        if cache_record is not None:
            cache.delete(phone)
        code = func_helper.random_generate_otp_code(5)
        res_otp = otp_helper.send_otp_message(conn=conn, cursor=cursor, code=code, phone=phone, type=type_otp.upper())
        cache.set(res.phone, json.dumps({"code": code}), 60 * 60 * 24 * 100)
        token = func_helper.get_tracking_code()
        return token, "", phone
    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/auth", "check_send_sms", str(e), request_data, {})
        return None, "مشکلی در احراز هویت شما رخ داده با پشتیبانی ارتباط بگیرید.", None


def check_sms_verify(conn, cursor, redis_db, request_data):
    try:
        phone = request_data["phone"]
        code = request_data["code"]
        type_otp = request_data["type"]

        query = 'SELECT user_id, password, role FROM users WHERE phone = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)

        if res is None:
            return None, "کاربری با این شماره تلفن موجود نمی‌باشد.", None

        cache = redis_db.cache(REDIS_CACHE_OTP)
        cache_record = cache.get(phone)

        if cache_record is None:
            return None, "کدی برای این شماره تلفن در سامانه ثبت نشده. لطفا دوباره  درخواست دهید.", None

        record = json.loads(cache_record)

        if int(code) != record["code"]:
            return None, "کد وارد شده صحیح نمی‌باشد.", None

        info = [res.user_id, phone, res.role]
        token_user = create_token(conn=conn, cursor=cursor, info=info)

        if type_otp == "otp":

            if res.role == "ins":
                ـ, info = institute_service.select_institute_info(conn=conn, cursor=cursor, user_id=res.user_id)
            elif res.role == "sch":
                ـ, info = school_service.select_school_info(conn=conn, cursor=cursor, user_id=res.user_id)
            elif res.role == "wCon":
                ـ, info = owner_consultant_service.select_wcon_info(conn=conn, cursor=cursor, user_id=res.user_id)
            elif res.role == "con":
                ـ, info = consultant_service.select_consultant_info(conn=conn, cursor=cursor, user_id=res.user_id)
            else:
                return None, "شما به این سرویس دسترسی ندارید.", None
            return token_user, "", info

        else:
            if res.role == "ins":
                ـ, info = institute_service.update_ins_verify(conn=conn, cursor=cursor, user_id=res.user_id)
            elif res.role == "sch":
                ـ, info = school_service.update_sch_verify(conn=conn, cursor=cursor, user_id=res.user_id)
            elif res.role == "wCon":
                ـ, info = owner_consultant_service.update_wcon_verify(conn=conn, cursor=cursor, user_id=res.user_id)
            else:
                return None, "شما به این سرویس دسترسی ندارید.", None
            return token_user, "", info

    except Exception as e:
        conn.rollback()
        func_helper.service_exception_error_logging(conn, cursor, "ag_api/auth", "check_sms_verify", str(e), request_data, {})
        return None, "مشکلی در احراز هویت شما رخ داده با پشتیبانی ارتباط بگیرید.", None
