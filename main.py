import os
import time
import json
from functools import wraps

from fastapi import FastAPI, Request, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse, Response, JSONResponse
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

import helper.db.db_helper as db_helper
import helper.func_helper as func_helper
import services.institute.institute_service as institute_service
import services.owner_consultant.owner_consultant_service as owner_consultant_service
import services.school.school_service as school_service
import services.service as service
from config import (
    DEVELOP_TOKEN,
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

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------

REQUEST_COUNT = Counter(
    "ag_api_requests_total",
    "Total count of requests by endpoint and method_type",
    ["endpoint", "method_type", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "ag_api_request_duration_seconds",
    "Histogram of request processing time by endpoint and method_type",
    ["endpoint", "method_type", "status_code"],
)

REQUEST_ERRORS = Counter(
    "ag_api_request_errors_total",
    "Count of errors by endpoint and method_type",
    ["endpoint", "method_type"],
)

HTTP_REQUESTS_TOTAL = Counter(
    "ag_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_LATENCY_SECONDS = Histogram(
    "ag_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path", "status_code"],
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "ag_http_requests_in_progress",
    "Number of HTTP requests in progress",
    ["method", "path"],
)


def monitor_endpoint(endpoint_name: str):
    """
    Decorator to measure latency and basic counters per endpoint.

    This keeps the existing behaviour (driven by request.json()['method_type'])
    but extends the metrics with response status_code for richer dashboards.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            method_type = "UNKNOWN"
            status_code = "200"
            try:
                request: Request | None = kwargs.get("request")
                if request:
                    try:
                        body = await request.json()
                        method_type = body.get("method_type", "UNKNOWN")
                    except Exception as e:
                        print(e)

                response = await func(*args, **kwargs)

                try:
                    status_code = str(getattr(response, "status_code", 200))
                except Exception as e:
                    print(e)
                    status_code = "200"

                REQUEST_COUNT.labels(
                    endpoint=endpoint_name,
                    method_type=method_type,
                    status_code=status_code,
                ).inc()

                return response
            except Exception:
                REQUEST_ERRORS.labels(
                    endpoint=endpoint_name,
                    method_type=method_type,
                ).inc()
                status_code = "500"
                raise
            finally:
                elapsed = time.perf_counter() - start_time
                REQUEST_LATENCY.labels(
                    endpoint=endpoint_name,
                    method_type=method_type,
                    status_code=status_code,
                ).observe(elapsed)

        return wrapper

    return decorator


@app.middleware("http")
async def prometheus_http_middleware(request: Request, call_next):
    """
    Lightweight middleware that exposes generic HTTP-level metrics.

    It complements the explicit @monitor_endpoint decorator and covers:
    - all HTTP methods
    - all paths (except /ag_api/metrics and docs)
    - in-progress requests
    - latency and status codes
    """

    path = request.url.path

    # Avoid self-scraping and skip docs by default
    if path in {"/ag_api/metrics", "/docs", "/redoc", "/openapi.json"}:
        return await call_next(request)

    method = request.method
    labels_in_progress = {"method": method, "path": path}
    HTTP_REQUESTS_IN_PROGRESS.labels(**labels_in_progress).inc()

    start_time = time.perf_counter()
    status_code = "500"

    try:
        response = await call_next(request)
        status_code = str(getattr(response, "status_code", 200))
        return response
    except Exception:
        # Exceptions are turned into 500s by FastAPI; we still want to count them
        status_code = "500"
        raise
    finally:
        elapsed = time.perf_counter() - start_time
        HTTP_REQUESTS_IN_PROGRESS.labels(**labels_in_progress).dec()

        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            path=path,
            status_code=status_code,
        ).inc()

        HTTP_REQUEST_LATENCY_SECONDS.labels(
            method=method,
            path=path,
            status_code=status_code,
        ).observe(elapsed)


def check_develop_token(token):
    if token and token == DEVELOP_TOKEN:
        return True
    return False


@app.get("/ag_api/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/ag_api/health")
async def health_check(request: Request):
    """
    Health check endpoint for monitoring and load balancers.

    Returns:
        JSON response with health status, timestamp, and instance information.
    """
    import os
    from datetime import datetime

    instance_name = os.getenv("INSTANCE_NAME", "unknown")
    port = os.getenv("PORT", "unknown")

    # Basic health check - can be extended to check database, redis, etc.
    try:
        # Quick database connection test
        conn, cursor = await func_helper.db_connection()
        await func_helper.close_db_connection(conn, cursor)
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "instance": instance_name,
        "port": port,
        "database": db_status,
        "version": "1.0.0"
    }


@app.post("/ag_api/signin")
@monitor_endpoint("signin_api")
async def signin_api(request: Request):
    method_type = "SIGNIN"
    conn, cursor = None, None

    try:
        request_data = await request.json()

        action = request_data.get("method_type")
        if not action:
            return func_helper.not_method_access_return()

        data = request_data.get("data")
        if data is None:
            return func_helper.not_data_return(method_type=method_type)

        if action != "signin":
            return func_helper.not_method_access_return()

        conn, cursor = await func_helper.db_connection()

        return service.signin(conn=conn, cursor=cursor, request_data=data)

    except KeyError as e:
        return await func_helper.key_error_logging("ag_api/signin", "signin_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api/signin", "signin_api", str(e), method_type)
    finally:
        if conn and cursor:
            await func_helper.close_db_connection(conn=conn, cursor=cursor)


@app.post("/ag_api/insert_request")
@monitor_endpoint("insert_request")
async def insert_api(request: Request):
    method_type = "INSERT"
    conn, cursor = None, None

    try:
        request_data = await request.json()

        action = request_data.get("method_type")
        if not action:
            return func_helper.not_method_access_return()

        data = request_data.get("data")
        if data is None:
            return func_helper.not_data_return(method_type=method_type)

        conn, cursor = await func_helper.db_connection()

        if action == "signup":
            redis_db = await func_helper.redis_connection()
            try:
                return service.signup(conn=conn, cursor=cursor, redis_db=redis_db, request_data=data)
            finally:
                await func_helper.close_redis_connection(redis_db=redis_db)
        elif action == "send_otp":
            redis_db = await func_helper.redis_connection()
            try:
                return service.send_otp(conn=conn, cursor=cursor, redis_db=redis_db, request_data=data)
            finally:
                await func_helper.close_redis_connection(redis_db=redis_db)
        elif action == "insert_comment":
            return service.insert_comment(conn=conn, cursor=cursor, request_data=data)

        state, state_message, info = await func_helper.authorizer(conn=conn, cursor=cursor, request_data=data)
        if not state:
            return func_helper.not_auth_return(message=state_message)

        action_map = {
            "insert_order_payment": service.insert_order_payment,
            "insert_consultant": service.insert_consultant,
            "insert_student": service.insert_student,
        }

        handler = action_map.get(action)
        if handler is None:
            return func_helper.not_method_access_return()

        return handler(conn=conn, cursor=cursor, request_data=data, info=info)

    except KeyError as e:
        return await func_helper.key_error_logging("ag_api/insert_request", "insert_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api/insert_request", "insert_api", str(e), method_type)
    finally:
        if conn and cursor:
            await func_helper.close_db_connection(conn=conn, cursor=cursor)


@app.post("/ag_api/select_request")
@monitor_endpoint("select_request")
async def select_api(request: Request):
    method_type = "SELECT"
    conn, cursor = None, None

    try:
        request_data = await request.json()

        action = request_data.get("method_type")
        if not action:
            return func_helper.not_method_access_return()

        data = request_data.get("data")
        if data is None:
            return func_helper.not_data_return(method_type=method_type)

        conn, cursor = await func_helper.db_connection()

        if action == "check_otp":
            redis_db = await func_helper.redis_connection()
            try:
                return service.check_otp(conn=conn, cursor=cursor, redis_db=redis_db, request_data=data)
            finally:
                await func_helper.close_redis_connection(redis_db=redis_db)

        if action == "select_comments":
            return service.select_comments(conn=conn, cursor=cursor)

        state, state_message, info = await func_helper.authorizer(conn=conn, cursor=cursor, request_data=data)
        if not state:
            return func_helper.not_auth_return(message=state_message)

        action_map = {
            "select_dashboard": service.select_dashboard,
            "select_consultants": service.select_consultants,
            "select_students": service.select_students,
            "select_report": service.select_report,
            "select_management_report": service.select_management_report,
            "select_quiz_setting": service.select_quiz_setting,
            "select_quiz_info": service.select_quiz_info,
            "apply_discount": service.apply_discount,
            "select_users_transactions": service.get_users_transactions,
            "select_report_data": service.select_report_data,
        }

        handler = action_map.get(action)
        if handler is None:
            return func_helper.not_method_access_return()

        return handler(conn=conn, cursor=cursor, request_data=data, info=info)

    except KeyError as e:
        return await func_helper.key_error_logging("ag_api/select_request", "select_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api/select_request", "select_api", str(e), method_type)
    finally:
        if conn and cursor:
            await func_helper.close_db_connection(conn=conn, cursor=cursor)


@app.post("/ag_api/update_request")
@monitor_endpoint("update_request")
async def update_api(request: Request):
    method_type = "UPDATE"
    conn, cursor = None, None

    try:
        request_data = await request.json()

        action = request_data.get("method_type")
        if not action:
            return func_helper.not_method_access_return()

        data = request_data.get("data")
        if data is None:
            return func_helper.not_data_return(method_type=method_type)

        conn, cursor = await func_helper.db_connection()
        state, state_message, info = await func_helper.authorizer(conn=conn, cursor=cursor, request_data=data)
        if not state:
            return func_helper.not_auth_return(message=state_message)

        action_map = {
            "update_user": service.update_user,
            "update_password": service.update_password,
            "update_setting": service.update_setting,
            "update_consultant": service.update_consultant,
            "update_student": service.update_student,
            "update_comment": service.make_comment,
            "update_user_quiz_setting": service.update_user_quiz_setting,
            "update_student_access": service.update_student_access,
        }

        handler = action_map.get(action)
        if handler is None:
            return func_helper.not_method_access_return()

        return handler(conn=conn, cursor=cursor, request_data=data, info=info)

    except KeyError as e:
        return await func_helper.key_error_logging("ag_api/update_request", "update_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api/update_request", "update_api", str(e), method_type)
    finally:
        if conn and cursor:
            await func_helper.close_db_connection(conn=conn, cursor=cursor)


@app.post("/ag_api/delete_request")
@monitor_endpoint("delete_request")
async def delete_api(request: Request):
    method_type = "DELETE"
    conn, cursor = None, None

    try:
        request_data = await request.json()

        action = request_data.get("method_type")
        if not action:
            return func_helper.not_method_access_return()

        data = request_data.get("data")
        if data is None:
            return func_helper.not_data_return(method_type=method_type)

        conn, cursor = await func_helper.db_connection()
        state, state_message, info = await func_helper.authorizer(conn=conn, cursor=cursor, request_data=data)
        if not state:
            return func_helper.not_auth_return(message=state_message)

        action_map = {
            "delete_token": service.delete_token,
        }

        handler = action_map.get(action)
        if handler is None:
            return func_helper.not_method_access_return()

        return handler(conn=conn, cursor=cursor, request_data=data, info=info)

    except KeyError as e:
        return await func_helper.key_error_logging("ag_api/delete_request", "delete_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api/delete_request", "delete_api", str(e), method_type)
    finally:
        if conn and cursor:
            await func_helper.close_db_connection(conn=conn, cursor=cursor)


@app.post("/ag_api/admin_request")
@monitor_endpoint("admin_request")
async def admin_api(request: Request):
    method_type = "ADMIN"
    conn, cursor = None, None

    try:
        request_data = await request.json()

        # Check develop token
        token = request_data.get("token")
        if not check_develop_token(token):
            return {"status": 200, "tracking_code": None, "method_type": method_type,
                    "error": "شما به این سرویس دسترسی ندارید."}

        action = request_data.get("method_type")
        if not action:
            return func_helper.not_method_access_return()

        data = request_data.get("data")
        if data is None:
            return func_helper.not_data_return(method_type=method_type)

        conn, cursor = await func_helper.db_connection()

        action_map = {
            "update_capacity": service.admin_update_capacity,
            "get_user_info": service.admin_get_user_info,
            "check_student_quiz_answer": service.admin_check_student_quiz_answer,
        }

        handler = action_map.get(action)
        if handler is None:
            return func_helper.not_method_access_return()

        return handler(conn=conn, cursor=cursor, request_data=data)

    except KeyError as e:
        return await func_helper.key_error_logging("ag_api/admin_request", "admin_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api/admin_request", "admin_api", str(e), method_type)
    finally:
        if conn and cursor:
            await func_helper.close_db_connection(conn=conn, cursor=cursor)


@app.post("/ag_api/update_user_file_image")
async def update_user_file_image(request: Request):
    method_type = "UPDATE"
    conn, cursor = None, None
    try:
        request_data = await request.json()
        data = request_data.get("data", request_data)
        user_id = data["user_id"]
        token = data["token"]
        conn, cursor = await func_helper.db_connection()
        state, state_message, info = await func_helper.authorizer(conn=conn, cursor=cursor,
                                                      request_data={"user_id": int(user_id), "token": token})
        if not state:
            return func_helper.not_auth_return(message=state_message)
        return service.update_user(conn=conn, cursor=cursor, request_data=data, info=info)
    except KeyError as e:
        return await func_helper.key_error_logging("ag_api", "update_user_file_image", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api", "update_user_file_image", str(e), method_type)
    finally:
        if conn and cursor:
            await func_helper.close_db_connection(conn=conn, cursor=cursor)


@app.post("/ag_api/update_user_voice")
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
        conn, cursor = await func_helper.db_connection()
        state, state_message, info = await func_helper.authorizer(conn=conn, cursor=cursor,
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
            res_request = institute_service.update_user_ins_voice(conn=conn, cursor=cursor, request_data=data, info=info)
            return res_request
        elif role == "sch":
            res_request = school_service.update_user_sch_voice(conn=conn, cursor=cursor, request_data=data, info=info)
            return res_request
        elif role == "wCon":
            res_request = owner_consultant_service.update_user_wcon_voice(conn=conn, cursor=cursor, request_data=data, info=info)
            return res_request
        else:
            return {"status": 200, "tracking_code": None, "method_type": method_type,
                    "error": "شما به این سرویس دسترسی ندارید."}
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api", "update_user_voice", str(e), method_type)
    finally:
        if conn and cursor:
            await func_helper.close_db_connection(conn=conn, cursor=cursor)


@app.get("/ag_api/get_ins_pic/{filename}")
async def get_ins_pic(filename: str):
    file_path = os.path.join(INS_PIC_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/ag_api/get_ag_first_pdf/{phone}/{kind}")
async def get_ag_first_pdf(phone: str, kind: str):
    conn, cursor = None, None

    try:
        if kind.upper() != "AG":
            return JSONResponse(
                status_code=321,
                content={"status": 321, "tracking_code": None, "method_type": "GET",
                         "error": "درخواست برای دریافت کارنامه نامعتبر است."}
            )
        conn, cursor = await func_helper.db_connection()
        # Check the access of the student for this kind - should have permission = 1
        query = 'SELECT user_id, access FROM stu WHERE phone = ?'
        stu = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)

        if not stu:
            return JSONResponse(
                status_code=404,
                content={"status": 404, "tracking_code": None, "method_type": "GET",
                         "error": "دانش‌آموزی با این شماره تلفن یافت نشد."}
            )

        # Parse access field to check permission
        raw_access = getattr(stu, "access", None) or "{}"
        try:
            access_data = json.loads(raw_access) if isinstance(raw_access, str) else (raw_access or {})
        except (json.JSONDecodeError, TypeError):
            access_data = {}

        # Check permission for the given kind
        package_info = access_data.get(kind.upper(), {})
        permission = 0
        if isinstance(package_info, dict):
            permission = int(package_info.get("permission") or 0)
        elif isinstance(package_info, bool):
            permission = 1 if package_info else 0
        elif isinstance(package_info, (int, float, str)):
            try:
                permission = int(package_info) if str(package_info).strip() != "" else 0
            except ValueError:
                permission = 0

        if permission != 1:
            return JSONResponse(
                status_code=403,
                content={"status": 403, "tracking_code": None, "method_type": "GET",
                         "error": "دانش‌آموز دسترسی لازم برای دریافت این کارنامه را ندارد."}
            )

        # After the count of the quiz answered, check that all answers should be completed (state = 2)
        query_quiz = (
            'SELECT state, quiz_id FROM quiz_answer '
            'WHERE user_id = ? AND quiz_kind = ? ORDER BY quiz_id ASC'
        )
        res_quiz = db_helper.search_allin_table(
            conn=conn,
            cursor=cursor,
            query=query_quiz,
            field=(stu.user_id, kind.upper())
        )
        if len(res_quiz) < 7:
            return JSONResponse(
                status_code=321,
                content={"status": 321, "tracking_code": None, "method_type": "GET",
                         "error": "در حال حاضر آزمون‌های دانش‌آموز به پایان نرسیده است."}
            )

        # Check that all quiz answers are completed (state = 2)
        for quiz in res_quiz:
            quiz_state = getattr(quiz, "state", None)
            if quiz_state != 2:
                return JSONResponse(
                    status_code=321,
                    content={"status": 321, "tracking_code": None, "method_type": "GET",
                             "error": "در حال حاضر آزمون‌های دانش‌آموز به پایان نرسیده است."}
                )

        # Proceed with checking report status
        query = 'SELECT status FROM redis_log WHERE user_id = ? and kind = ?'
        res_queue = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=(stu.user_id, kind.upper()))
        # if not res_queue:
        #     return JSONResponse(
        #         status_code=404,
        #         content={"status": 404, "tracking_code": None, "method_type": "GET",
        #                  "error": "مشکلی در سامانه پیش آماده با پشتیبانی ارتباط بگیرید."}
        #     )
        if not res_queue:
            pass
        elif res_queue.status == 1:
            return JSONResponse(
                status_code=323,
                content={"status": 323, "tracking_code": None, "method_type": "GET",
                         "error": "کارنامه در حال تولید است."}
            )
        elif res_queue.status == 0:
            return JSONResponse(
                status_code=324,
                content={"status": 324, "tracking_code": None, "method_type": "GET",
                         "error": "کارنامه در صف تولید است."}
            )
        folder_check = os.path.join(REPORTS_DIR, phone)
        file_path = os.path.join(REPORTS_DIR, phone, 'Report1.pdf')
        if os.path.exists(file_path):
            return FileResponse(file_path, filename="Report1.pdf")
        else:
            if os.path.exists(folder_check):
                return JSONResponse(
                    status_code=322,
                    content={"status": 322, "tracking_code": None, "method_type": "GET",
                             "error": "کارنامه‌ها درحال آماده سازی می‌باشد."}
                )
            else:
                return JSONResponse(
                    status_code=404,
                    content={"status": 404, "tracking_code": None, "method_type": "GET", "error": "File not found"}
                )

    except Exception as e:
        await func_helper.exception_error_logging("ag_api/get_report1", "get_report1", str(e), "GET")
        return JSONResponse(
            status_code=404,
            content={"status": 404, "tracking_code": None, "method_type": "GET", "error": "File not found"}
        )

    finally:
        if conn and cursor:
            await func_helper.close_db_connection(conn=conn, cursor=cursor)


@app.get("/ag_api/get_ag_second_pdf/{phone}/{kind}")
async def get_ag_second_pdf(phone: str, kind: str):
    conn, cursor = None, None

    try:
        if kind.upper() != "AG":
            return JSONResponse(
                status_code=321,
                content={"status": 321, "tracking_code": None, "method_type": "GET",
                         "error": "درخواست برای دریافت کارنامه نامعتبر است."}
            )
        conn, cursor = await func_helper.db_connection()
        # Check the access of the student for this kind - should have permission = 1
        query = 'SELECT user_id, access FROM stu WHERE phone = ?'
        stu = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)

        if not stu:
            return JSONResponse(
                status_code=404,
                content={"status": 404, "tracking_code": None, "method_type": "GET",
                         "error": "دانش‌آموزی با این شماره تلفن یافت نشد."}
            )

        # Parse access field to check permission
        raw_access = getattr(stu, "access", None) or "{}"
        try:
            access_data = json.loads(raw_access) if isinstance(raw_access, str) else (raw_access or {})
        except (json.JSONDecodeError, TypeError):
            access_data = {}

        # Check permission for the given kind
        package_info = access_data.get(kind.upper(), {})
        permission = 0
        if isinstance(package_info, dict):
            permission = int(package_info.get("permission") or 0)
        elif isinstance(package_info, bool):
            permission = 1 if package_info else 0
        elif isinstance(package_info, (int, float, str)):
            try:
                permission = int(package_info) if str(package_info).strip() != "" else 0
            except ValueError:
                permission = 0

        if permission != 1:
            return JSONResponse(
                status_code=403,
                content={"status": 403, "tracking_code": None, "method_type": "GET",
                         "error": "دانش‌آموز دسترسی لازم برای دریافت این کارنامه را ندارد."}
            )

        # After the count of the quiz answered, check that all answers should be completed (state = 2)
        query_quiz = (
            'SELECT state, quiz_id FROM quiz_answer '
            'WHERE user_id = ? AND quiz_kind = ? ORDER BY quiz_id ASC'
        )
        res_quiz = db_helper.search_allin_table(
            conn=conn,
            cursor=cursor,
            query=query_quiz,
            field=(stu.user_id, kind.upper())
        )
        if len(res_quiz) < 7:
            return JSONResponse(
                status_code=321,
                content={"status": 321, "tracking_code": None, "method_type": "GET",
                         "error": "در حال حاضر آزمون‌های دانش‌آموز به پایان نرسیده است."}
            )

        # Check that all quiz answers are completed (state = 2)
        for quiz in res_quiz:
            quiz_state = getattr(quiz, "state", None)
            if quiz_state != 2:
                return JSONResponse(
                    status_code=321,
                    content={"status": 321, "tracking_code": None, "method_type": "GET",
                             "error": "در حال حاضر آزمون‌های دانش‌آموز به پایان نرسیده است."}
                )

        # Proceed with checking report status
        query = 'SELECT status FROM redis_log WHERE user_id = ? and kind = ?'
        res_queue = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=(stu.user_id, kind.upper()))
        # if not res_queue:
        #     return JSONResponse(
        #         status_code=404,
        #         content={"status": 404, "tracking_code": None, "method_type": "GET",
        #                  "error": "مشکلی در سامانه پیش آماده با پشتیبانی ارتباط بگیرید."}
        #     )
        if not res_queue:
            pass
        elif res_queue.status == 1:
            return JSONResponse(
                status_code=323,
                content={"status": 323, "tracking_code": None, "method_type": "GET",
                         "error": "کارنامه در حال تولید است."}
            )
        elif res_queue.status == 0:
            return JSONResponse(
                status_code=324,
                content={"status": 324, "tracking_code": None, "method_type": "GET",
                         "error": "کارنامه در صف تولید است."}
            )
        folder_check = os.path.join(REPORTS_DIR, phone)
        file_path = os.path.join(REPORTS_DIR, phone, 'Report2.pdf')
        if os.path.exists(file_path):
            return FileResponse(file_path, filename="Report2.pdf")
        else:
            if os.path.exists(folder_check):
                return JSONResponse(
                    status_code=322,
                    content={"status": 322, "tracking_code": None, "method_type": "GET",
                             "error": "کارنامه‌ها درحال آماده سازی می‌باشد."}
                )
            else:
                return JSONResponse(
                    status_code=404,
                    content={"status": 404, "tracking_code": None, "method_type": "GET", "error": "File not found"}
                )

    except Exception as e:
        await func_helper.exception_error_logging("ag_api/get_report2", "get_report2", str(e), "GET")
        return JSONResponse(
            status_code=404,
            content={"status": 404, "tracking_code": None, "method_type": "GET", "error": "File not found"}
        )

    finally:
        if conn and cursor:
            await func_helper.close_db_connection(conn=conn, cursor=cursor)


@app.get("/ag_api/get_scl_first_pdf/{phone}/{kind}")
async def get_scl_first_pdf(phone: str, kind: str):
    conn, cursor = None, None

    try:
        if kind.upper() != "SCL":
            return JSONResponse(
                status_code=321,
                content={"status": 321, "tracking_code": None, "method_type": "GET",
                         "error": "درخواست برای دریافت کارنامه نامعتبر است."}
            )
        conn, cursor = await func_helper.db_connection()
        # Check the access of the student for this kind - should have permission = 1
        query = 'SELECT user_id, access FROM stu WHERE phone = ?'
        stu = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)

        if not stu:
            return JSONResponse(
                status_code=404,
                content={"status": 404, "tracking_code": None, "method_type": "GET",
                         "error": "دانش‌آموزی با این شماره تلفن یافت نشد."}
            )

        # Parse access field to check permission
        raw_access = getattr(stu, "access", None) or "{}"
        try:
            access_data = json.loads(raw_access) if isinstance(raw_access, str) else (raw_access or {})
        except (json.JSONDecodeError, TypeError):
            access_data = {}

        # Check permission for the given kind
        package_info = access_data.get(kind.upper(), {})
        permission = 0
        if isinstance(package_info, dict):
            permission = int(package_info.get("permission") or 0)
        elif isinstance(package_info, bool):
            permission = 1 if package_info else 0
        elif isinstance(package_info, (int, float, str)):
            try:
                permission = int(package_info) if str(package_info).strip() != "" else 0
            except ValueError:
                permission = 0

        if permission != 1:
            return JSONResponse(
                status_code=403,
                content={"status": 403, "tracking_code": None, "method_type": "GET",
                         "error": "دانش‌آموز دسترسی لازم برای دریافت این کارنامه را ندارد."}
            )

        # After the count of the quiz answered, check that all answers should be completed (state = 2)
        query_quiz = (
            'SELECT state, quiz_id FROM quiz_answer '
            'WHERE user_id = ? AND quiz_kind = ? ORDER BY quiz_id ASC'
        )
        res_quiz = db_helper.search_allin_table(
            conn=conn,
            cursor=cursor,
            query=query_quiz,
            field=(stu.user_id, kind.upper())
        )
        if len(res_quiz) < 4:
            return JSONResponse(
                status_code=321,
                content={"status": 321, "tracking_code": None, "method_type": "GET",
                         "error": "در حال حاضر آزمون‌های دانش‌آموز به پایان نرسیده است."}
            )

        # Check that all quiz answers are completed (state = 2)
        for quiz in res_quiz:
            quiz_state = getattr(quiz, "state", None)
            if quiz_state != 2:
                return JSONResponse(
                    status_code=321,
                    content={"status": 321, "tracking_code": None, "method_type": "GET",
                             "error": "در حال حاضر آزمون‌های دانش‌آموز به پایان نرسیده است."}
                )

        # Proceed with checking report status
        query = 'SELECT status FROM redis_log WHERE user_id = ? and kind = ?'
        res_queue = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=(stu.user_id, kind.upper()))
        # if not res_queue:
        #     return JSONResponse(
        #         status_code=404,
        #         content={"status": 404, "tracking_code": None, "method_type": "GET",
        #                  "error": "مشکلی در سامانه پیش آماده با پشتیبانی ارتباط بگیرید."}
        #     )
        if not res_queue:
            pass
        elif res_queue.status == 1:
            return JSONResponse(
                status_code=323,
                content={"status": 323, "tracking_code": None, "method_type": "GET",
                         "error": "کارنامه در حال تولید است."}
            )
        elif res_queue.status == 0:
            return JSONResponse(
                status_code=324,
                content={"status": 324, "tracking_code": None, "method_type": "GET",
                         "error": "کارنامه در صف تولید است."}
            )
        folder_check = os.path.join(REPORTS_DIR, phone)
        file_path = os.path.join(REPORTS_DIR, phone, 'Report3.pdf')
        if os.path.exists(file_path):
            return FileResponse(file_path, filename="Report3.pdf")
        else:
            if os.path.exists(folder_check):
                return JSONResponse(
                    status_code=322,
                    content={"status": 322, "tracking_code": None, "method_type": "GET",
                             "error": "کارنامه‌ها درحال آماده سازی می‌باشد."}
                )
            else:
                return JSONResponse(
                    status_code=404,
                    content={"status": 404, "tracking_code": None, "method_type": "GET", "error": "File not found"}
                )

    except Exception as e:
        await func_helper.exception_error_logging("ag_api/get_report3", "get_report3", str(e), "GET")
        return JSONResponse(
            status_code=404,
            content={"status": 404, "tracking_code": None, "method_type": "GET", "error": "File not found"}
        )

    finally:
        if conn and cursor:
            await func_helper.close_db_connection(conn=conn, cursor=cursor)


@app.get("/ag_api/get_scl_second_pdf/{phone}/{kind}")
async def get_scl_second_pdf(phone: str, kind: str):
    conn, cursor = None, None

    try:
        if kind.upper() != "SCL":
            return JSONResponse(
                status_code=321,
                content={"status": 321, "tracking_code": None, "method_type": "GET",
                         "error": "درخواست برای دریافت کارنامه نامعتبر است."}
            )
        conn, cursor = await func_helper.db_connection()
        # Check the access of the student for this kind - should have permission = 1
        query = 'SELECT user_id, access FROM stu WHERE phone = ?'
        stu = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)

        if not stu:
            return JSONResponse(
                status_code=404,
                content={"status": 404, "tracking_code": None, "method_type": "GET",
                         "error": "دانش‌آموزی با این شماره تلفن یافت نشد."}
            )

        # Parse access field to check permission
        raw_access = getattr(stu, "access", None) or "{}"
        try:
            access_data = json.loads(raw_access) if isinstance(raw_access, str) else (raw_access or {})
        except (json.JSONDecodeError, TypeError):
            access_data = {}

        # Check permission for the given kind
        package_info = access_data.get(kind.upper(), {})
        permission = 0
        if isinstance(package_info, dict):
            permission = int(package_info.get("permission") or 0)
        elif isinstance(package_info, bool):
            permission = 1 if package_info else 0
        elif isinstance(package_info, (int, float, str)):
            try:
                permission = int(package_info) if str(package_info).strip() != "" else 0
            except ValueError:
                permission = 0

        if permission != 1:
            return JSONResponse(
                status_code=403,
                content={"status": 403, "tracking_code": None, "method_type": "GET",
                         "error": "دانش‌آموز دسترسی لازم برای دریافت این کارنامه را ندارد."}
            )

        # After the count of the quiz answered, check that all answers should be completed (state = 2)
        query_quiz = (
            'SELECT state, quiz_id FROM quiz_answer '
            'WHERE user_id = ? AND quiz_kind = ? ORDER BY quiz_id ASC'
        )
        res_quiz = db_helper.search_allin_table(
            conn=conn,
            cursor=cursor,
            query=query_quiz,
            field=(stu.user_id, kind.upper())
        )
        if len(res_quiz) < 4:
            return JSONResponse(
                status_code=321,
                content={"status": 321, "tracking_code": None, "method_type": "GET",
                         "error": "در حال حاضر آزمون‌های دانش‌آموز به پایان نرسیده است."}
            )

        # Check that all quiz answers are completed (state = 2)
        for quiz in res_quiz:
            quiz_state = getattr(quiz, "state", None)
            if quiz_state != 2:
                return JSONResponse(
                    status_code=321,
                    content={"status": 321, "tracking_code": None, "method_type": "GET",
                             "error": "در حال حاضر آزمون‌های دانش‌آموز به پایان نرسیده است."}
                )

        # Proceed with checking report status
        query = 'SELECT status FROM redis_log WHERE user_id = ? and kind = ?'
        res_queue = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=(stu.user_id, kind.upper()))
        # if not res_queue:
        #     return JSONResponse(
        #         status_code=404,
        #         content={"status": 404, "tracking_code": None, "method_type": "GET",
        #                  "error": "مشکلی در سامانه پیش آماده با پشتیبانی ارتباط بگیرید."}
        #     )
        if not res_queue:
            pass
        elif res_queue.status == 1:
            return JSONResponse(
                status_code=323,
                content={"status": 323, "tracking_code": None, "method_type": "GET",
                         "error": "کارنامه در حال تولید است."}
            )
        elif res_queue.status == 0:
            return JSONResponse(
                status_code=324,
                content={"status": 324, "tracking_code": None, "method_type": "GET",
                         "error": "کارنامه در صف تولید است."}
            )
        folder_check = os.path.join(REPORTS_DIR, phone)
        file_path = os.path.join(REPORTS_DIR, phone, 'Report4.pdf')
        if os.path.exists(file_path):
            return FileResponse(file_path, filename="Report4.pdf")
        else:
            if os.path.exists(folder_check):
                return JSONResponse(
                    status_code=322,
                    content={"status": 322, "tracking_code": None, "method_type": "GET",
                             "error": "کارنامه‌ها درحال آماده سازی می‌باشد."}
                )
            else:
                return JSONResponse(
                    status_code=404,
                    content={"status": 404, "tracking_code": None, "method_type": "GET", "error": "File not found"}
                )

    except Exception as e:
        await func_helper.exception_error_logging("ag_api/get_report4", "get_report4", str(e), "GET")
        return JSONResponse(
            status_code=404,
            content={"status": 404, "tracking_code": None, "method_type": "GET", "error": "File not found"}
        )

    finally:
        if conn and cursor:
            await func_helper.close_db_connection(conn=conn, cursor=cursor)


@app.get("/ag_api/get_scl_third_pdf/{phone}/{kind}")
async def get_scl_third_pdf(phone: str, kind: str):
    conn, cursor = None, None

    try:
        if kind.upper() != "SCL":
            return JSONResponse(
                status_code=321,
                content={"status": 321, "tracking_code": None, "method_type": "GET",
                         "error": "درخواست برای دریافت کارنامه نامعتبر است."}
            )
        conn, cursor = await func_helper.db_connection()
        # Check the access of the student for this kind - should have permission = 1
        query = 'SELECT user_id, access FROM stu WHERE phone = ?'
        stu = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=phone)

        if not stu:
            return JSONResponse(
                status_code=404,
                content={"status": 404, "tracking_code": None, "method_type": "GET",
                         "error": "دانش‌آموزی با این شماره تلفن یافت نشد."}
            )

        # Parse access field to check permission
        raw_access = getattr(stu, "access", None) or "{}"
        try:
            access_data = json.loads(raw_access) if isinstance(raw_access, str) else (raw_access or {})
        except (json.JSONDecodeError, TypeError):
            access_data = {}

        # Check permission for the given kind
        package_info = access_data.get(kind.upper(), {})
        permission = 0
        if isinstance(package_info, dict):
            permission = int(package_info.get("permission") or 0)
        elif isinstance(package_info, bool):
            permission = 1 if package_info else 0
        elif isinstance(package_info, (int, float, str)):
            try:
                permission = int(package_info) if str(package_info).strip() != "" else 0
            except ValueError:
                permission = 0

        if permission != 1:
            return JSONResponse(
                status_code=403,
                content={"status": 403, "tracking_code": None, "method_type": "GET",
                         "error": "دانش‌آموز دسترسی لازم برای دریافت این کارنامه را ندارد."}
            )

        # After the count of the quiz answered, check that all answers should be completed (state = 2)
        query_quiz = (
            'SELECT state, quiz_id FROM quiz_answer '
            'WHERE user_id = ? AND quiz_kind = ? ORDER BY quiz_id ASC'
        )
        res_quiz = db_helper.search_allin_table(
            conn=conn,
            cursor=cursor,
            query=query_quiz,
            field=(stu.user_id, kind.upper())
        )
        if len(res_quiz) < 4:
            return JSONResponse(
                status_code=321,
                content={"status": 321, "tracking_code": None, "method_type": "GET",
                         "error": "در حال حاضر آزمون‌های دانش‌آموز به پایان نرسیده است."}
            )

        # Check that all quiz answers are completed (state = 2)
        for quiz in res_quiz:
            quiz_state = getattr(quiz, "state", None)
            if quiz_state != 2:
                return JSONResponse(
                    status_code=321,
                    content={"status": 321, "tracking_code": None, "method_type": "GET",
                             "error": "در حال حاضر آزمون‌های دانش‌آموز به پایان نرسیده است."}
                )

        # Proceed with checking report status
        query = 'SELECT status FROM redis_log WHERE user_id = ? and kind = ?'
        res_queue = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=(stu.user_id, kind.upper()))
        # if not res_queue:
        #     return JSONResponse(
        #         status_code=404,
        #         content={"status": 404, "tracking_code": None, "method_type": "GET",
        #                  "error": "مشکلی در سامانه پیش آماده با پشتیبانی ارتباط بگیرید."}
        #     )
        if not res_queue:
            pass
        elif res_queue.status == 1:
            return JSONResponse(
                status_code=323,
                content={"status": 323, "tracking_code": None, "method_type": "GET",
                         "error": "کارنامه در حال تولید است."}
            )
        elif res_queue.status == 0:
            return JSONResponse(
                status_code=324,
                content={"status": 324, "tracking_code": None, "method_type": "GET",
                         "error": "کارنامه در صف تولید است."}
            )
        folder_check = os.path.join(REPORTS_DIR, phone)
        file_path = os.path.join(REPORTS_DIR, phone, 'Report5.pdf')
        if os.path.exists(file_path):
            return FileResponse(file_path, filename="Report5.pdf")
        else:
            if os.path.exists(folder_check):
                return JSONResponse(
                    status_code=322,
                    content={"status": 322, "tracking_code": None, "method_type": "GET",
                             "error": "کارنامه‌ها درحال آماده سازی می‌باشد."}
                )
            else:
                return JSONResponse(
                    status_code=404,
                    content={"status": 404, "tracking_code": None, "method_type": "GET", "error": "File not found"}
                )

    except Exception as e:
        await func_helper.exception_error_logging("ag_api/get_report4", "get_report4", str(e), "GET")
        return JSONResponse(
            status_code=404,
            content={"status": 404, "tracking_code": None, "method_type": "GET", "error": "File not found"}
        )

    finally:
        if conn and cursor:
            await func_helper.close_db_connection(conn=conn, cursor=cursor)


@app.get("/ag_api/get_default/{reportname}")
async def get_first_default_pdf(reportname: str):
    file_path = os.path.join(DEFAULT_REPORT_PATH, reportname)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename="Report.pdf")
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/ag_api/get_pic/{filename}")
async def get_pic(filename: str):
    file_path = os.path.join(PICS_INFO_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/ag_api/get_pic_scl/{filename}")
async def get_pic_scl(filename: str):
    file_path = os.path.join(PICS_WORD_SCL_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/ag_api/get_pic_info/report/{filename}")
async def get_pic_info_report(filename: str):
    file_path = os.path.join(PICS_REPORT_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/ag_api/get_pic_info/quiz/{filename}")
async def get_pic_info(filename: str):
    file_path = os.path.join(PICS_QUIZ_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/ag_api/get_quiz_pic/{filename}")
async def get_quiz_pic(filename: str):
    file_path = os.path.join(QUIZ_PIC_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/ag_api/get_voice/{filename}")
async def get_voice(filename: str):
    file_path = os.path.join(VOICES_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/ag_api/get_pic_info/field/{filename}")
async def get_pic_info_field(filename: str):
    file_path = os.path.join(PICS_FIELD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")
