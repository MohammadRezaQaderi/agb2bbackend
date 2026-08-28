import os

from fastapi import FastAPI, Request, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse

import helper.db.db_helper as db_helper
import helper.api_metrics as api_metrics
import helper.func_helper as func_helper
import helper.static_data.get_data as static_data
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.report_downloads import get_report_download_status
import services.institute.institute_service as institute_service
import services.owner_consultant.owner_consultant_service as owner_consultant_service
import services.school.school_service as school_service
import services.service as service
from config import (
    INS_PIC_DIR,
    VOICES_DIR,
    REPORTS_DIR,
    PICS_INFO_DIR,
    PICS_REPORT_DIR,
    PICS_QUIZ_DIR,
    PICS_FIELD_DIR,
    QUIZ_PIC_DIR,
    DEFAULT_REPORT_PATH,
    PICS_WORD_SCL_DIR,
)

app = FastAPI()
app.middleware("http")(api_metrics.prometheus_http_middleware)


@app.get("/ag_api/metrics")
async def metrics():
    return api_metrics.metrics_response()


@app.get("/ag_api/health")
async def health_check():
    return await func_helper.health_payload("ag_api")


@app.get("/ags_api/metrics")
async def student_metrics():
    return api_metrics.metrics_response()


@app.get("/ags_api/health")
async def student_health_check():
    return await func_helper.health_payload("ags_api")


@app.post("/ags_api/signin")
@api_metrics.monitor_endpoint("ags_api/signin")
async def student_signin_api(request: Request):
    method_type = "SIGNIN"
    conn, cursor = None, None

    try:
        data = await request.json()
        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()
        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)
        if action != "ags_sign_in":
            return func_helper.not_method_access_return()

        conn, cursor = await db_helper.db_connection()
        return service.student_sign_in(conn=conn, cursor=cursor, request_data=request_data)

    except KeyError as e:
        return await func_helper.key_error_logging("ags_api/signin", "student_signin_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ags_api/signin", "student_signin_api", str(e), method_type)
    finally:
        if conn and cursor:
            await db_helper.close_db_connection(conn=conn, cursor=cursor)


@app.post("/ags_api/select_request")
@api_metrics.monitor_endpoint("ags_api/select_request")
async def student_select_api(request: Request):
    method_type = "SELECT"
    conn, cursor = None, None

    try:
        data = await request.json()
        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()
        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)

        conn, cursor = await db_helper.db_connection()
        state, state_message, user_info = await func_helper.authorizer(
            conn=conn, cursor=cursor, request_data=request_data
        )
        if not state:
            return func_helper.not_auth_return(message=state_message)

        action_map = {
            "ags_get_dashboard": service.student_get_dashboard,
            "ags_get_quiz_setting": service.student_get_quiz_setting,
            "ags_get_access_product": service.student_get_access_product,
            "ags_get_quiz_table_info": service.student_get_quiz_table_info,
            "ags_get_quiz_info": service.student_get_quiz_info,
        }
        handler = action_map.get(action)
        if handler is None:
            return func_helper.not_method_access_return()
        return handler(conn=conn, cursor=cursor, request_data=request_data, user_info=user_info)

    except KeyError as e:
        return await func_helper.key_error_logging("ags_api/select_request", "student_select_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ags_api/select_request", "student_select_api", str(e), method_type)
    finally:
        if conn and cursor:
            await db_helper.close_db_connection(conn=conn, cursor=cursor)


@app.post("/ags_api/update_request")
@api_metrics.monitor_endpoint("ags_api/update_request")
async def student_update_api(request: Request):
    method_type = "UPDATE"
    conn, cursor = None, None

    try:
        data = await request.json()
        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()
        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)

        conn, cursor = await db_helper.db_connection()
        state, state_message, user_info = await func_helper.authorizer(
            conn=conn, cursor=cursor, request_data=request_data
        )
        if not state:
            return func_helper.not_auth_return(message=state_message)

        action_map = {
            "ags_change_user_info": service.student_change_user_info,
            "ags_change_password": service.student_change_password,
            "ags_change_quiz_answer": service.student_change_quiz_answer,
        }
        handler = action_map.get(action)
        if handler is None:
            return func_helper.not_method_access_return()
        return handler(conn=conn, cursor=cursor, request_data=request_data, user_info=user_info)

    except KeyError as e:
        return await func_helper.key_error_logging("ags_api/update_request", "student_update_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ags_api/update_request", "student_update_api", str(e), method_type)
    finally:
        if conn and cursor:
            await db_helper.close_db_connection(conn=conn, cursor=cursor)


