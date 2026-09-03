from fastapi import APIRouter, Request

import helper.api_metrics as api_metrics
import helper.service_errors as service_errors
from routers.action_helpers import (
    dispatch_authenticated_action,
    dispatch_redis_action,
    dispatch_single_action,
    run_endpoint,
)
import services.admin.admin_service as admin_service
import services.accounts_gateway as accounts_gateway
import services.admin.admin_gateway as admin_gateway
import services.auth.auth_gateway as auth_gateway
import services.management_gateway as management_gateway
import services.other.other_gateway as other_gateway
import services.quiz.quiz_gateway as quiz_gateway
import services.student.student_gateway as student_gateway

router = APIRouter()


STUDENT_SELECT_ACTIONS = {
    "ags_get_dashboard": student_gateway.student_get_dashboard,
    "ags_get_quiz_setting": quiz_gateway.student_get_quiz_setting,
    "ags_get_access_product": student_gateway.student_get_access_product,
    "ags_get_quiz_table_info": student_gateway.student_get_quiz_table_info,
    "ags_get_quiz_info": student_gateway.student_get_quiz_info,
}

STUDENT_UPDATE_ACTIONS = {
    "ags_change_user_info": student_gateway.student_change_user_info,
    "ags_change_password": student_gateway.student_change_password,
    "ags_change_quiz_answer": student_gateway.student_change_quiz_answer,
}

STUDENT_DELETE_ACTIONS = {
    "ags_sign_out": auth_gateway.sign_out,
}

MANAGEMENT_INSERT_ACTIONS = {
    "ag_add_payment_order": other_gateway.add_payment_order,
    "ag_add_consultant": accounts_gateway.add_consultant,
    "ag_add_student": accounts_gateway.add_student,
    "ag_mark_notification_read": other_gateway.mark_notification_read,
}

MANAGEMENT_SELECT_ACTIONS = {
    "ag_get_dashboard": management_gateway.get_dashboard,
    "ag_get_consultants": management_gateway.get_consultants,
    "ag_get_students": management_gateway.get_students,
    "ag_get_report": management_gateway.get_report,
    "ag_get_management_report": management_gateway.get_management_report,
    "ag_get_quiz_setting": quiz_gateway.get_quiz_setting,
    "ag_get_quiz_info": quiz_gateway.get_quiz_info,
    "ag_apply_discount": other_gateway.apply_discount,
    "ag_get_transactions": other_gateway.get_transactions,
    "ag_get_report_data": other_gateway.get_report_data,
}

MANAGEMENT_UPDATE_ACTIONS = {
    "ag_change_user_info": management_gateway.change_user_info,
    "ag_change_password": management_gateway.change_password,
    "ag_change_setting": management_gateway.change_setting,
    "ag_change_consultant": management_gateway.change_consultant,
    "ag_change_student": management_gateway.change_student,
    "ag_change_comment": management_gateway.change_comment,
    "ag_change_user_quiz_setting": management_gateway.change_user_quiz_setting,
    "ag_change_student_access": management_gateway.change_student_access,
}

MANAGEMENT_DELETE_ACTIONS = {
    "ag_sign_out": auth_gateway.sign_out,
}

MANAGEMENT_INSERT_PRE_AUTH_ACTIONS = {
    "ag_sign_up": lambda request_data: dispatch_redis_action(auth_gateway.sign_up, request_data),
    "ag_send_otp": lambda request_data: dispatch_redis_action(auth_gateway.send_otp, request_data),
    "ag_add_comment": other_gateway.add_comment,
}

MANAGEMENT_SELECT_PRE_AUTH_ACTIONS = {
    "ag_check_otp": lambda request_data: dispatch_redis_action(auth_gateway.check_otp, request_data),
    "ag_get_comments": lambda _request_data: other_gateway.get_comments(),
}

ADMIN_ACTIONS = {
    "ag_change_capacity": admin_gateway.admin_change_capacity,
    "ag_get_user_info": admin_gateway.admin_get_user_info,
    "ag_check_student_quiz_answer": admin_gateway.admin_check_student_quiz_answer,
}


@router.post("/ags_api/signin")
@api_metrics.monitor_endpoint("ags_api/signin")
async def student_signin_api(request: Request):
    return await run_endpoint(
        "ags_api/signin",
        "student_signin_api",
        "SIGNIN",
        lambda: dispatch_single_action(request, "SIGNIN", "ags_sign_in", auth_gateway.student_sign_in),
    )


