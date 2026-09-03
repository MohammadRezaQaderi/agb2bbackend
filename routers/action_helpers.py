from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from fastapi import Request

import helper.auth_context as auth_context
import helper.service_errors as service_errors
from helper.redis_helper import close_redis_connection, redis_connection

ServiceHandler = Callable[..., Any]
PreAuthHandler = Callable[[dict], Any]


@dataclass(frozen=True)
class ActionPayload:
    data: dict
    action: str
    request_data: dict


async def read_action_payload(request: Request, method_type: str) -> tuple[ActionPayload | None, dict | None]:
    data = await request.json()
    action = data.get("action_type")
    if not action:
        return None, service_errors.not_method_access_return()

    request_data = data.get("request_data")
    if request_data is None:
        return None, service_errors.not_data_return(method_type=method_type)

    return ActionPayload(data=data, action=action, request_data=request_data), None


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def run_endpoint(endpoint: str, func_name: str, method_type: str, handler: Callable[[], Any]) -> Any:
    try:
        return await _maybe_await(handler())
    except KeyError as exc:
        return await service_errors.key_error_logging(endpoint, func_name, str(exc), method_type)
    except Exception as exc:
        return await service_errors.exception_error_logging(endpoint, func_name, str(exc), method_type)


async def dispatch_single_action(
    request: Request,
    method_type: str,
    expected_action: str,
    handler: ServiceHandler,
) -> Any:
    payload, error_response = await read_action_payload(request, method_type)
    if error_response is not None:
        return error_response
    if payload.action != expected_action:
        return service_errors.not_method_access_return()
    return handler(request_data=payload.request_data)


async def dispatch_authenticated_action(
    request: Request,
    method_type: str,
    action_map: Mapping[str, ServiceHandler],
    pre_auth_actions: Mapping[str, PreAuthHandler] | None = None,
) -> Any:
    payload, error_response = await read_action_payload(request, method_type)
    if error_response is not None:
        return error_response

    pre_auth_actions = pre_auth_actions or {}
    pre_auth_handler = pre_auth_actions.get(payload.action)
    if pre_auth_handler is not None:
        return await _maybe_await(pre_auth_handler(payload.request_data))

    state, state_message, user_info = await auth_context.authorizer(request_data=payload.request_data)
    if not state:
        return service_errors.not_auth_return(message=state_message)

    handler = action_map.get(payload.action)
    if handler is None:
        return service_errors.not_method_access_return()
    return handler(request_data=payload.request_data, user_info=user_info)


async def dispatch_redis_action(handler: ServiceHandler, request_data: dict) -> Any:
    redis_db = await redis_connection()
    try:
        return handler(redis_db=redis_db, request_data=request_data)
    finally:
        await close_redis_connection(redis_db=redis_db)