@app.post("/ags_api/delete_request")
@api_metrics.monitor_endpoint("ags_api/delete_request")
async def student_delete_api(request: Request):
    method_type = "DELETE"
    conn, cursor = None, None

    try:
        data = await request.json()
        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()
        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)

        conn, cursor = await db_helper.db_connection()
        state, state_message, user_info = await func_helper.authorizer(
            conn=conn, cursor=cursor, request_data=request_data
        )
        if not state:
            return func_helper.not_auth_return(message=state_message)

        action_map = {
            "ags_remove_token": service.remove_token,
        }
        handler = action_map.get(action)
        if handler is None:
            return func_helper.not_method_access_return()
        return handler(conn=conn, cursor=cursor, request_data=request_data, user_info=user_info)

    except KeyError as e:
        return await func_helper.key_error_logging("ags_api/delete_request", "student_delete_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ags_api/delete_request", "student_delete_api", str(e), method_type)
    finally:
        if conn and cursor:
            await db_helper.close_db_connection(conn=conn, cursor=cursor)


@app.post("/ag_api/signin")
@api_metrics.monitor_endpoint("ag_api/signin")
async def signin_api(request: Request):
    method_type = "SIGNIN"
    conn, cursor = None, None

    try:
        data = await request.json()

        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()

        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)

        if action != "ag_sign_in":
            return func_helper.not_method_access_return()

        conn, cursor = await db_helper.db_connection()

        return service.sign_in(conn=conn, cursor=cursor, request_data=request_data)

    except KeyError as e:
        return await func_helper.key_error_logging("ag_api/signin", "signin_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api/signin", "signin_api", str(e), method_type)
    finally:
        if conn and cursor:
            await db_helper.close_db_connection(conn=conn, cursor=cursor)


@app.post("/ag_api/insert_request")
@api_metrics.monitor_endpoint("ag_api/insert_request")
async def insert_api(request: Request):
    method_type = "INSERT"
    conn, cursor = None, None

    try:
        data = await request.json()

        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()

        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)

        conn, cursor = await db_helper.db_connection()

        if action == "ag_sign_up":
            redis_db = await db_helper.redis_connection()
            try:
                return service.sign_up(conn=conn, cursor=cursor, redis_db=redis_db, request_data=request_data)
            finally:
                await db_helper.close_redis_connection(redis_db=redis_db)
        elif action == "ag_send_otp":
            redis_db = await db_helper.redis_connection()
            try:
                return service.send_otp(conn=conn, cursor=cursor, redis_db=redis_db, request_data=request_data)
            finally:
                await db_helper.close_redis_connection(redis_db=redis_db)
        elif action == "ag_add_comment":
            return service.add_comment(conn=conn, cursor=cursor, request_data=request_data)

        state, state_message, user_info = await func_helper.authorizer(conn=conn, cursor=cursor, request_data=request_data)
        if not state:
            return func_helper.not_auth_return(message=state_message)

        action_map = {
            "ag_add_payment_order": service.add_payment_order,
            "ag_add_consultant": service.add_consultant,
            "ag_add_student": service.add_student,
            "ag_mark_notification_read": service.mark_notification_read,
        }

        handler = action_map.get(action)
        if handler is None:
            return func_helper.not_method_access_return()

        return handler(conn=conn, cursor=cursor, request_data=request_data, user_info=user_info)

    except KeyError as e:
        return await func_helper.key_error_logging("ag_api/insert_request", "insert_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api/insert_request", "insert_api", str(e), method_type)
    finally:
        if conn and cursor:
            await db_helper.close_db_connection(conn=conn, cursor=cursor)


