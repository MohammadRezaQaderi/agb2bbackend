from typing import Any, Mapping

from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.auth import get_user_identity_by_token
from helper.service_errors import service_exception_error_logging


async def authorizer(request_data: Mapping[str, Any]):
    try:
        token = request_data.get("token")
        if not token:
            return False, "اطلاعات دریافتی شما دچار مشکل شده لطفا یکبار خروج کرده و سپس ورود شوید.", None

        with session_scope() as session:
            res = get_user_identity_by_token(session=session, token=token)

        if res is None:
            return False, "نشست شما به پایان رسیده  لطفا یکبار خروج کرده و سپس ورود شوید.", None

        request_user_id = request_data.get("user_id")
        if request_user_id is None or str(request_user_id) != str(res["user_id"]):
            return False, "اطلاعات دریافتی شما دچار مشکل شده لطفا یکبار خروج کرده و سپس ورود شوید.", None

        return True, "", {"user_id": res["user_id"], "phone": res["phone"], "role": res["role"]}
    except Exception as e:
        service_exception_error_logging("ag_api/check", "check", str(e), request_data, {})
        return False, "اطلاعات دریافتی شما دچار مشکل شده لطفا یکبار خروج کرده و سپس ورود شوید.", None
