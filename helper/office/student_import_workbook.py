from __future__ import annotations

import re
import zipfile
from io import BytesIO
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from helper.constants import PROVINCES
from helper.student_education import EDUCATION_FIELDS, EDUCATION_LEVELS

MAX_STUDENT_IMPORT_ROWS = 500
MAX_STUDENT_IMPORT_UNCOMPRESSED_BYTES = 20 * 1024 * 1024
STUDENT_IMPORT_SHEET = "دانش‌آموزان"

STUDENT_IMPORT_COLUMNS = (
    ("نام", "first_name"),
    ("نام خانوادگی", "last_name"),
    ("جنسیت", "sex"),
    ("استان محل سکونت", "province"),
    ("شماره تلفن مشاور", "consultant_phone"),
    ("سال تولد", "birth_date"),
    ("دوره تحصیلی", "education_level"),
    ("رشته تحصیلی", "education_field"),
)

SEX_OPTIONS = ("مرد", "زن")
SEX_IDS = {"مرد": 0, "زن": 1}
PROVINCE_BY_NAME = {item["name"]: item for item in PROVINCES}
EDUCATION_LEVEL_BY_LABEL = {item["label"]: item["id"] for item in EDUCATION_LEVELS}
EDUCATION_FIELD_BY_LABEL = {item["label"]: item["id"] for item in EDUCATION_FIELDS}
DIGIT_TRANSLATION = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


class StudentImportValidationError(ValueError):
    def __init__(self, errors: list[dict[str, Any]]):
        super().__init__("Student import workbook is invalid.")
        self.errors = errors


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def normalize_phone(value: Any) -> str:
    phone = _clean_text(value).translate(DIGIT_TRANSLATION)
    phone = re.sub(r"[\s\-()]", "", phone)
    if len(phone) == 10 and phone.startswith("9"):
        phone = f"0{phone}"
    return phone


def _defined_name(workbook: Workbook, name: str, column: str, count: int) -> None:
    from openpyxl.workbook.defined_name import DefinedName

    last_row = max(count + 1, 2)
    workbook.defined_names.add(DefinedName(name, attr_text=f"'_options'!${column}$2:${column}${last_row}"))


def _add_list_validation(
    sheet,
    formula: str,
    cells: str,
    prompt: str,
    *,
    allow_blank: bool = False,
) -> None:
    validation = DataValidation(type="list", formula1=formula, allow_blank=allow_blank)
    validation.error = "مقدار را فقط از فهرست انتخاب کنید."
    validation.errorTitle = "مقدار نامعتبر"
    validation.prompt = prompt
    validation.promptTitle = "راهنما"
    validation.showErrorMessage = True
    validation.showInputMessage = True
    sheet.add_data_validation(validation)
    validation.add(cells)