@app.post("/ag_api/select_request")
@api_metrics.monitor_endpoint("ag_api/select_request")
async def select_api(request: Request):
    method_type = "SELECT"
    conn, cursor = None, None

    try:
        data = await request.json()

        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()

        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)

        conn, cursor = await db_helper.db_connection()

        if action == "ag_check_otp":
            redis_db = await db_helper.redis_connection()
            try:
                return service.check_otp(conn=conn, cursor=cursor, redis_db=redis_db, request_data=request_data)
            finally:
                await db_helper.close_redis_connection(redis_db=redis_db)

        if action == "ag_get_comments":
            return service.get_comments(conn=conn, cursor=cursor)

        state, state_message, user_info = await func_helper.authorizer(conn=conn, cursor=cursor, request_data=request_data)
        if not state:
            return func_helper.not_auth_return(message=state_message)

        action_map = {
            "ag_get_dashboard": service.get_dashboard,
            "ag_get_consultants": service.get_consultants,
            "ag_get_students": service.get_students,
            "ag_get_report": service.get_report,
            "ag_get_management_report": service.get_management_report,
            "ag_get_quiz_setting": service.get_quiz_setting,
            "ag_get_quiz_info": service.get_quiz_info,
            "ag_apply_discount": service.apply_discount,
            "ag_get_transactions": service.get_transactions,
            "ag_get_report_data": service.get_report_data,
        }

        handler = action_map.get(action)
        if handler is None:
            return func_helper.not_method_access_return()

        return handler(conn=conn, cursor=cursor, request_data=request_data, user_info=user_info)

    except KeyError as e:
        return await func_helper.key_error_logging("ag_api/select_request", "select_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api/select_request", "select_api", str(e), method_type)
    finally:
        if conn and cursor:
            await db_helper.close_db_connection(conn=conn, cursor=cursor)


@app.post("/ag_api/update_request")
@api_metrics.monitor_endpoint("ag_api/update_request")
async def update_api(request: Request):
    method_type = "UPDATE"
    conn, cursor = None, None

    try:
        data = await request.json()

        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()

        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)

        conn, cursor = await db_helper.db_connection()
        state, state_message, user_info = await func_helper.authorizer(conn=conn, cursor=cursor, request_data=request_data)
        if not state:
            return func_helper.not_auth_return(message=state_message)

        action_map = {
            "ag_change_user_info": service.change_user_info,
            "ag_change_password": service.change_password,
            "ag_change_setting": service.change_setting,
            "ag_change_consultant": service.change_consultant,
            "ag_change_student": service.change_student,
            "ag_change_comment": service.change_comment,
            "ag_change_user_quiz_setting": service.change_user_quiz_setting,
            "ag_change_student_access": service.change_student_access,
        }

        handler = action_map.get(action)
        if handler is None:
            return func_helper.not_method_access_return()

        return handler(conn=conn, cursor=cursor, request_data=request_data, user_info=user_info)

    except KeyError as e:
        return await func_helper.key_error_logging("ag_api/update_request", "update_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api/update_request", "update_api", str(e), method_type)
    finally:
        if conn and cursor:
            await db_helper.close_db_connection(conn=conn, cursor=cursor)


@app.post("/ag_api/delete_request")
@api_metrics.monitor_endpoint("ag_api/delete_request")
async def delete_api(request: Request):
    method_type = "DELETE"
    conn, cursor = None, None

    try:
        data = await request.json()

        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()

        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)

        conn, cursor = await db_helper.db_connection()
        state, state_message, user_info = await func_helper.authorizer(conn=conn, cursor=cursor, request_data=request_data)
        if not state:
            return func_helper.not_auth_return(message=state_message)

        action_map = {
            "ag_remove_token": service.remove_token,
        }

        handler = action_map.get(action)
        if handler is None:
            return func_helper.not_method_access_return()

        return handler(conn=conn, cursor=cursor, request_data=request_data, user_info=user_info)

    except KeyError as e:
        return await func_helper.key_error_logging("ag_api/delete_request", "delete_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api/delete_request", "delete_api", str(e), method_type)
    finally:
        if conn and cursor:
            await db_helper.close_db_connection(conn=conn, cursor=cursor)


