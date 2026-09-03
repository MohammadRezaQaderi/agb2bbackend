import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

import helper.file_helper as file_helper
from config import (
    DEFAULT_REPORT_PATH,
    INS_PIC_DIR,
    PICS_FIELD_DIR,
    PICS_INFO_DIR,
    PICS_QUIZ_DIR,
    PICS_REPORT_DIR,
    PICS_WORD_SCL_DIR,
    QUIZ_PIC_DIR,
    VOICES_DIR,
)

router = APIRouter()


def storage_file_response(storage_dir: str, filename: str, download_name: str | None = None) -> FileResponse:
    try:
        file_path = file_helper.safe_storage_path(storage_dir, filename)
        clean_name = file_helper.normalize_storage_filename(filename)
    except file_helper.FileValidationError:
        raise HTTPException(status_code=404, detail="File not found")

    if os.path.isfile(file_path):
        return FileResponse(file_path, filename=download_name or clean_name)
    raise HTTPException(status_code=404, detail="File not found")


@router.get("/ags_api/get_ins_pic/{filename}")
@router.get("/ag_api/get_ins_pic/{filename}")
async def get_ins_pic(filename: str):
    return storage_file_response(INS_PIC_DIR, filename)


@router.get("/ags_api/get_default/{reportname}")
@router.get("/ag_api/get_default/{reportname}")
async def get_first_default_pdf(reportname: str):
    return storage_file_response(DEFAULT_REPORT_PATH, reportname, download_name="Report.pdf")


@router.get("/ags_api/get_pic/{filename}")
@router.get("/ag_api/get_pic/{filename}")
async def get_pic(filename: str):
    return storage_file_response(PICS_INFO_DIR, filename)


@router.get("/ags_api/get_pic_scl/{filename}")
@router.get("/ag_api/get_pic_scl/{filename}")
async def get_pic_scl(filename: str):
    return storage_file_response(PICS_WORD_SCL_DIR, filename)


@router.get("/ags_api/get_pic_info/report/{filename}")
@router.get("/ag_api/get_pic_info/report/{filename}")
async def get_pic_info_report(filename: str):
    return storage_file_response(PICS_REPORT_DIR, filename)


@router.get("/ags_api/get_pic_info/quiz/{filename}")
@router.get("/ag_api/get_pic_info/quiz/{filename}")
async def get_pic_info(filename: str):
    return storage_file_response(PICS_QUIZ_DIR, filename)


@router.get("/ags_api/get_quiz_pic/{filename}")
@router.get("/ag_api/get_quiz_pic/{filename}")
async def get_quiz_pic(filename: str):
    return storage_file_response(QUIZ_PIC_DIR, filename)


@router.get("/ags_api/get_voice/{filename}")
@router.get("/ag_api/get_voice/{filename}")
async def get_voice(filename: str):
    return storage_file_response(VOICES_DIR, filename)


@router.get("/ags_api/get_pic_info/field/{filename}")
@router.get("/ag_api/get_pic_info/field/{filename}")
async def get_pic_info_field(filename: str):
    return storage_file_response(PICS_FIELD_DIR, filename)