def build_student_import_workbook(
    consultant_phones: list[str],
    *,
    include_example: bool = False,
) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = STUDENT_IMPORT_SHEET
    sheet.sheet_view.rightToLeft = True
    sheet.freeze_panes = "A2"
    sheet.append([label for label, _ in STUDENT_IMPORT_COLUMNS])

    normalized_phones = list(dict.fromkeys(filter(None, (normalize_phone(phone) for phone in consultant_phones))))
    if include_example:
        sheet.append(
            [
                "علی",
                "نمونه",
                "مرد",
                "تهران",
                normalized_phones[0] if normalized_phones else "09123456789",
                "1388",
                "دوم",
                "تجربی",
            ]
        )

    header_fill = PatternFill("solid", fgColor="4361EE")
    for cell in sheet[1]:
        cell.font = Font(name="Tahoma", bold=True, color="FFFFFF", size=11)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.comment = Comment("این ستون الزامی است.", "AG")
    sheet.row_dimensions[1].height = 32

    widths = (18, 22, 14, 24, 22, 14, 18, 32)
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.column_dimensions["E"].number_format = "@"
    sheet.column_dimensions["F"].number_format = "@"
    if include_example:
        for cell in sheet[2]:
            cell.font = Font(name="Tahoma", size=11)
            cell.alignment = Alignment(horizontal="right", vertical="center")

    options = workbook.create_sheet("_options")
    option_groups = (
        ("جنسیت", SEX_OPTIONS),
        ("استان", tuple(PROVINCE_BY_NAME)),
        ("مشاور", tuple(normalized_phones) or ("",)),
        ("دوره", tuple(EDUCATION_LEVEL_BY_LABEL)),
        ("رشته", tuple(EDUCATION_FIELD_BY_LABEL)),
    )
    for column_index, (title, values) in enumerate(option_groups, start=1):
        options.cell(row=1, column=column_index, value=title)
        for row_index, value in enumerate(values, start=2):
            options.cell(row=row_index, column=column_index, value=value)
        _defined_name(workbook, f"StudentImportOptions{column_index}", get_column_letter(column_index), len(values))
    options.sheet_state = "hidden"

    last_row = MAX_STUDENT_IMPORT_ROWS + 1
    _add_list_validation(sheet, "=StudentImportOptions1", f"C2:C{last_row}", "مرد یا زن")
    _add_list_validation(sheet, "=StudentImportOptions2", f"D2:D{last_row}", "استان محل سکونت")
    _add_list_validation(sheet, "=StudentImportOptions3", f"E2:E{last_row}", "شماره تلفن مشاور")
    _add_list_validation(sheet, "=StudentImportOptions4", f"G2:G{last_row}", "دوره اول یا دوم")
    _add_list_validation(
        sheet,
        "=StudentImportOptions5",
        f"H2:H{last_row}",
        "برای دوره دوم الزامی است",
        allow_blank=True,
    )

    for column in ("A", "B"):
        validation = DataValidation(type="textLength", operator="between", formula1="2", formula2="50")
        validation.error = "نام باید بین ۲ تا ۵۰ نویسه باشد."
        validation.errorTitle = "مقدار نامعتبر"
        validation.showErrorMessage = True
        sheet.add_data_validation(validation)
        validation.add(f"{column}2:{column}{last_row}")

    birth_year_validation = DataValidation(
        type="whole",
        operator="between",
        formula1="1300",
        formula2="1500",
    )
    birth_year_validation.error = "سال تولد باید یک عدد چهاررقمی معتبر باشد."
    birth_year_validation.errorTitle = "سال تولد نامعتبر"
    birth_year_validation.showErrorMessage = True
    sheet.add_data_validation(birth_year_validation)
    birth_year_validation.add(f"F2:F{last_row}")

    field_required_fill = PatternFill("solid", fgColor="FFF4E5")
    sheet.conditional_formatting.add(
        f"H2:H{last_row}",
        FormulaRule(formula=['AND($G2="دوم",$H2="")'], fill=field_required_fill),
    )
    sheet.auto_filter.ref = f"A1:H{max(sheet.max_row, 2)}"

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _validate_xlsx_archive(content: bytes) -> None:
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            members = archive.infolist()
            if len(members) > 200:
                raise StudentImportValidationError(
                    [{"row": None, "field": "فایل", "message": "ساختار فایل اکسل معتبر نیست."}]
                )
            if sum(member.file_size for member in members) > MAX_STUDENT_IMPORT_UNCOMPRESSED_BYTES:
                raise StudentImportValidationError(
                    [{"row": None, "field": "فایل", "message": "حجم بازشده فایل اکسل بیش از حد مجاز است."}]
                )
    except zipfile.BadZipFile as exc:
        raise StudentImportValidationError(
            [{"row": None, "field": "فایل", "message": "فایل اکسل قابل خواندن نیست."}]
        ) from exc


def _row_error(row: int | None, field: str, message: str) -> dict[str, Any]:
    return {"row": row, "field": field, "message": message}