@app.post("/ag_api/admin_request")
@api_metrics.monitor_endpoint("ag_api/admin_request")
async def admin_api(request: Request):
    method_type = "ADMIN"
    conn, cursor = None, None

    try:
        data = await request.json()

        token = data.get("token")
        if not func_helper.authorize_admin(token=token):
            return func_helper.not_auth_return(message="شما به این سرویس دسترسی ندارید.", method_type=method_type)

        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()

        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)

        conn, cursor = await db_helper.db_connection()

        action_map = {
            "ag_change_capacity": service.admin_change_capacity,
            "ag_get_user_info": service.admin_get_user_info,
            "ag_check_student_quiz_answer": service.admin_check_student_quiz_answer,
        }

        handler = action_map.get(action)
        if handler is None:
            return func_helper.not_method_access_return()

        return handler(conn=conn, cursor=cursor, request_data=request_data)

    except KeyError as e:
        return await func_helper.key_error_logging("ag_api/admin_request", "admin_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api/admin_request", "admin_api", str(e), method_type)
    finally:
        if conn and cursor:
            await db_helper.close_db_connection(conn=conn, cursor=cursor)


@app.post("/ag_api/update_user_file_image")
@api_metrics.monitor_endpoint("ag_api/update_user_file_image")
async def update_user_file_image(request: Request):
    method_type = "UPDATE"
    conn, cursor = None, None
    try:
        data = await request.json()
        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()
        if action not in ["ag_change_user_info", "ag_change_user_image"]:
            return func_helper.not_method_access_return()

        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)

        user_id = request_data["user_id"]
        token = request_data["token"]
        conn, cursor = await db_helper.db_connection()
        state, state_message, user_info = await func_helper.authorizer(conn=conn, cursor=cursor,
                                                      request_data={"user_id": int(user_id), "token": token})
        if not state:
            return func_helper.not_auth_return(message=state_message)
        return service.change_user_info(conn=conn, cursor=cursor, request_data=request_data, user_info=user_info)
    except KeyError as e:
        return await func_helper.key_error_logging("ag_api", "update_user_file_image", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api", "update_user_file_image", str(e), method_type)
    finally:
        if conn and cursor:
            await db_helper.close_db_connection(conn=conn, cursor=cursor)


@app.post("/ag_api/update_user_voice")
@api_metrics.monitor_endpoint("ag_api/update_user_voice")
async def update_user_voice(
        voice: UploadFile = Form(...),
        description: str = Form(...),
        quiz_id: int = Form(...),
        user_id: int = Form(...),
        phone: str = Form(...),
        setting_id: int = Form(...),
        last_voice: str = Form(...),
        role: str = Form(...),
        token: str = Form(...),
):
    method_type = "UPDATE"
    conn, cursor = None, None
    try:
        conn, cursor = await db_helper.db_connection()
        state, state_message, user_info = await func_helper.authorizer(conn=conn, cursor=cursor,
                                                      request_data={"user_id": int(user_id), "token": token})
        if not state:
            return func_helper.not_auth_return(message=state_message)
        generate_random_name = func_helper.get_tracking_code()
        new_file_name = generate_random_name + "." + voice.filename.split(".")[1]
        voice.filename = new_file_name
        file_path = os.path.join(VOICES_DIR, voice.filename)
        last_path = os.path.join(VOICES_DIR, last_voice)
        if os.path.exists(last_path):
            os.remove(last_path)
        else:
            print("The file does not exist")
        data = {"phone": phone, "setting_id": setting_id, "description": description, "quiz_id": quiz_id,
                "user_id": int(user_id), "voice": voice.filename}
        with open(file_path, "wb") as file_object:
            file_object.write(voice.file.read())
        if role == "ins":
            tracking_token, response_data, response_message = institute_service.change_user_voice(
                conn=conn, cursor=cursor, request_data=data, user_info=user_info
            )
            return service.service_response(method_type, tracking_token, response_data, response_message)
        elif role == "sch":
            tracking_token, response_data, response_message = school_service.change_user_voice(
                conn=conn, cursor=cursor, request_data=data, user_info=user_info
            )
            return service.service_response(method_type, tracking_token, response_data, response_message)
        elif role == "ocon":
            tracking_token, response_data, response_message = owner_consultant_service.change_user_voice(
                conn=conn, cursor=cursor, request_data=data, user_info=user_info
            )
            return service.service_response(method_type, tracking_token, response_data, response_message)
        else:
            return {"status": 200, "tracking_code": None, "method_type": method_type,
                    "error": "شما به این سرویس دسترسی ندارید."}
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api", "update_user_voice", str(e), method_type)
    finally:
        if conn and cursor:
            await db_helper.close_db_connection(conn=conn, cursor=cursor)


@app.get("/ags_api/get_ins_pic/{filename}")
@app.get("/ag_api/get_ins_pic/{filename}")
async def get_ins_pic(filename: str):
    file_path = os.path.join(INS_PIC_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")


def _report_error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"status": status_code, "tracking_code": None, "method_type": "GET", "error": message},
    )


