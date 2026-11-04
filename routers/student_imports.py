from urllib.parse import quote

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response

import helper.api_metrics as api_metrics
import helper.auth_context as auth_context
import helper.file_helper as file_helper
import helper.service_errors as service_errors
from helper.office.student_import_workbook import StudentImportValidationError, build_student_import_workbook
from helper.tracking import get_tracking_code
from services.gateway_helpers import ACCESS_DENIED_MESSAGE, error_response, service_response
from services.student_import_service import (
    ALLOWED_IMPORT_ROLES,
    get_student_import_consultant_phones,
    import_students_from_workbook,
)

router = APIRouter()

EXCEL_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
EXCEL_UPLOAD_CONTENT_TYPES = {EXCEL_CONTENT_TYPE, "application/octet-stream"}
MAX_EXCEL_UPLOAD_BYTES = 5 * 1024 * 1024


def _attachment_headers(filename: str) -> dict[str, str]:
    return {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}


@router.post("/ag_api/student_import/template")
@api_metrics.monitor_endpoint("ag_api/student_import/template")
async def student_import_template(request: Request):
    method_type = "SELECT"
    try:
        payload = await request.json()
        request_data = payload.get("request_data") or {}
        state, state_message, user_info = await auth_context.authorizer(request_data=request_data)
        if not state:
            return service_errors.not_auth_return(message=state_message)
        if user_info.get("role") not in ALLOWED_IMPORT_ROLES:
            return error_response(method_type, ACCESS_DENIED_MESSAGE)

        include_example = bool(request_data.get("example"))
        consultant_phones = get_student_import_consultant_phones(user_info)
        workbook = build_student_import_workbook(
            consultant_phones,
            include_example=include_example,
        )
        filename = "student-import-example.xlsx" if include_example else "student-import-template.xlsx"
        return Response(
            workbook,
            media_type=EXCEL_CONTENT_TYPE,
            headers=_attachment_headers(filename),
        )
    except Exception as exc:
        return await service_errors.exception_error_logging(
            "ag_api/student_import/template",
            "student_import_template",
            str(exc),
            method_type,
        )


@router.post("/ag_api/student_import")
@api_metrics.monitor_endpoint("ag_api/student_import")
async def student_import(
    file: UploadFile = File(...),
    user_id: int = Form(...),
    token: str = Form(...),
):
    method_type = "INSERT"
    request_data = {"user_id": user_id, "token": token, "filename": file.filename}
    try:
        state, state_message, user_info = await auth_context.authorizer(request_data=request_data)
        if not state:
            return service_errors.not_auth_return(message=state_message)
        if user_info.get("role") not in ALLOWED_IMPORT_ROLES:
            return error_response(method_type, ACCESS_DENIED_MESSAGE)

        file_helper.get_extension(file.filename, {".xlsx"})
        file_helper.validate_content_type(file.content_type, EXCEL_UPLOAD_CONTENT_TYPES)
        content = file_helper.read_limited_file(file.file, MAX_EXCEL_UPLOAD_BYTES)
        inserted_count = import_students_from_workbook(content, user_info)
        return service_response(
            method_type,
            get_tracking_code(),
            {"inserted_count": inserted_count},
            f"{inserted_count} دانش‌آموز با موفقیت ثبت شد.",
        )
    except StudentImportValidationError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "status": 422,
                "tracking_code": None,
                "method_type": method_type,
                "error": "اطلاعات فایل اکسل معتبر نیست.",
                "errors": exc.errors,
            },
        )
    except file_helper.FileValidationError:
        return JSONResponse(
            status_code=400,
            content={
                "status": 400,
                "tracking_code": None,
                "method_type": method_type,
                "error": "فقط فایل معتبر XLSX تا حجم ۵ مگابایت قابل بارگذاری است.",
            },
        )
    except PermissionError:
        return error_response(method_type, ACCESS_DENIED_MESSAGE)
    except Exception as exc:
        return await service_errors.exception_error_logging(
            "ag_api/student_import",
            "student_import",
            str(exc),
            method_type,
        )
