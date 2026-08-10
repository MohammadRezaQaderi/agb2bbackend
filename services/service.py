from datetime import datetime

import helper.db.db_helper as db_helper
import helper.func_helper as func_helper
import helper.quiz.quiz_data_extractor as quiz_data_extractor
import services.admin.admin_service as admin_service
import services.auth.auth_service as auth_service
import services.consultant.consultant_service as consultant_service
import services.institute.institute_service as institute_service
import services.other.other_service as other_service
import services.owner_consultant.owner_consultant_service as owner_consultant_service
import services.school.school_service as school_service


def delete_token(conn, cursor, request_data, info):
    method_type = "DELETE"
    token = func_helper.get_tracking_code()
    res = auth_service.token_remove(conn=conn, cursor=cursor, request_data=request_data, info=info)
    if res == 0:
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": "نشد"}}
    return {"status": 200, "tracking_code": token, "method_type": method_type,
            "response": {"message": "شد"}}


def signin(conn, cursor, request_data):
    method_type = "SIGNIN"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone", "password"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    tracking_code, message, response_info = auth_service.check_signin(conn=conn, cursor=cursor, request_data=request_data)
    if response_info is None:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": message}
    elif tracking_code:
        return {"status": 200, "tracking_code": tracking_code, "method_type": method_type,
                "response": response_info}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."}


def signup(conn, cursor, redis_db, request_data):
    method_type = "INSERT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone", "password", "re_password", "role"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    token, message = auth_service.check_signup(conn=conn, cursor=cursor, redis_db=redis_db, request_data=request_data)
    if token is None:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": message}
    elif token:
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": message}}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."}


def send_otp(conn, cursor, redis_db, request_data):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone", "type", "code", "check"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    token, message, phone = auth_service.check_send_sms(conn=conn, cursor=cursor, redis_db=redis_db, request_data=request_data)
    if token is None:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": message}
    else:
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"phone": phone}}


def check_otp(conn, cursor, redis_db, request_data):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone", "code", "type"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    tracking_code, message, info = auth_service.check_sms_verify(conn=conn, cursor=cursor, redis_db=redis_db,
                                                    request_data=request_data)
    if info is None:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": message}
    elif tracking_code:
        return {"status": 200, "tracking_code": tracking_code, "method_type": method_type,
                "response": info}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."}