async def _get_report_pdf(
    phone: str,
    kind: str,
    expected_kind: str,
    expected_quiz_count: int,
    report_filename: str,
    log_endpoint: str,
    log_func_name: str,
):
    try:
        kind = kind.upper()
        if kind != expected_kind:
            return _report_error(321, "درخواست برای دریافت کارنامه نامعتبر است.")

        with session_scope() as session:
            report_status = get_report_download_status(
                session=session,
                phone=phone,
                kind=kind,
                expected_quiz_count=expected_quiz_count,
            )

        status = report_status["status"]
        if status == "student_not_found":
            return _report_error(404, "دانش‌آموزی با این شماره تلفن یافت نشد.")
        if status == "access_denied":
            return _report_error(403, "دانش‌آموز دسترسی لازم برای دریافت این کارنامه را ندارد.")
        if status == "quiz_incomplete":
            return _report_error(321, "در حال حاضر آزمون‌های دانش‌آموز به پایان نرسیده است.")
        if status == "generating":
            return _report_error(323, "کارنامه در حال تولید است.")
        if status == "queued":
            return _report_error(324, "کارنامه در صف تولید است.")

        folder_check = os.path.join(REPORTS_DIR, phone)
        file_path = os.path.join(folder_check, report_filename)
        if os.path.exists(file_path):
            return FileResponse(file_path, filename=report_filename)
        if os.path.exists(folder_check):
            return _report_error(322, "کارنامه‌ها درحال آماده سازی می‌باشد.")
        return _report_error(404, "File not found")
    except Exception as e:
        await func_helper.exception_error_logging(log_endpoint, log_func_name, str(e), "GET")
        return _report_error(404, "File not found")


@app.get("/ags_api/get_ag_first_pdf/{phone}/{kind}")
@app.get("/ag_api/get_ag_first_pdf/{phone}/{kind}")
async def get_ag_first_pdf(phone: str, kind: str):
    return await _get_report_pdf(phone, kind, "AG", 7, "Report1.pdf", "ag_api/get_report1", "get_report1")


@app.get("/ags_api/get_ag_second_pdf/{phone}/{kind}")
@app.get("/ag_api/get_ag_second_pdf/{phone}/{kind}")
async def get_ag_second_pdf(phone: str, kind: str):
    return await _get_report_pdf(phone, kind, "AG", 7, "Report2.pdf", "ag_api/get_report2", "get_report2")


@app.get("/ags_api/get_scl_first_pdf/{phone}/{kind}")
@app.get("/ag_api/get_scl_first_pdf/{phone}/{kind}")
async def get_scl_first_pdf(phone: str, kind: str):
    return await _get_report_pdf(phone, kind, "SCL", 4, "Report3.pdf", "ag_api/get_report3", "get_report3")


