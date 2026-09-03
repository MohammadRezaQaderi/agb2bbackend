DEFAULT_SERVICE_ERROR = "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."
ACCESS_DENIED_MESSAGE = "شما به این سرویس دسترسی ندارید."


def error_response(method_type, message=DEFAULT_SERVICE_ERROR):
    return {"status": 200, "tracking_code": None, "method_type": method_type, "error": message}


def service_response(method_type, tracking_token, response_data=None, response_message="", error_message=None,
                     **extra_response):
    if tracking_token:
        response = {"data": response_data, "message": response_message}
        response.update(extra_response)
        return {
            "status": 200,
            "tracking_code": tracking_token,
            "method_type": method_type,
            "response": response,
        }
    return error_response(
        method_type=method_type,
        message=error_message or response_message or DEFAULT_SERVICE_ERROR,
    )


def role_handler(user_info, handlers):
    handler = handlers.get(user_info.get("role"))
    return handler() if handler else None
