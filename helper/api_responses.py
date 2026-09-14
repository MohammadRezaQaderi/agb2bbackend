DEFAULT_SERVICE_ERROR = "مشکلی در اطلاعات شما پیش آمده با پشتیبانی در ارتباط باشید."
ACCESS_DENIED_MESSAGE = "شما به این سرویس دسترسی ندارید."


def api_error(status: int, method_type, message: str):
    return {
        "status": status,
        "tracking_code": None,
        "method_type": method_type,
        "error": message,
    }


def business_error(method_type, message: str = DEFAULT_SERVICE_ERROR):
    return api_error(200, method_type, message)


def api_success(method_type, tracking_code, response_data=None, response_message="", **extra_response):
    response = {"data": response_data, "message": response_message}
    response.update(extra_response)
    return {
        "status": 200,
        "tracking_code": tracking_code,
        "method_type": method_type,
        "response": response,
    }


def service_response(method_type, tracking_token, response_data=None, response_message="", error_message=None,
                     **extra_response):
    if tracking_token:
        return api_success(method_type, tracking_token, response_data, response_message, **extra_response)
    return business_error(
        method_type=method_type,
        message=error_message or response_message or DEFAULT_SERVICE_ERROR,
    )