def parse_student_import_workbook(content: bytes) -> list[dict[str, Any]]:
    _validate_xlsx_archive(content)
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=False, keep_links=False)
    except Exception as exc:
        raise StudentImportValidationError([_row_error(None, "فایل", "فایل اکسل قابل خواندن نیست.")]) from exc

    try:
        if STUDENT_IMPORT_SHEET not in workbook.sheetnames:
            raise StudentImportValidationError([_row_error(None, "فایل", f"برگه «{STUDENT_IMPORT_SHEET}» یافت نشد.")])
        sheet = workbook[STUDENT_IMPORT_SHEET]
        expected_headers = [label for label, _ in STUDENT_IMPORT_COLUMNS]
        actual_headers = [_clean_text(sheet.cell(1, index).value) for index in range(1, len(expected_headers) + 1)]
        if actual_headers != expected_headers:
            raise StudentImportValidationError(
                [_row_error(None, "ستون‌ها", "عنوان یا ترتیب ستون‌های فایل با قالب اصلی یکسان نیست.")]
            )
        if sheet.max_column != len(expected_headers):
            raise StudentImportValidationError([_row_error(None, "ستون‌ها", "ستون اضافی در فایل وجود دارد.")])
        if max(sheet.max_row - 1, 0) > MAX_STUDENT_IMPORT_ROWS:
            raise StudentImportValidationError(
                [_row_error(None, "فایل", f"حداکثر {MAX_STUDENT_IMPORT_ROWS} دانش‌آموز قابل بارگذاری است.")]
            )

        parsed_rows: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for row_number, cells in enumerate(
            sheet.iter_rows(min_row=2, max_col=len(expected_headers)),
            start=2,
        ):
            values = [_clean_text(cell.value) for cell in cells]
            if not any(values):
                continue
            if any(cell.data_type == "f" for cell in cells):
                errors.append(_row_error(row_number, "ردیف", "استفاده از فرمول در فایل مجاز نیست."))
                continue

            raw = dict(zip((key for _, key in STUDENT_IMPORT_COLUMNS), values, strict=True))
            first_name = raw["first_name"]
            last_name = raw["last_name"]
            if not 2 <= len(first_name) <= 50:
                errors.append(_row_error(row_number, "نام", "نام باید بین ۲ تا ۵۰ نویسه باشد."))
            if not 2 <= len(last_name) <= 50:
                errors.append(_row_error(row_number, "نام خانوادگی", "نام خانوادگی باید بین ۲ تا ۵۰ نویسه باشد."))

            sex = SEX_IDS.get(raw["sex"])
            if sex is None:
                errors.append(_row_error(row_number, "جنسیت", "جنسیت باید مرد یا زن باشد."))

            province = PROVINCE_BY_NAME.get(raw["province"])
            if province is None:
                errors.append(_row_error(row_number, "استان محل سکونت", "استان انتخاب‌شده معتبر نیست."))

            consultant_phone = normalize_phone(raw["consultant_phone"])
            if not re.fullmatch(r"09\d{9}", consultant_phone):
                errors.append(
                    _row_error(row_number, "شماره تلفن مشاور", "شماره تلفن مشاور باید ۱۱ رقم و با 09 شروع شود.")
                )

            birth_date = raw["birth_date"].translate(DIGIT_TRANSLATION)
            if not re.fullmatch(r"\d{4}", birth_date) or not 1300 <= int(birth_date) <= 1500:
                errors.append(_row_error(row_number, "سال تولد", "سال تولد باید یک عدد چهاررقمی معتبر باشد."))

            education_level = EDUCATION_LEVEL_BY_LABEL.get(raw["education_level"])
            if education_level is None:
                errors.append(_row_error(row_number, "دوره تحصیلی", "دوره تحصیلی باید اول یا دوم باشد."))

            education_field = None
            if education_level == "second":
                education_field = EDUCATION_FIELD_BY_LABEL.get(raw["education_field"])
                if education_field is None:
                    errors.append(_row_error(row_number, "رشته تحصیلی", "رشته تحصیلی دوره دوم معتبر نیست."))
            elif raw["education_field"]:
                errors.append(_row_error(row_number, "رشته تحصیلی", "برای دوره اول، رشته تحصیلی باید خالی باشد."))

            parsed_rows.append(
                {
                    "row_number": row_number,
                    "first_name": first_name,
                    "last_name": last_name,
                    "sex": sex,
                    "city": f"{province['name']},{province['id']}" if province else None,
                    "consultant_phone": consultant_phone,
                    "birth_date": birth_date,
                    "education_level": education_level,
                    "education_field": education_field,
                }
            )

        if not parsed_rows and not errors:
            errors.append(_row_error(None, "فایل", "فایل هیچ ردیف دانش‌آموزی ندارد."))
        if errors:
            raise StudentImportValidationError(errors)
        return parsed_rows
    finally:
        workbook.close()