def update_user(conn, cursor, request_data, info):
    method_type = "UPDATE"
    if info["role"] == "ins":
        token, data = institute_service.update_ins_user_profile(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": data, "message": "اطلاعات شما با موفقیت تغییر یافت."}}
    elif info["role"] == "sch":
        token, data = school_service.update_sch_user_profile(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": data, "message": "اطلاعات شما با موفقیت تغییر یافت."}}
    elif info["role"] == "con":
        token, data = consultant_service.update_con_user_profile(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": data, "message": "اطلاعات شما با موفقیت تغییر یافت."}}
    elif info["role"] == "wCon":
        token, data = owner_consultant_service.update_wcon_user_profile(conn=conn, cursor=cursor, request_data=request_data,
                                               info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": data, "message": "اطلاعات شما با موفقیت تغییر یافت."}}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."}


def update_password(conn, cursor, request_data, info):
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
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "رمز عبور و تکرار رمز عبور باهم تطابق ندارد."}
    if not val:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": message}
    role = info.get("role")
    role_table_map = {
        "ins": "ins",
        "sch": "sch",
        "wCon": "wCon",
        "con": "con",
    }

    role_table = role_table_map.get(role)
    if not role_table:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."}

    token = func_helper.update_user_and_role_password(
        conn=conn,
        cursor=cursor,
        request_data=request_data,
        info=info,
        role_table=role_table,
    )
    if not token:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."}

    return {"status": 200, "tracking_code": token, "method_type": method_type,
            "response": {"message": "رمز عبور شما با موفقیت تغییر کرد."}}


def update_setting(conn, cursor, request_data, info):
    method_type = "UPDATE"
    if info["role"] == "ins":
        token = institute_service.update_ins_setting(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": "پیش اطلاعات اولیه آزمون شما تغییر یافت."}}
    elif info["role"] == "sch":
        token = school_service.update_sch_setting(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": "پیش اطلاعات اولیه آزمون شما تغییر یافت."}}
    elif info["role"] == "wCon":
        token = owner_consultant_service.update_wcon_setting(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": "پیش اطلاعات اولیه آزمون شما تغییر یافت."}}
    elif info["role"] in ["con"]:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "شما به این سرویس دسترسی ندارید."}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."}


def update_student_access(conn, cursor, request_data, info):
    method_type = "UPDATE"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["stu_id", "limit", "permission", "kind"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response
    if info["role"] == "ins":
        token, message = institute_service.update_ins_student_access(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": message}}
    elif info["role"] == "sch":
        token, message = school_service.update_sch_student_access(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": message}}
    elif info["role"] == "wCon":
        token, message = owner_consultant_service.update_wcon_student_access(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": message}}
    elif info["role"] in ["con"]:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "شما به این سرویس دسترسی ندارید."}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."}


def update_user_quiz_setting(conn, cursor, request_data, info):
    method_type = "UPDATE"
    if info["role"] == "ins":
        token = institute_service.update_ins_setting(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": "پیش اطلاعات اولیه آزمون شما تغییر یافت."}}
    elif info["role"] == "sch":
        token = school_service.update_sch_setting(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": "پیش اطلاعات اولیه آزمون شما تغییر یافت."}}
    elif info["role"] == "wCon":
        token = owner_consultant_service.update_wcon_setting(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": "پیش اطلاعات اولیه آزمون شما تغییر یافت."}}
    elif info["role"] in ["con"]:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "شما به این سرویس دسترسی ندارید."}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."}


# The users functionality

def select_dashboard(conn, cursor, request_data, info):
    method_type = "SELECT"
    if info["role"] == "ins":
        token, dash_info, notifications = institute_service.select_ins_dashboard(conn=conn, cursor=cursor, request_data=request_data,
                                                               info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": dash_info, "notifications": notifications}}
    elif info["role"] == "sch":
        token, dash_info, notifications = school_service.select_sch_dashboard(conn=conn, cursor=cursor, request_data=request_data,
                                                               info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": dash_info, "notifications": notifications}}
    elif info["role"] == "wCon":
        token, dash_info, notifications = owner_consultant_service.select_wcon_dashboard(conn=conn, cursor=cursor, request_data=request_data,
                                                                info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": dash_info, "notifications": notifications}}
    elif info["role"] == "con":
        token, dash_info, notifications = consultant_service.select_con_dashboard(conn=conn, cursor=cursor, request_data=request_data,
                                                               info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": dash_info, "notifications": notifications}}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."}


# this gateway is for get the consultants list of roles
def select_consultants(conn, cursor, request_data, info):
    method_type = "SELECT"
    if info["role"] == "ins":
        token, cons_info = institute_service.select_ins_consultant(conn=conn, cursor=cursor, request_data=request_data,
                                                 info=info)
        if token is not None:
            return {"status": 200, "tracking_code": token, "method_type": method_type,
                    "response": {"data": cons_info}}
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "اطلاعات مشاورین مشکل دارد، با پشتیبانی در ارتباط باشید."}
    elif info["role"] == "sch":
        token, cons_info = school_service.select_sch_consultant(conn=conn, cursor=cursor, request_data=request_data,
                                                 info=info)
        if token is not None:
            return {"status": 200, "tracking_code": token, "method_type": method_type,
                    "response": {"data": cons_info}}
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "اطلاعات مشاورین مشکل دارد، با پشتیبانی در ارتباط باشید."}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "شما به این سرویس دسترسی ندارید."}


# this gateway for insert consultant for user role
def insert_consultant(conn, cursor, request_data, info):
    method_type = "INSERT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    con_user_id, password, error_message = func_helper.insert_user(conn=conn, cursor=cursor, request_data=request_data, info=info)
    if not con_user_id:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": error_message}
    request_data["password"] = password
    if info["role"] == "ins":
        token, message = institute_service.insert_ins_consultant(conn=conn, cursor=cursor, request_data=request_data,
                                               con_user_id=con_user_id, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": message}}
    elif info["role"] == "sch":
        token, message = school_service.insert_sch_consultant(conn=conn, cursor=cursor, request_data=request_data,
                                               con_user_id=con_user_id, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": message}}
    elif info["role"] in ["con", "wCon"]:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "شما به این سرویس دسترسی ندارید."}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."}


# this gateway for update the consultant information from user role
def update_consultant(conn, cursor, request_data, info):
    method_type = "UPDATE"
    if info["role"] == "ins":
        token, message = institute_service.update_ins_consultant(conn=conn, cursor=cursor, request_data=request_data, info=info)
        if token is None:
            return {"status": 200, "tracking_code": None, "method_type": method_type,
                    "error": message}
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": message}}
    elif info["role"] == "sch":
        token, message = school_service.update_sch_consultant(conn=conn, cursor=cursor, request_data=request_data, info=info)
        if token is None:
            return {"status": 200, "tracking_code": None, "method_type": method_type,
                    "error": message}
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": message}}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "شما به این سرویس دسترسی ندارید."}


# this gateway for get list of student from user role
def select_students(conn, cursor, request_data, info):
    method_type = "SELECT"
    if info["role"] == "ins":
        token, stu_conf = institute_service.select_ins_student(conn=conn, cursor=cursor, request_data=request_data,
                                             info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": stu_conf}}
    elif info["role"] == "sch":
        token, stu_conf = school_service.select_sch_student(conn=conn, cursor=cursor, request_data=request_data,
                                             info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": stu_conf}}
    if info["role"] == "con":
        token, stu_conf = consultant_service.select_con_student(conn=conn, cursor=cursor, request_data=request_data,
                                             info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": stu_conf}}
    elif info["role"] == "wCon":
        token, stu_conf = owner_consultant_service.select_wcon_student(conn=conn, cursor=cursor, request_data=request_data,
                                              info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": stu_conf}}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."}

def check_student_access(conn, cursor, student_user_id, info):
    """
    Check if the current user has access to the specified student.
    For ins/sch roles: check if student's ins_id matches user_id
    For con/wCon roles: check if student's con_id matches user_id
    Returns True if access is granted, False otherwise.
    """
    try:
        query = 'SELECT ins_id, con_id FROM stu WHERE user_id = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=student_user_id)
        if not res:
            return False
        
        role = info.get("role")
        user_id = info.get("user_id")
        
        if role in ["ins", "sch"]:
            # For institute/school, check if student's ins_id matches user_id
            return res.ins_id == user_id
        elif role in ["con", "wCon"]:
            # For consultant/owner consultant, check if student's con_id matches user_id
            return res.con_id == user_id
        
        return False
    except Exception as e:
        print(f"Error checking student access: {e}")
        return False


def select_report_data(conn, cursor, request_data, info):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["student_id", "report_type"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response
    
    if info["role"] in ["ins", "sch", "con", "wCon"]:
        student_id = request_data.get("student_id")
        # Check if user has access to this student
        if not check_student_access(conn, cursor, student_id, info):
            return {"status": 200, "tracking_code": None, "method_type": method_type,
                    "error": "شما به این دانش‌آموز دسترسی ندارید."}
        
        token, stu_conf = other_service.get_report_data(conn=conn, cursor=cursor, request_data=request_data,
                                             info=info)
        if token is None:
            return {"status": 200, "tracking_code": None, "method_type": method_type,
                    "error": "خطا در دریافت اطلاعات گزارش."}
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": stu_conf}}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."}

# this gateway for insert student for user role
def insert_student(conn, cursor, request_data, info):
    method_type = "INSERT"
    # No strict required fields here because phone/password are generated,
    # but you can add validation for optional metadata if needed.
    stu_user_id, password, phone, error_message = func_helper.insert_user_student(conn=conn, cursor=cursor, info=info)
    if not stu_user_id:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": error_message}
    request_data["phone"] = phone
    request_data["password"] = password
    if info["role"] == "ins":
        token = institute_service.insert_ins_student(conn=conn, cursor=cursor, request_data=request_data, stu_user_id=stu_user_id,
                                   info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": "دانش‌آموز شما با موفقیت ثبت شد."}}
    elif info["role"] == "sch":
        token = school_service.insert_sch_student(conn=conn, cursor=cursor, request_data=request_data, stu_user_id=stu_user_id,
                                   info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": "دانش‌آموز شما با موفقیت ثبت شد."}}
    elif info["role"] == "wCon":
        token = owner_consultant_service.insert_wcon_student(conn=conn, cursor=cursor, request_data=request_data, stu_user_id=stu_user_id,
                                    info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": "دانش‌آموز شما با موفقیت ثبت شد."}}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "شما به این سرویس دسترسی ندارید."}


# this gateway for update the student information from user role
def update_student(conn, cursor, request_data, info):
    method_type = "UPDATE"
    required_fields = ["first_name", "last_name", "sex", "city", "birth_date", "student_id"]
    if info["role"] in ["ins", "sch"]:
        required_fields.append("con_id")
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=required_fields,
        method_type=method_type,
    )
    if not is_valid:
        return error_response
    if info["role"] == "ins":
        token = institute_service.update_ins_student(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": "اطلاعات دانش‌آموز شما با موفقیت تغییر کرد."}}
    elif info["role"] == "sch":
        token = school_service.update_sch_student(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": "اطلاعات دانش‌آموز شما با موفقیت تغییر کرد."}}
    elif info["role"] == "wCon":
        token = owner_consultant_service.update_wcon_student(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": "اطلاعات دانش‌آموز شما با موفقیت تغییر کرد."}}
    elif info["role"] == "con":
        token = consultant_service.update_con_student(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": "اطلاعات دانش‌آموز شما با موفقیت تغییر کرد."}}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."}


# this gateway is for make or update the comment of the student
def make_comment(conn, cursor, request_data, info):
    method_type = "UPDATE"
    if info["role"] == "con":
        token = consultant_service.update_con_comment(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": "اطلاعات دانش‌آموز شما با موفقیت تغییر کرد."}}
    elif info["role"] == "wCon":
        token = owner_consultant_service.update_wcon_comment(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": "اطلاعات دانش‌آموز شما با موفقیت تغییر کرد."}}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "متاسفانه شما از این سامانه به این سرویس دسترسی ندارید."}


def select_quiz_setting(conn, cursor, request_data, info):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["quiz_id"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    quiz_id = request_data["quiz_id"]
    query_select_setting = "select * from setting where setting.user_id = '" + str(
        info["user_id"]) + "' and setting.quiz_id = '" + str(quiz_id) + "' "
    cursor.execute(query_select_setting)
    res = cursor.fetchone()
    conn.commit()
    token = func_helper.get_tracking_code()
    if res is None:
        quiz_info = quiz_data_extractor.get_quiz_info(quiz_id=quiz_id)
        info_data = {"voice": quiz_info["voice"], "description": quiz_info["description"], "setting_id": "no setting"}
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": info_data}}
    elif len(res) == 0:
        quiz_info = quiz_data_extractor.get_quiz_info(quiz_id=quiz_id)
        info_data = {"voice": quiz_info["voice"], "description": quiz_info["description"], "setting_id": "no setting"}
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": info_data}}
    else:
        info_data = {"voice": res[3], "description": res[2], "setting_id": res[0]}
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": info_data}}


def select_report(conn, cursor, request_data, info):
    method_type = "SELECT"
    if info["role"] == "ins":
        token, data = institute_service.select_ins_report(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": data}}
    elif info["role"] == "sch":
        token, data = school_service.select_sch_report(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": data}}
    elif info["role"] == "wCon":
        token, data = owner_consultant_service.select_wcon_report(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": data}}
    elif info["role"] == "con":
        token, data = consultant_service.select_con_report(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": data}}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."}


def select_management_report(conn, cursor, request_data, info):
    method_type = "SELECT"
    if info["role"] == "ins":
        token, data = institute_service.select_ins_management_report(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": data}}
    elif info["role"] == "sch":
        token, data = school_service.select_sch_management_report(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": data}}
    elif info["role"] == "wCon":
        token, data = owner_consultant_service.select_wcon_management_report(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": data}}
    elif info["role"] == "con":
        token, data = consultant_service.select_con_management_report(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": data}}
    elif info["role"] == "stu":
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "متاسفانه شما از این سامانه به این سرویس دسترسی ندارید."}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."}


# get the information of quiz (quiz id, quiz description, quiz voice, quiz sections, quiz name)
def select_quiz_info(conn, cursor, request_data, info):
    method_type = "SELECT"
    if info["role"] not in ["ins", "sch", "wCon", "con"]:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "متاسفانه شما از این سامانه به این سرویس دسترسی ندارید."}
    else:
        token = func_helper.get_tracking_code()
        quiz_info = quiz_data_extractor.get_quiz_table_info()
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": quiz_info}}


# transactions and payments
def get_users_transactions(conn, cursor, request_data, info):
    method_type = "SELECT"
    if info["role"] in ["wCon", "ins", "sch"]:
        token, transactions_info = other_service.select_users_transactions(conn, cursor, request_data, info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"data": transactions_info}}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."}


def apply_discount(conn, cursor, request_data, info):
    try:
        method_type = "SELECT"
        is_valid, error_response = func_helper.validate_request_data_fields(
            request_data=request_data,
            required_fields=["discount_code", "total_value"],
            method_type=method_type,
        )
        if not is_valid:
            return error_response

        query = 'SELECT id, discount_percentage, count, status, count_apply, expire_time FROM discount WHERE code = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=request_data["discount_code"])
        if not res:
            return {"status": 200, "tracking_code": None, "method_type": method_type,
                    "error": "کد تخفیف مد نظر شما موجود نیست."}
        else:
            if res.expire_time:
                if datetime.now() > res.expire_time:
                    return {"status": 200, "tracking_code": None, "method_type": method_type,
                            "error": "متاسفانه زمان مصرف این کد به پایان رسیده."}

            elif res.status == 'expired':
                return {"status": 200, "tracking_code": None, "method_type": method_type,
                        "error": "متاسفانه زمان مصرف این کد به پایان رسیده."}
            elif res.count == 0:
                return {"status": 200, "tracking_code": None, "method_type": method_type,
                        "error": "متاسفانه کد تخفیف مدنظر اتمام یافته."}
            field = '([code], [status], [phone], [user_id])'
            values = (request_data["discount_code"], "APPLY CODE", info["phone"], info["user_id"])
            db_helper.insert_value(conn=conn, cursor=cursor, table_name='using_discount', fields=field,
                                   values=values)
            db_helper.update_record(
                conn, cursor, "discount", ["count_apply", "edited_time"], [
                    res.count_apply + 1,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ], "id = ?", [res.id]
            )
        token = func_helper.get_tracking_code()
        new_total = (round(int(request_data["total_value"]) * (1 - res.discount_percentage)))/100
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"new_total": new_total}}
    except Exception as e:
        print("error occurred in apply discount", e)
        return {"status": 200, "tracking_code": None, "method_type": None,
                "error": "در پردازش کد تخفیف مشکلی پیش آمده"}

def insert_order_payment(conn, cursor, request_data, info):
    method_type = "INSERT"
    # is_valid, error_response = func_helper.validate_request_data_fields(
    #     request_data=request_data,
    #     required_fields=["price", "discount_code", "AG", "SCL"],
    #     method_type=method_type,
    # )
    # if not is_valid:
    #     return error_response
    if info["role"] in ["wCon", "ins", "sch"]:
        token, ref_id, message, url = other_service.order_payment(conn=conn, cursor=cursor, request_data=request_data, info=info)
        return {"status": 200, "tracking_code": token, "method_type": method_type,
                "response": {"message": message, "url": url, "ref_id": ref_id}}
    else:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."}



def select_comments(conn, cursor):
    method_type = "SELECT"
    query = """
            SELECT TOP 100
                id, 
                name,
                comment, 
                rating,
                persian_date
            FROM comments 
            ORDER BY created_time DESC
        """
    res = db_helper.search_fetchall(conn=conn, cursor=cursor, query=query)
    comments = [
        {
            "id": p["id"],
            "name": p["name"],
            "comment": p["comment"],
            "rating": p["rating"],
            "persian_date": p["persian_date"],
        }
        for p in res
    ]
    token = func_helper.get_tracking_code()
    return {
        "status": 200,
        "tracking_code": token,
        "method_type": method_type,
        "response": comments
    }


def insert_comment(conn, cursor, request_data):
    method_type = "INSERT"
    user_role = None
    name = ""
    query = 'SELECT role, user_id FROM users WHERE phone = ?'
    res_role = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=request_data["phone"])
    if res_role is None:
        return {
            "status": 422,
            "tracking_code": None,
            "method_type": method_type,
            "response": ""
        }
    else:
        user_role = res_role[0]
    if user_role in ["ins", "sch"]:
        if user_role == "ins":
            query = 'SELECT user_id, name, phone FROM ins WHERE phone = ?'
        else:
            query = 'SELECT user_id, name, phone FROM sch WHERE phone = ?'
        res_user = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=request_data["phone"])
        if res_user is None:
            return {
                "status": 422,
                "tracking_code": None,
                "method_type": method_type,
                "response": ""
            }
        name = res_user[1]
    elif user_role in ["con", "wCon"]:
        if user_role == "con":
            query = 'SELECT user_id, first_name, last_name, phone FROM con WHERE phone = ?'
        else:
            query = 'SELECT user_id, first_name, last_name, phone FROM wCon WHERE phone = ?'
        res_user = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=request_data["phone"])
        if res_user is None:
            return {
                "status": 422,
                "tracking_code": None,
                "method_type": method_type,
                "response": ""
            }
        name = res_user[1] + " " + res_user[2]
    field = '([name], [comment], [rating], [persian_date], [user_id], [phone], [db_name], [role])'
    values = (
        request_data["first_name"] + " " + request_data["last_name"], request_data["comment"], request_data["rating"], request_data["date"], res_role[1],
        request_data["phone"], name, user_role,)
    db_helper.insert_value(conn=conn, cursor=cursor, table_name='comments', fields=field,
                           values=values)
    token = func_helper.get_tracking_code()
    return {
        "status": 200,
        "tracking_code": token,
        "method_type": method_type,
        "response": ""
    }


# Admin functions
def admin_update_capacity(conn, cursor, request_data):
    method_type = "UPDATE"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone", "kind", "count"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response
    
    token, result = admin_service.update_capacity(conn=conn, cursor=cursor, request_data=request_data)
    if token is None:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": result}
    return {"status": 200, "tracking_code": token, "method_type": method_type,
            "response": result}


def admin_get_user_info(conn, cursor, request_data):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response
    
    token, result = admin_service.get_user_info(conn=conn, cursor=cursor, request_data=request_data)
    if token is None:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": result}
    return {"status": 200, "tracking_code": token, "method_type": method_type,
            "response": result}


def admin_check_student_quiz_answer(conn, cursor, request_data):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response
    
    token, result = admin_service.check_student_quiz_answer(conn=conn, cursor=cursor, request_data=request_data)
    if token is None:
        return {"status": 200, "tracking_code": None, "method_type": method_type,
                "error": result}
    return {"status": 200, "tracking_code": token, "method_type": method_type,
            "response": result}
