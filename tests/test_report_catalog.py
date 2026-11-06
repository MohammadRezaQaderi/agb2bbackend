from helper.db.sqlalchemy.queries.report_downloads import (
    _access_values as report_download_access_values,
)
from helper.report_catalog import build_student_report_catalog


def _attempts(count, state=2):
    return [{"quiz_id": quiz_id, "state": state} for quiz_id in range(1, count + 1)]


def test_report_catalog_exposes_file_and_generation_states():
    available_files = {("AG", "Report1.pdf")}

    catalog = build_student_report_catalog(
        access={
            "AG": {"permission": 1, "limit": 1},
            "SCL": {"permission": 1, "limit": 1},
        },
        quiz_counts={"AG": 2, "SCL": 2},
        attempts_by_package={
            "AG": _attempts(2),
            "SCL": _attempts(2),
        },
        queue_statuses={"AG": 2, "SCL": 1},
        file_available=lambda package, filename: (package, filename) in available_files,
    )

    ag, scl = catalog["products"]
    assert [report["status"] for report in ag["reports"]] == [
        "ready",
        "preparing",
    ]
    assert ag["reports"][0]["can_download"] is True
    assert scl["status"] == "generating"
    assert all(report["can_download"] is False for report in scl["reports"])


def test_report_catalog_explains_incomplete_and_missing_queue():
    catalog = build_student_report_catalog(
        access={
            "AG": {"permission": 1, "limit": 1},
            "SCL": {"permission": 1, "limit": 1},
        },
        quiz_counts={"AG": 2, "SCL": 1},
        attempts_by_package={"AG": _attempts(1), "SCL": _attempts(1)},
        queue_statuses={"AG": None, "SCL": None},
        file_available=lambda _package, _filename: False,
    )

    ag, scl = catalog["products"]
    assert ag["status"] == "quiz_incomplete"
    assert ag["completed_quizzes"] == 1
    assert scl["status"] == "not_requested"


def test_report_catalog_returns_granted_psy_packages_without_fake_downloads():
    catalog = build_student_report_catalog(
        access={
            "AG": {"permission": 0, "limit": 0},
            "SCL": {"permission": 0, "limit": 0},
            "PSY_ANX": {"permission": 1, "limit": 1},
        },
        quiz_counts={"AG": 7, "SCL": 4, "PSY_ANX": 5},
        attempts_by_package={"AG": [], "SCL": [], "PSY_ANX": _attempts(5)},
        queue_statuses={"AG": None, "SCL": None, "PSY_ANX": None},
        file_available=lambda _package, _filename: False,
    )

    psy = catalog["products"][2]
    assert psy["code"] == "PSY"
    assert psy["reports"][0]["title"] == "کارنامه اضطراب"
    assert psy["reports"][0]["status"] == "not_available"
    assert psy["reports"][0]["download_action"] is None
    assert psy["reports"][0]["can_download"] is False


def test_report_catalog_requires_separate_report_permission():
    catalog = build_student_report_catalog(
        access={
            "AG": {"permission": 1, "limit": 0},
            "SCL": {"permission": 0, "limit": 0},
        },
        quiz_counts={"AG": 1, "SCL": 1},
        attempts_by_package={"AG": _attempts(1), "SCL": []},
        queue_statuses={"AG": 2, "SCL": None},
        file_available=lambda _package, _filename: True,
    )

    ag = catalog["products"][0]
    assert ag["status"] == "report_access_denied"
    assert all(report["can_download"] is False for report in ag["reports"])


def test_report_download_access_requires_report_permission():
    assert report_download_access_values(
        {"AG": {"permission": 1, "limit": 0}},
        "AG",
    ) == (1, 0)


def test_advisor_catalog_includes_private_scl_report():
    catalog = build_student_report_catalog(
        access={
            "AG": {"permission": 0, "limit": 0},
            "SCL": {"permission": 1, "limit": 1},
        },
        quiz_counts={"AG": 7, "SCL": 4},
        attempts_by_package={"AG": [], "SCL": _attempts(4)},
        queue_statuses={"AG": None, "SCL": 2},
        file_available=lambda package, filename: (
            package,
            filename,
        )
        == ("SCL", "Report5.pdf"),
        include_advisor_reports=True,
    )

    scl = catalog["products"][1]
    assert [report["id"] for report in scl["reports"]] == [
        "scl-first-report",
        "scl-second-report",
        "scl-third-report",
    ]
    assert scl["reports"][2]["status"] == "ready"
    assert scl["reports"][2]["can_download"] is True


def test_report_catalog_can_be_scoped_to_one_product():
    catalog = build_student_report_catalog(
        access={
            "AG": {"permission": 1, "limit": 1},
            "SCL": {"permission": 1, "limit": 1},
            "PSY_ANX": {"permission": 1, "limit": 1},
        },
        quiz_counts={"AG": 1, "SCL": 1, "PSY_ANX": 1},
        attempts_by_package={
            "AG": _attempts(1),
            "SCL": _attempts(1),
            "PSY_ANX": _attempts(1),
        },
        queue_statuses={"AG": 2, "SCL": 2, "PSY_ANX": 2},
        file_available=lambda _package, _filename: False,
        product_filter="ag",
    )

    assert [product["code"] for product in catalog["products"]] == ["AG"]
