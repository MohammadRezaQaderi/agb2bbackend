from fastapi import APIRouter, Request

import helper.api_metrics as api_metrics
import helper.func_helper as func_helper
from helper.redis_helper import close_redis_connection, redis_connection
import services.admin.admin_service as admin_service
import services.service as service

router = APIRouter()


@router.post("/ags_api/signin")
@api_metrics.monitor_endpoint("ags_api/signin")
async def student_signin_api(request: Request):
    method_type = "SIGNIN"

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

        return service.student_sign_in(request_data=request_data)

    except KeyError as e:
        return await func_helper.key_error_logging("ags_api/signin", "student_signin_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ags_api/signin", "student_signin_api", str(e), method_type)


@router.post("/ags_api/select_request")
@api_metrics.monitor_endpoint("ags_api/select_request")
async def student_select_api(request: Request):
    method_type = "SELECT"

    try:
        data = await request.json()
        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()
        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)

        state, state_message, user_info = await func_helper.authorizer(request_data=request_data)
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
        return handler(request_data=request_data, user_info=user_info)

    except KeyError as e:
        return await func_helper.key_error_logging("ags_api/select_request", "student_select_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ags_api/select_request", "student_select_api", str(e), method_type)


@router.post("/ags_api/update_request")
@api_metrics.monitor_endpoint("ags_api/update_request")
async def student_update_api(request: Request):
    method_type = "UPDATE"

    try:
        data = await request.json()
        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()
        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)

        state, state_message, user_info = await func_helper.authorizer(request_data=request_data)
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
        return handler(request_data=request_data, user_info=user_info)

    except KeyError as e:
        return await func_helper.key_error_logging("ags_api/update_request", "student_update_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ags_api/update_request", "student_update_api", str(e), method_type)


@router.post("/ags_api/delete_request")
@api_metrics.monitor_endpoint("ags_api/delete_request")
async def student_delete_api(request: Request):
    method_type = "DELETE"

    try:
        data = await request.json()
        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()
        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)

        state, state_message, user_info = await func_helper.authorizer(request_data=request_data)
        if not state:
            return func_helper.not_auth_return(message=state_message)

        action_map = {
            "ags_sign_out": service.sign_out,
        }
        handler = action_map.get(action)
        if handler is None:
            return func_helper.not_method_access_return()
        return handler(request_data=request_data, user_info=user_info)

    except KeyError as e:
        return await func_helper.key_error_logging("ags_api/delete_request", "student_delete_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ags_api/delete_request", "student_delete_api", str(e), method_type)


@router.post("/ag_api/signin")
@api_metrics.monitor_endpoint("ag_api/signin")
async def signin_api(request: Request):
    method_type = "SIGNIN"

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

        return service.sign_in(request_data=request_data)

    except KeyError as e:
        return await func_helper.key_error_logging("ag_api/signin", "signin_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api/signin", "signin_api", str(e), method_type)


@router.post("/ag_api/insert_request")
@api_metrics.monitor_endpoint("ag_api/insert_request")
async def insert_api(request: Request):
    method_type = "INSERT"

    try:
        data = await request.json()

        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()

        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)

        if action == "ag_sign_up":
            redis_db = await redis_connection()
            try:
                return service.sign_up(redis_db=redis_db, request_data=request_data)
            finally:
                await close_redis_connection(redis_db=redis_db)
        elif action == "ag_send_otp":
            redis_db = await redis_connection()
            try:
                return service.send_otp(redis_db=redis_db, request_data=request_data)
            finally:
                await close_redis_connection(redis_db=redis_db)
        elif action == "ag_add_comment":
            return service.add_comment(request_data=request_data)

        state, state_message, user_info = await func_helper.authorizer(request_data=request_data)
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

        return handler(request_data=request_data, user_info=user_info)

    except KeyError as e:
        return await func_helper.key_error_logging("ag_api/insert_request", "insert_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api/insert_request", "insert_api", str(e), method_type)


@router.post("/ag_api/select_request")
@api_metrics.monitor_endpoint("ag_api/select_request")
async def select_api(request: Request):
    method_type = "SELECT"

    try:
        data = await request.json()

        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()

        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)

        if action == "ag_check_otp":
            redis_db = await redis_connection()
            try:
                return service.check_otp(redis_db=redis_db, request_data=request_data)
            finally:
                await close_redis_connection(redis_db=redis_db)

        if action == "ag_get_comments":
            return service.get_comments()

        state, state_message, user_info = await func_helper.authorizer(request_data=request_data)
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

        return handler(request_data=request_data, user_info=user_info)

    except KeyError as e:
        return await func_helper.key_error_logging("ag_api/select_request", "select_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api/select_request", "select_api", str(e), method_type)


@router.post("/ag_api/update_request")
@api_metrics.monitor_endpoint("ag_api/update_request")
async def update_api(request: Request):
    method_type = "UPDATE"

    try:
        data = await request.json()

        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()

        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)

        state, state_message, user_info = await func_helper.authorizer(request_data=request_data)
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

        return handler(request_data=request_data, user_info=user_info)

    except KeyError as e:
        return await func_helper.key_error_logging("ag_api/update_request", "update_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api/update_request", "update_api", str(e), method_type)


@router.post("/ag_api/delete_request")
@api_metrics.monitor_endpoint("ag_api/delete_request")
async def delete_api(request: Request):
    method_type = "DELETE"

    try:
        data = await request.json()

        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()

        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)

        state, state_message, user_info = await func_helper.authorizer(request_data=request_data)
        if not state:
            return func_helper.not_auth_return(message=state_message)

        action_map = {
            "ag_sign_out": service.sign_out,
        }

        handler = action_map.get(action)
        if handler is None:
            return func_helper.not_method_access_return()

        return handler(request_data=request_data, user_info=user_info)

    except KeyError as e:
        return await func_helper.key_error_logging("ag_api/delete_request", "delete_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api/delete_request", "delete_api", str(e), method_type)


@router.post("/ag_api/admin_request")
@api_metrics.monitor_endpoint("ag_api/admin_request")
async def admin_api(request: Request):
    method_type = "ADMIN"

    try:
        data = await request.json()

        token = data.get("token")
        admin_context = admin_service.authenticate_admin_token(token=token)
        if admin_context is None:
            return func_helper.not_auth_return(message="شما به این سرویس دسترسی ندارید.", method_type=method_type)

        action = data.get("action_type")
        if not action:
            return func_helper.not_method_access_return()

        request_data = data.get("request_data")
        if request_data is None:
            return func_helper.not_data_return(method_type=method_type)

        action_map = {
            "ag_change_capacity": service.admin_change_capacity,
            "ag_get_user_info": service.admin_get_user_info,
            "ag_check_student_quiz_answer": service.admin_check_student_quiz_answer,
        }

        handler = action_map.get(action)
        if handler is None:
            return func_helper.not_method_access_return()

        return handler(request_data=request_data, admin_context=admin_context, action_type=action)

    except KeyError as e:
        return await func_helper.key_error_logging("ag_api/admin_request", "admin_api", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api/admin_request", "admin_api", str(e), method_type)
