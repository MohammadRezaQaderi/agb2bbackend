from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest
from openpyxl import load_workbook

import services.student_import_service as import_service
from helper.office.student_import_workbook import (
    STUDENT_IMPORT_COLUMNS,
    STUDENT_IMPORT_SHEET,
    StudentImportValidationError,
    build_student_import_workbook,
    parse_student_import_workbook,
)

FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "student_import"


def test_student_import_template_has_dropdowns_and_hidden_options():
    content = build_student_import_workbook(["09123456789"])
    workbook = load_workbook(BytesIO(content))

    sheet = workbook[STUDENT_IMPORT_SHEET]
    assert [cell.value for cell in sheet[1]] == [label for label, _ in STUDENT_IMPORT_COLUMNS]
    assert len(sheet.data_validations.dataValidation) == 8
    education_field_validation = next(
        validation for validation in sheet.data_validations.dataValidation if str(validation.sqref).startswith("H2:")
    )
    assert education_field_validation.allow_blank is True
    assert workbook["_options"].sheet_state == "hidden"
    assert sheet.sheet_view.rightToLeft is True


def test_student_import_example_parses_to_backend_values():
    content = build_student_import_workbook(["09123456789"], include_example=True)

    rows = parse_student_import_workbook(content)

    assert rows == [
        {
            "row_number": 2,
            "first_name": "علی",
            "last_name": "نمونه",
            "sex": 0,
            "city": "تهران,8",
            "consultant_phone": "09123456789",
            "birth_date": "1388",
            "education_level": "second",
            "education_field": "experimental",
        }
    ]


def test_student_import_fixture_files_cover_valid_and_invalid_uploads():
    valid_rows = parse_student_import_workbook((FIXTURE_DIRECTORY / "student_import_valid.xlsx").read_bytes())
    assert len(valid_rows) == 1
    assert valid_rows[0]["consultant_phone"] == "09382858785"

    with pytest.raises(StudentImportValidationError) as exc_info:
        parse_student_import_workbook((FIXTURE_DIRECTORY / "student_import_invalid.xlsx").read_bytes())

    fields = {error["field"] for error in exc_info.value.errors}
    assert {
        "نام",
        "جنسیت",
        "استان محل سکونت",
        "شماره تلفن مشاور",
        "سال تولد",
        "رشته تحصیلی",
    }.issubset(fields)


def test_student_import_reports_all_invalid_cells_before_insert():
    content = build_student_import_workbook(["09123456789"], include_example=True)
    workbook = load_workbook(BytesIO(content))
    sheet = workbook[STUDENT_IMPORT_SHEET]
    sheet["A2"] = ""
    sheet["C2"] = "نامشخص"
    sheet["D2"] = "استان نامعتبر"
    sheet["E2"] = "123"
    sheet["F2"] = "88"
    sheet["G2"] = "سوم"
    output = BytesIO()
    workbook.save(output)

    with pytest.raises(StudentImportValidationError) as exc_info:
        parse_student_import_workbook(output.getvalue())

    fields = {error["field"] for error in exc_info.value.errors}
    assert {
        "نام",
        "جنسیت",
        "استان محل سکونت",
        "شماره تلفن مشاور",
        "سال تولد",
        "دوره تحصیلی",
    }.issubset(fields)


def test_student_import_rejects_changed_headers():
    content = build_student_import_workbook(["09123456789"], include_example=True)
    workbook = load_workbook(BytesIO(content))
    workbook[STUDENT_IMPORT_SHEET]["A1"] = "نام دانش‌آموز"
    output = BytesIO()
    workbook.save(output)

    with pytest.raises(StudentImportValidationError, match="invalid"):
        parse_student_import_workbook(output.getvalue())


def test_import_validates_consultant_ownership_before_creating_accounts(monkeypatch):
    rows = [{"row_number": 2, "consultant_phone": "09120000000"}]
    create_account = Mock(side_effect=AssertionError("account creation must not run"))

    @contextmanager
    def fake_session_scope():
        yield object()

    monkeypatch.setattr(import_service, "parse_student_import_workbook", lambda _content: rows)
    monkeypatch.setattr(import_service, "session_scope", fake_session_scope)
    monkeypatch.setattr(import_service, "_consultant_phone_map", lambda _session, _user: {})
    monkeypatch.setattr(import_service, "create_student_account", create_account)

    with pytest.raises(StudentImportValidationError) as exc_info:
        import_service.import_students_from_workbook(
            b"xlsx",
            {"user_id": 10, "phone": "09121111111", "role": "ins"},
        )

    assert exc_info.value.errors[0]["row"] == 2
    create_account.assert_not_called()


def test_import_creates_all_students_in_one_session(monkeypatch):
    rows = [
        {
            "row_number": row_number,
            "first_name": "نام",
            "last_name": "خانوادگی",
            "sex": 0,
            "city": "تهران,8",
            "consultant_phone": "09120000000",
            "birth_date": "1388",
            "education_level": "second",
            "education_field": "experimental",
        }
        for row_number in (2, 3)
    ]
    session = object()
    create_account = Mock()

    @contextmanager
    def fake_session_scope():
        yield session

    monkeypatch.setattr(import_service, "parse_student_import_workbook", lambda _content: rows)
    monkeypatch.setattr(import_service, "session_scope", fake_session_scope)
    monkeypatch.setattr(
        import_service,
        "_consultant_phone_map",
        lambda _session, _user: {"09120000000": 20},
    )
    monkeypatch.setattr(
        import_service, "_generate_available_student_phone", Mock(side_effect=["00911111111", "00922222222"])
    )
    monkeypatch.setattr(import_service, "random_generate_password", lambda: "123456")
    monkeypatch.setattr(import_service, "encrypt_password", lambda password: f"encrypted:{password}")
    monkeypatch.setattr(import_service, "create_student_account", create_account)

    inserted_count = import_service.import_students_from_workbook(
        b"xlsx",
        {"user_id": 10, "phone": "09121111111", "role": "ins"},
    )

    assert inserted_count == 2
    assert create_account.call_count == 2
    assert all(call.kwargs["session"] is session for call in create_account.call_args_list)


def test_import_rejects_unsupported_role_before_reading_workbook(monkeypatch):
    parser = Mock(side_effect=AssertionError("workbook must not be read"))
    monkeypatch.setattr(import_service, "parse_student_import_workbook", parser)

    with pytest.raises(PermissionError):
        import_service.import_students_from_workbook(
            b"xlsx",
            {"user_id": 10, "phone": "09121111111", "role": "con"},
        )

    parser.assert_not_called()
