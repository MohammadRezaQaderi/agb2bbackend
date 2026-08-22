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
import services.student.student_service as student_service


DEFAULT_SERVICE_ERROR = "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."
ACCESS_DENIED_MESSAGE = "شما به این سرویس دسترسی ندارید."


def _error_response(method_type, message=DEFAULT_SERVICE_ERROR):
    return {"status": 200, "tracking_code": None, "method_type": method_type, "error": message}


def _service_response(method_type, tracking_token, response_data=None, response_message="", error_message=None,
                      **extra_response):
    if tracking_token:
        response = {"data": response_data, "message": response_message}
        response.update(extra_response)
        return {"status": 200, "tracking_code": tracking_token, "method_type": method_type,
                "response": response}
    return _error_response(method_type=method_type, message=error_message or response_message or DEFAULT_SERVICE_ERROR)


def service_response(method_type, tracking_token, response_data=None, response_message="", error_message=None,
                     **extra_response):
    return _service_response(method_type, tracking_token, response_data, response_message, error_message,
                             **extra_response)


def _role_handler(user_info, handlers):
    handler = handlers.get(user_info.get("role"))
    return handler() if handler else None


def remove_token(conn, cursor, request_data, user_info):
    method_type = "DELETE"
    tracking_token, response_data, response_message = auth_service.remove_token(
        conn=conn, cursor=cursor, request_data=request_data, user_info=user_info
    )
    return _service_response(method_type, tracking_token, response_data, response_message)


def sign_in(conn, cursor, request_data):
    method_type = "SIGNIN"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone", "password"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    tracking_token, response_data, response_message = auth_service.sign_in(
        conn=conn, cursor=cursor, request_data=request_data
    )
    return _service_response(method_type, tracking_token, response_data, response_message)


def student_sign_in(conn, cursor, request_data):
    method_type = "SIGNIN"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone", "password"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    tracking_token, response_data, response_message = auth_service.sign_in_student(
        conn=conn, cursor=cursor, request_data=request_data
    )
    return _service_response(method_type, tracking_token, response_data, response_message)


def sign_up(conn, cursor, redis_db, request_data):
    method_type = "INSERT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone", "password", "re_password", "role"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    tracking_token, response_data, response_message = auth_service.sign_up(
        conn=conn, cursor=cursor, redis_db=redis_db, request_data=request_data
    )
    return _service_response(method_type, tracking_token, response_data, response_message)


def send_otp(conn, cursor, redis_db, request_data):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone", "type", "code", "check"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    tracking_token, response_data, response_message = auth_service.send_otp(
        conn=conn, cursor=cursor, redis_db=redis_db, request_data=request_data
    )
    return _service_response(method_type, tracking_token, response_data, response_message)


def check_otp(conn, cursor, redis_db, request_data):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone", "code", "type"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    tracking_token, response_data, response_message = auth_service.check_otp(
        conn=conn, cursor=cursor, redis_db=redis_db, request_data=request_data
    )
    return _service_response(method_type, tracking_token, response_data, response_message)