@router.post("/ags_api/select_request")
@api_metrics.monitor_endpoint("ags_api/select_request")
async def student_select_api(request: Request):
    return await run_endpoint(
        "ags_api/select_request",
        "student_select_api",
        "SELECT",
        lambda: dispatch_authenticated_action(
            request,
            "SELECT",
            STUDENT_SELECT_ACTIONS,
        ),
    )


@router.post("/ags_api/update_request")
@api_metrics.monitor_endpoint("ags_api/update_request")
async def student_update_api(request: Request):
    return await run_endpoint(
        "ags_api/update_request",
        "student_update_api",
        "UPDATE",
        lambda: dispatch_authenticated_action(
            request,
            "UPDATE",
            STUDENT_UPDATE_ACTIONS,
        ),
    )


@router.post("/ags_api/delete_request")
@api_metrics.monitor_endpoint("ags_api/delete_request")
async def student_delete_api(request: Request):
    return await run_endpoint(
        "ags_api/delete_request",
        "student_delete_api",
        "DELETE",
        lambda: dispatch_authenticated_action(request, "DELETE", STUDENT_DELETE_ACTIONS),
    )


@router.post("/ag_api/signin")
@api_metrics.monitor_endpoint("ag_api/signin")
async def signin_api(request: Request):
    return await run_endpoint(
        "ag_api/signin",
        "signin_api",
        "SIGNIN",
        lambda: dispatch_single_action(request, "SIGNIN", "ag_sign_in", auth_gateway.sign_in),
    )


@router.post("/ag_api/insert_request")
@api_metrics.monitor_endpoint("ag_api/insert_request")
async def insert_api(request: Request):
    return await run_endpoint(
        "ag_api/insert_request",
        "insert_api",
        "INSERT",
        lambda: dispatch_authenticated_action(
            request,
            "INSERT",
            MANAGEMENT_INSERT_ACTIONS,
            pre_auth_actions=MANAGEMENT_INSERT_PRE_AUTH_ACTIONS,
        ),
    )


@router.post("/ag_api/select_request")
@api_metrics.monitor_endpoint("ag_api/select_request")
async def select_api(request: Request):
    return await run_endpoint(
        "ag_api/select_request",
        "select_api",
        "SELECT",
        lambda: dispatch_authenticated_action(
            request,
            "SELECT",
            MANAGEMENT_SELECT_ACTIONS,
            pre_auth_actions=MANAGEMENT_SELECT_PRE_AUTH_ACTIONS,
        ),
    )


@router.post("/ag_api/update_request")
@api_metrics.monitor_endpoint("ag_api/update_request")
async def update_api(request: Request):
    return await run_endpoint(
        "ag_api/update_request",
        "update_api",
        "UPDATE",
        lambda: dispatch_authenticated_action(
            request,
            "UPDATE",
            MANAGEMENT_UPDATE_ACTIONS,
        ),
    )


@router.post("/ag_api/delete_request")
@api_metrics.monitor_endpoint("ag_api/delete_request")
async def delete_api(request: Request):
    return await run_endpoint(
        "ag_api/delete_request",
        "delete_api",
        "DELETE",
        lambda: dispatch_authenticated_action(request, "DELETE", MANAGEMENT_DELETE_ACTIONS),
    )


@router.post("/ag_api/admin_request")
@api_metrics.monitor_endpoint("ag_api/admin_request")
async def admin_api(request: Request):
    return await run_endpoint(
        "ag_api/admin_request",
        "admin_api",
        "ADMIN",
        lambda: _dispatch_admin_action(request),
    )


async def _dispatch_admin_action(request: Request):
    method_type = "ADMIN"
    data = await request.json()

    token = data.get("token")
    admin_context = admin_service.authenticate_admin_token(token=token)
    if admin_context is None:
        return service_errors.not_auth_return(message="شما به این سرویس دسترسی ندارید.", method_type=method_type)

    action = data.get("action_type")
    if not action:
        return service_errors.not_method_access_return()

    request_data = data.get("request_data")
    if request_data is None:
        return service_errors.not_data_return(method_type=method_type)

    handler = ADMIN_ACTIONS.get(action)
    if handler is None:
        return service_errors.not_method_access_return()

    return handler(request_data=request_data, admin_context=admin_context, action_type=action)
