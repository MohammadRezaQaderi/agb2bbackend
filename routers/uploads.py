from fastapi import APIRouter, Form, Request, UploadFile

import helper.api_metrics as api_metrics
import helper.file_helper as file_helper
import helper.func_helper as func_helper
import services.institute.institute_service as institute_service
import services.management_gateway as management_gateway
import services.owner_consultant.owner_consultant_service as owner_consultant_service
import services.school.school_service as school_service
from config import VOICES_DIR
from services.gateway_helpers import service_response

router = APIRouter()


@router.post("/ag_api/update_user_file_image")
@api_metrics.monitor_endpoint("ag_api/update_user_file_image")
async def update_user_file_image(request: Request):
    method_type = "UPDATE"
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
        state, state_message, user_info = await func_helper.authorizer(
            request_data={"user_id": int(user_id), "token": token}
        )
        if not state:
            return func_helper.not_auth_return(message=state_message)
        return management_gateway.change_user_info(request_data=request_data, user_info=user_info)
    except KeyError as e:
        return await func_helper.key_error_logging("ag_api", "update_user_file_image", str(e), method_type)
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api", "update_user_file_image", str(e), method_type)


@router.post("/ag_api/update_user_voice")
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
    try:
        state, state_message, user_info = await func_helper.authorizer(
            request_data={"user_id": int(user_id), "token": token}
        )
        if not state:
            return func_helper.not_auth_return(message=state_message)

        file_helper.validate_content_type(voice.content_type, file_helper.VOICE_CONTENT_TYPES)
        extension = file_helper.get_extension(voice.filename, file_helper.VOICE_EXTENSIONS)
        voice_content = file_helper.read_limited_file(voice.file, file_helper.MAX_VOICE_BYTES)
        new_file_name = f"{func_helper.get_tracking_code()}{extension}"
        file_helper.write_storage_file(VOICES_DIR, new_file_name, voice_content)
        file_helper.remove_storage_file(VOICES_DIR, last_voice)

        data = {
            "phone": phone,
            "setting_id": setting_id,
            "description": description,
            "quiz_id": quiz_id,
            "user_id": int(user_id),
            "voice": new_file_name,
        }
        if role == "ins":
            tracking_token, response_data, response_message = institute_service.change_user_voice(
                request_data=data, user_info=user_info
            )
            return service_response(method_type, tracking_token, response_data, response_message)
        if role == "sch":
            tracking_token, response_data, response_message = school_service.change_user_voice(
                request_data=data, user_info=user_info
            )
            return service_response(method_type, tracking_token, response_data, response_message)
        if role == "ocon":
            tracking_token, response_data, response_message = owner_consultant_service.change_user_voice(
                request_data=data, user_info=user_info
            )
            return service_response(method_type, tracking_token, response_data, response_message)

        return {
            "status": 200,
            "tracking_code": None,
            "method_type": method_type,
            "error": "شما به این سرویس دسترسی ندارید.",
        }
    except file_helper.FileValidationError:
        return service_response(method_type, None, error_message="فایل صوتی معتبر نیست.")
    except Exception as e:
        return await func_helper.exception_error_logging("ag_api", "update_user_voice", str(e), method_type)