@app.get("/ags_api/get_scl_second_pdf/{phone}/{kind}")
@app.get("/ag_api/get_scl_second_pdf/{phone}/{kind}")
async def get_scl_second_pdf(phone: str, kind: str):
    return await _get_report_pdf(phone, kind, "SCL", 4, "Report4.pdf", "ag_api/get_report4", "get_report4")


@app.get("/ags_api/get_scl_third_pdf/{phone}/{kind}")
@app.get("/ag_api/get_scl_third_pdf/{phone}/{kind}")
async def get_scl_third_pdf(phone: str, kind: str):
    return await _get_report_pdf(phone, kind, "SCL", 4, "Report5.pdf", "ag_api/get_report4", "get_report4")


@app.get("/ags_api/get_default/{reportname}")
@app.get("/ag_api/get_default/{reportname}")
async def get_first_default_pdf(reportname: str):
    file_path = os.path.join(DEFAULT_REPORT_PATH, reportname)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename="Report.pdf")
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/ags_api/get_pic/{filename}")
@app.get("/ag_api/get_pic/{filename}")
async def get_pic(filename: str):
    file_path = os.path.join(PICS_INFO_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/ags_api/get_pic_scl/{filename}")
@app.get("/ag_api/get_pic_scl/{filename}")
async def get_pic_scl(filename: str):
    file_path = os.path.join(PICS_WORD_SCL_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/ags_api/get_pic_info/report/{filename}")
@app.get("/ag_api/get_pic_info/report/{filename}")
async def get_pic_info_report(filename: str):
    file_path = os.path.join(PICS_REPORT_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/ags_api/get_pic_info/quiz/{filename}")
@app.get("/ag_api/get_pic_info/quiz/{filename}")
async def get_pic_info(filename: str):
    file_path = os.path.join(PICS_QUIZ_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/ags_api/get_quiz_pic/{filename}")
@app.get("/ag_api/get_quiz_pic/{filename}")
async def get_quiz_pic(filename: str):
    file_path = os.path.join(QUIZ_PIC_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/ags_api/get_voice/{filename}")
@app.get("/ag_api/get_voice/{filename}")
async def get_voice(filename: str):
    file_path = os.path.join(VOICES_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")

@app.get("/ags_api/majors")
@app.get("/ag_api/majors")
async def get_majors():
    return {"majors": static_data.MAJORS}


@app.get("/ags_api/majors/{major_id}/categories")
@app.get("/ag_api/majors/{major_id}/categories")
async def get_major_categories(major_id: int):
    major_item = next((item for item in static_data.MAJORS if item["id"] == major_id), None)
    if not major_item:
        raise HTTPException(status_code=404, detail="Major not found")

    categories = [item for item in static_data.CATEGORY if item.get("number") == major_item["id"]]
    return {"major": major_item, "categories": categories}


@app.get("/ags_api/fields/{field_id}")
@app.get("/ag_api/fields/{field_id}")
async def get_field(field_id: int):
    field_item = next((item for item in static_data.FIELDS if item["id"] == field_id), None)
    if not field_item:
        raise HTTPException(status_code=404, detail="Field not found")

    category_items = [item for item in static_data.CATEGORY if item.get("id") == field_id]
    field_item_with_categories = field_item.copy()

    if category_items:
        field_item_with_categories["categories"] = category_items
        first_category = category_items[0]
        for key in ["a1", "a2", "a3", "a4", "a5", "a6"]:
            if key in first_category:
                field_item_with_categories[key] = first_category[key]
    else:
        for key in ["a1", "a2", "a3", "a4", "a5", "a6"]:
            field_item_with_categories[key] = None

    return {"field": field_item_with_categories}



@app.get("/ags_api/get_pic_info/field/{filename}")
@app.get("/ag_api/get_pic_info/field/{filename}")
async def get_pic_info_field(filename: str):
    file_path = os.path.join(PICS_FIELD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")
