from helper.api_responses import (
    ACCESS_DENIED_MESSAGE,
    DEFAULT_SERVICE_ERROR,
    business_error,
    service_response,
)


def error_response(method_type, message=DEFAULT_SERVICE_ERROR):
    return business_error(method_type=method_type, message=message)


def role_handler(user_info, handlers):
    handler = handlers.get(user_info.get("role"))
    return handler() if handler else None