def change_user_info(conn, cursor, request_data, user_info):
    method_type = "UPDATE"
    result = _role_handler(user_info, {
        "ins": lambda: institute_service.change_user_info(conn=conn, cursor=cursor, request_data=request_data,
                                                          user_info=user_info),
        "sch": lambda: school_service.change_user_info(conn=conn, cursor=cursor, request_data=request_data,
                                                       user_info=user_info),
        "con": lambda: consultant_service.change_user_info(conn=conn, cursor=cursor, request_data=request_data,
                                                           user_info=user_info),
        "ocon": lambda: owner_consultant_service.change_user_info(conn=conn, cursor=cursor,
                                                                  request_data=request_data, user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


def change_password(conn, cursor, request_data, user_info):
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
        conn=conn,
        cursor=cursor,
        request_data=request_data,
        user_info=user_info,
        role_table=role_table,
    )
    response_data = None
    response_message = "رمز عبور شما با موفقیت تغییر کرد."
    return _service_response(method_type, tracking_token, response_data, response_message)


def student_change_user_info(conn, cursor, request_data, user_info):
    method_type = "UPDATE"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["first_name", "last_name"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response
    if user_info["role"] != "stu":
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = student_service.update_stu_user_profile(
        conn=conn, cursor=cursor, request_data=request_data, info=user_info
    )
    return _service_response(method_type, tracking_token, response_data, response_message)


def student_change_password(conn, cursor, request_data, user_info):
    method_type = "UPDATE"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["password", "re_password"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    if request_data["password"] != request_data["re_password"]:
        return _error_response(method_type, "رمز عبور و تکرار رمز عبور باهم تطابق ندارد.")

    val, message = func_helper.password_format_check(password=request_data["password"])
    if not val:
        return _error_response(method_type, message)

    if user_info["role"] != "stu":
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = student_service.update_stu_password(
        conn=conn, cursor=cursor, request_data=request_data, info=user_info
    )
    return _service_response(method_type, tracking_token, response_data, response_message)


def student_get_dashboard(conn, cursor, request_data, user_info):
    method_type = "SELECT"
    if user_info["role"] != "stu":
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = student_service.select_stu_dashboard(
        conn=conn, cursor=cursor, request_data=request_data, info=user_info
    )
    return _service_response(method_type, tracking_token, response_data, response_message)


def student_get_quiz_setting(conn, cursor, request_data, user_info):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["quiz_id"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response
    return get_quiz_setting(conn=conn, cursor=cursor, request_data=request_data, user_info=user_info)


def student_get_quiz_table_info(conn, cursor, request_data, user_info):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["kind"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response
    if user_info["role"] != "stu":
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = student_service.select_stu_quiz_table_info(
        conn=conn, cursor=cursor, request_data=request_data, info=user_info
    )
    return _service_response(method_type, tracking_token, response_data, response_message)


def student_get_quiz_info(conn, cursor, request_data, user_info):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["quiz_id", "quiz_kind"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response
    if user_info["role"] != "stu":
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = student_service.select_stu_quiz_info(
        conn=conn, cursor=cursor, request_data=request_data, info=user_info
    )
    if not response_data:
        return _error_response(method_type, response_message or "آزمون مورد نظر شما در دسترس شما نیست.")
    return _service_response(method_type, tracking_token, response_data, response_message)


def student_change_quiz_answer(conn, cursor, request_data, user_info):
    method_type = "UPDATE"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["quiz_id", "question_Number", "question_Answer", "last_question_id", "user_id"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response
    if user_info["role"] != "stu":
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = student_service.submit_quiz_answer(
        conn=conn, cursor=cursor, request_data=request_data, info=user_info
    )
    return _service_response(method_type, tracking_token, response_data, response_message)


def student_get_access_product(conn, cursor, request_data, user_info):
    method_type = "SELECT"
    if user_info["role"] != "stu":
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = student_service.select_student_access_info(
        conn=conn, cursor=cursor, request_data=request_data, info=user_info
    )
    return _service_response(method_type, tracking_token, response_data, response_message)


def change_setting(conn, cursor, request_data, user_info):
    method_type = "UPDATE"
    if user_info["role"] == "con":
        return _error_response(method_type, ACCESS_DENIED_MESSAGE)

    result = _role_handler(user_info, {
        "ins": lambda: institute_service.change_setting(conn=conn, cursor=cursor, request_data=request_data,
                                                        user_info=user_info),
        "sch": lambda: school_service.change_setting(conn=conn, cursor=cursor, request_data=request_data,
                                                     user_info=user_info),
        "ocon": lambda: owner_consultant_service.change_setting(conn=conn, cursor=cursor, request_data=request_data,
                                                                user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


def change_student_access(conn, cursor, request_data, user_info):
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
        "ins": lambda: institute_service.change_student_access(conn=conn, cursor=cursor, request_data=request_data,
                                                               user_info=user_info),
        "sch": lambda: school_service.change_student_access(conn=conn, cursor=cursor, request_data=request_data,
                                                            user_info=user_info),
        "ocon": lambda: owner_consultant_service.change_student_access(conn=conn, cursor=cursor,
                                                                       request_data=request_data, user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


def change_user_quiz_setting(conn, cursor, request_data, user_info):
    return change_setting(conn=conn, cursor=cursor, request_data=request_data, user_info=user_info)


# The users functionality

def get_dashboard(conn, cursor, request_data, user_info):
    method_type = "SELECT"
    result = _role_handler(user_info, {
        "ins": lambda: institute_service.get_dashboard(conn=conn, cursor=cursor, request_data=request_data,
                                                       user_info=user_info),
        "sch": lambda: school_service.get_dashboard(conn=conn, cursor=cursor, request_data=request_data,
                                                    user_info=user_info),
        "ocon": lambda: owner_consultant_service.get_dashboard(conn=conn, cursor=cursor, request_data=request_data,
                                                               user_info=user_info),
        "con": lambda: consultant_service.get_dashboard(conn=conn, cursor=cursor, request_data=request_data,
                                                        user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


# this gateway is for get the consultants list of roles
def get_consultants(conn, cursor, request_data, user_info):
    method_type = "SELECT"
    result = _role_handler(user_info, {
        "ins": lambda: institute_service.get_consultants(conn=conn, cursor=cursor, request_data=request_data,
                                                         user_info=user_info),
        "sch": lambda: school_service.get_consultants(conn=conn, cursor=cursor, request_data=request_data,
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
def add_consultant(conn, cursor, request_data, user_info):
    method_type = "INSERT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    con_user_id, password, error_message = func_helper.insert_user(conn=conn, cursor=cursor, request_data=request_data, user_info=user_info)
    if not con_user_id:
        return _error_response(method_type, error_message)
    request_data["password"] = password
    if user_info["role"] in ["con", "ocon"]:
        return _error_response(method_type, ACCESS_DENIED_MESSAGE)

    result = _role_handler(user_info, {
        "ins": lambda: institute_service.add_consultant(conn=conn, cursor=cursor, request_data=request_data,
                                                        con_user_id=con_user_id, user_info=user_info),
        "sch": lambda: school_service.add_consultant(conn=conn, cursor=cursor, request_data=request_data,
                                                     con_user_id=con_user_id, user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


# this gateway for update the consultant information from user role
def change_consultant(conn, cursor, request_data, user_info):
    method_type = "UPDATE"
    result = _role_handler(user_info, {
        "ins": lambda: institute_service.change_consultant(conn=conn, cursor=cursor, request_data=request_data,
                                                           user_info=user_info),
        "sch": lambda: school_service.change_consultant(conn=conn, cursor=cursor, request_data=request_data,
                                                        user_info=user_info),
    })
    if result is None:
        return _error_response(method_type, ACCESS_DENIED_MESSAGE)

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


# this gateway for get list of student from user role
def get_students(conn, cursor, request_data, user_info):
    method_type = "SELECT"
    result = _role_handler(user_info, {
        "ins": lambda: institute_service.get_students(conn=conn, cursor=cursor, request_data=request_data,
                                                      user_info=user_info),
        "sch": lambda: school_service.get_students(conn=conn, cursor=cursor, request_data=request_data,
                                                   user_info=user_info),
        "con": lambda: consultant_service.get_students(conn=conn, cursor=cursor, request_data=request_data,
                                                       user_info=user_info),
        "ocon": lambda: owner_consultant_service.get_students(conn=conn, cursor=cursor, request_data=request_data,
                                                              user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)

def check_student_access(conn, cursor, student_user_id, user_info):
    """
    Check if the current user has access to the specified student.
    For ins/sch roles: check if student's owner_user_id matches user_id.
    For con/ocon roles: check if student's consultant_user_id matches user_id.
    Returns True if access is granted, False otherwise.
    """
    try:
        query = 'SELECT owner_user_id, consultant_user_id FROM stu WHERE user_id = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=student_user_id)
        if not res:
            return False
        
        role = user_info.get("role")
        user_id = user_info.get("user_id")
        
        if role in ["ins", "sch"]:
            return res.owner_user_id == user_id
        elif role in ["con", "ocon"]:
            return res.consultant_user_id == user_id
        
        return False
    except Exception as e:
        print(f"Error checking student access: {e}")
        return False


def get_report_data(conn, cursor, request_data, user_info):
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
        if not check_student_access(conn, cursor, student_id, user_info):
            return _error_response(method_type, "شما به این دانش‌آموز دسترسی ندارید.")
        
        tracking_token, response_data, response_message = other_service.get_report_data(conn=conn, cursor=cursor, request_data=request_data,
                                             user_info=user_info)
        return _service_response(
            method_type, tracking_token, response_data, response_message, error_message="خطا در دریافت اطلاعات گزارش."
        )
    else:
        return func_helper.not_method_access_return()

# this gateway for insert student for user role
def add_student(conn, cursor, request_data, user_info):
    method_type = "INSERT"
    # No strict required fields here because phone/password are generated,
    # but you can add validation for optional metadata if needed.
    stu_user_id, password, phone, error_message = func_helper.insert_user_student(conn=conn, cursor=cursor, user_info=user_info)
    if not stu_user_id:
        return _error_response(method_type, error_message)
    request_data["phone"] = phone
    request_data["password"] = password
    result = _role_handler(user_info, {
        "ins": lambda: institute_service.add_student(conn=conn, cursor=cursor, request_data=request_data,
                                                     stu_user_id=stu_user_id, user_info=user_info),
        "sch": lambda: school_service.add_student(conn=conn, cursor=cursor, request_data=request_data,
                                                  stu_user_id=stu_user_id, user_info=user_info),
        "ocon": lambda: owner_consultant_service.add_student(conn=conn, cursor=cursor, request_data=request_data,
                                                             stu_user_id=stu_user_id, user_info=user_info),
    })
    if result is None:
        return _error_response(method_type, ACCESS_DENIED_MESSAGE)

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


# this gateway for update the student information from user role
def change_student(conn, cursor, request_data, user_info):
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
        "ins": lambda: institute_service.change_student(conn=conn, cursor=cursor, request_data=request_data,
                                                        user_info=user_info),
        "sch": lambda: school_service.change_student(conn=conn, cursor=cursor, request_data=request_data,
                                                     user_info=user_info),
        "ocon": lambda: owner_consultant_service.change_student(conn=conn, cursor=cursor, request_data=request_data,
                                                                user_info=user_info),
        "con": lambda: consultant_service.change_student(conn=conn, cursor=cursor, request_data=request_data,
                                                         user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


# this gateway is for make or update the comment of the student
def change_comment(conn, cursor, request_data, user_info):
    method_type = "UPDATE"
    result = _role_handler(user_info, {
        "con": lambda: consultant_service.change_comment(conn=conn, cursor=cursor, request_data=request_data,
                                                         user_info=user_info),
        "ocon": lambda: owner_consultant_service.change_comment(conn=conn, cursor=cursor, request_data=request_data,
                                                                user_info=user_info),
    })
    if result is None:
        return _error_response(method_type, "متاسفانه شما از این سامانه به این سرویس دسترسی ندارید.")

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


def get_quiz_setting(conn, cursor, request_data, user_info):
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
        user_info["user_id"]) + "' and setting.quiz_id = '" + str(quiz_id) + "' "
    cursor.execute(query_select_setting)
    res = cursor.fetchone()
    conn.commit()
    token = func_helper.get_tracking_code()
    if res is None:
        quiz_info = quiz_data_extractor.get_quiz_info(quiz_id=quiz_id)
        info_data = {"voice": quiz_info["voice"], "description": quiz_info["description"], "setting_id": "no setting"}
        return _service_response(method_type, token, info_data)
    elif len(res) == 0:
        quiz_info = quiz_data_extractor.get_quiz_info(quiz_id=quiz_id)
        info_data = {"voice": quiz_info["voice"], "description": quiz_info["description"], "setting_id": "no setting"}
        return _service_response(method_type, token, info_data)
    else:
        info_data = {"voice": res[3], "description": res[2], "setting_id": res[0]}
        return _service_response(method_type, token, info_data)


def get_report(conn, cursor, request_data, user_info):
    method_type = "SELECT"
    result = _role_handler(user_info, {
        "ins": lambda: institute_service.get_report(conn=conn, cursor=cursor, request_data=request_data,
                                                    user_info=user_info),
        "sch": lambda: school_service.get_report(conn=conn, cursor=cursor, request_data=request_data,
                                                 user_info=user_info),
        "ocon": lambda: owner_consultant_service.get_report(conn=conn, cursor=cursor, request_data=request_data,
                                                            user_info=user_info),
        "con": lambda: consultant_service.get_report(conn=conn, cursor=cursor, request_data=request_data,
                                                     user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


def get_management_report(conn, cursor, request_data, user_info):
    method_type = "SELECT"
    if user_info["role"] == "stu":
        return _error_response(method_type, "متاسفانه شما از این سامانه به این سرویس دسترسی ندارید.")

    result = _role_handler(user_info, {
        "ins": lambda: institute_service.get_management_report(conn=conn, cursor=cursor, request_data=request_data,
                                                               user_info=user_info),
        "sch": lambda: school_service.get_management_report(conn=conn, cursor=cursor, request_data=request_data,
                                                            user_info=user_info),
        "ocon": lambda: owner_consultant_service.get_management_report(conn=conn, cursor=cursor,
                                                                       request_data=request_data,
                                                                       user_info=user_info),
        "con": lambda: consultant_service.get_management_report(conn=conn, cursor=cursor, request_data=request_data,
                                                                user_info=user_info),
    })
    if result is None:
        return func_helper.not_method_access_return()

    tracking_token, response_data, response_message = result
    return _service_response(method_type, tracking_token, response_data, response_message)


# get the information of quiz (quiz id, quiz description, quiz voice, quiz sections, quiz name)
def get_quiz_info(conn, cursor, request_data, user_info):
    method_type = "SELECT"
    if user_info["role"] not in ["ins", "sch", "ocon", "con"]:
        return _error_response(method_type, "متاسفانه شما از این سامانه به این سرویس دسترسی ندارید.")

    tracking_token = func_helper.get_tracking_code()
    response_data = quiz_data_extractor.get_quiz_table_info()
    return _service_response(method_type, tracking_token, response_data, "")


# transactions and payments
def get_transactions(conn, cursor, request_data, user_info):
    method_type = "SELECT"
    if user_info["role"] in ["ocon", "ins", "sch"]:
        tracking_token, response_data, response_message = other_service.get_transactions(conn, cursor, request_data, user_info)
        return _service_response(method_type, tracking_token, response_data, response_message)
    return func_helper.not_method_access_return()


def apply_discount(conn, cursor, request_data, user_info):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["discount_code", "total_value"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    tracking_token, response_data, response_message = other_service.apply_discount(
        conn=conn, cursor=cursor, request_data=request_data, user_info=user_info
    )
    return _service_response(method_type, tracking_token, response_data, response_message)

def add_payment_order(conn, cursor, request_data, user_info):
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
            conn=conn, cursor=cursor, request_data=request_data, user_info=user_info
        )
        return _service_response(method_type, tracking_token, response_data, response_message)
    return _error_response(method_type, DEFAULT_SERVICE_ERROR)

def get_comments(conn, cursor):
    method_type = "SELECT"
    tracking_token, response_data, response_message = other_service.get_comments(conn=conn, cursor=cursor)
    return _service_response(method_type, tracking_token, response_data, response_message)


def add_comment(conn, cursor, request_data):
    method_type = "INSERT"
    tracking_token, response_data, response_message = other_service.add_comment(
        conn=conn, cursor=cursor, request_data=request_data
    )
    return _service_response(method_type, tracking_token, response_data, response_message)


def mark_notification_read(conn, cursor, request_data, user_info):
    method_type = "INSERT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["notification_id"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response

    tracking_token, response_data, response_message = other_service.mark_notification_read(
        conn=conn, cursor=cursor, request_data=request_data, user_info=user_info
    )
    return _service_response(method_type, tracking_token, response_data, response_message)


# Admin functions
def admin_change_capacity(conn, cursor, request_data):
    method_type = "UPDATE"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone", "kind", "count"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response
    
    tracking_token, response_data, response_message = admin_service.change_capacity(conn=conn, cursor=cursor, request_data=request_data)
    return _service_response(method_type, tracking_token, response_data, response_message)


def admin_get_user_info(conn, cursor, request_data):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response
    
    tracking_token, response_data, response_message = admin_service.get_user_info(conn=conn, cursor=cursor, request_data=request_data)
    return _service_response(method_type, tracking_token, response_data, response_message)


def admin_check_student_quiz_answer(conn, cursor, request_data):
    method_type = "SELECT"
    is_valid, error_response = func_helper.validate_request_data_fields(
        request_data=request_data,
        required_fields=["phone"],
        method_type=method_type,
    )
    if not is_valid:
        return error_response
    
    tracking_token, response_data, response_message = admin_service.check_student_quiz_answer(
        conn=conn, cursor=cursor, request_data=request_data
    )
    return _service_response(method_type, tracking_token, response_data, response_message)
