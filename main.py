import os

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

import helper.api_metrics as api_metrics
import helper.file_helper as file_helper
import helper.func_helper as func_helper
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.report_downloads import get_report_download_status
from routers.actions import router as actions_router
from routers.files import router as files_router
from routers.health import router as health_router
from routers.static_data import router as static_data_router
from routers.uploads import router as uploads_router
from config import (
    REPORTS_DIR,
)

app = FastAPI()
app.middleware("http")(api_metrics.prometheus_http_middleware)
app.include_router(actions_router)
app.include_router(files_router)
app.include_router(health_router)
app.include_router(static_data_router)
app.include_router(uploads_router)


def _report_error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"status": status_code, "tracking_code": None, "method_type": "GET", "error": message},
    )


async def _get_report_pdf(
    phone: str,
    kind: str,
    expected_kind: str,
    expected_quiz_count: int,
    report_filename: str,
    log_endpoint: str,
    log_func_name: str,
):
    try:
        kind = kind.upper()
        if kind != expected_kind:
            return _report_error(321, "درخواست برای دریافت کارنامه نامعتبر است.")

        with session_scope() as session:
            report_status = get_report_download_status(
                session=session,
                phone=phone,
                kind=kind,
                expected_quiz_count=expected_quiz_count,
            )

        status = report_status["status"]
        if status == "student_not_found":
            return _report_error(404, "دانش‌آموزی با این شماره تلفن یافت نشد.")
        if status == "access_denied":
            return _report_error(403, "دانش‌آموز دسترسی لازم برای دریافت این کارنامه را ندارد.")
        if status == "quiz_incomplete":
            return _report_error(321, "در حال حاضر آزمون‌های دانش‌آموز به پایان نرسیده است.")
        if status == "generating":
            return _report_error(323, "کارنامه در حال تولید است.")
        if status == "queued":
            return _report_error(324, "کارنامه در صف تولید است.")

        try:
            folder_check = os.path.join(REPORTS_DIR, file_helper.normalize_storage_filename(phone))
            file_path = file_helper.safe_storage_path(folder_check, report_filename)
        except file_helper.FileValidationError:
            return _report_error(404, "File not found")
        if os.path.isfile(file_path):
            return FileResponse(file_path, filename=report_filename)
        if os.path.isdir(folder_check):
            return _report_error(322, "کارنامه‌ها درحال آماده سازی می‌باشد.")
        return _report_error(404, "File not found")
    except Exception as e:
        await func_helper.exception_error_logging(log_endpoint, log_func_name, str(e), "GET")
        return _report_error(404, "File not found")


@app.get("/ags_api/get_ag_first_pdf/{phone}/{kind}")
@app.get("/ag_api/get_ag_first_pdf/{phone}/{kind}")
async def get_ag_first_pdf(phone: str, kind: str):
    return await _get_report_pdf(phone, kind, "AG", 7, "Report1.pdf", "ag_api/get_report1", "get_report1")


@app.get("/ags_api/get_ag_second_pdf/{phone}/{kind}")
@app.get("/ag_api/get_ag_second_pdf/{phone}/{kind}")
async def get_ag_second_pdf(phone: str, kind: str):
    return await _get_report_pdf(phone, kind, "AG", 7, "Report2.pdf", "ag_api/get_report2", "get_report2")


@app.get("/ags_api/get_scl_first_pdf/{phone}/{kind}")
@app.get("/ag_api/get_scl_first_pdf/{phone}/{kind}")
async def get_scl_first_pdf(phone: str, kind: str):
    return await _get_report_pdf(phone, kind, "SCL", 4, "Report3.pdf", "ag_api/get_report3", "get_report3")


@app.get("/ags_api/get_scl_second_pdf/{phone}/{kind}")
@app.get("/ag_api/get_scl_second_pdf/{phone}/{kind}")
async def get_scl_second_pdf(phone: str, kind: str):
    return await _get_report_pdf(phone, kind, "SCL", 4, "Report4.pdf", "ag_api/get_report4", "get_report4")


@app.get("/ags_api/get_scl_third_pdf/{phone}/{kind}")
@app.get("/ag_api/get_scl_third_pdf/{phone}/{kind}")
async def get_scl_third_pdf(phone: str, kind: str):
    return await _get_report_pdf(phone, kind, "SCL", 4, "Report5.pdf", "ag_api/get_report4", "get_report4")
