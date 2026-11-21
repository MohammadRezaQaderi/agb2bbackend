from helper.psy_catalog import build_psy_catalog
from helper.quiz_metadata import get_quiz_name
from helper.response.dashboard_response import build_dashboard_info_response
from helper.response.report_response import build_student_management_report_response


def _completed_anxiety_attempts(user_id=10):
    return [{"user_id": user_id, "quiz_kind": "PSY_ANX", "quiz_id": quiz_id, "state": 2} for quiz_id in range(1, 6)]


def test_psy_catalog_uses_compiled_quiz_metadata_and_dashboard_counts():
    dashboard = build_dashboard_info_response(
        capacity_packages=[
            {"package_name": "PSY_ANX", "allowed": 7, "used": 3},
        ],
        student_count=1,
        package_counts={"PSY_ANX": 3},
        quiz_attempts=_completed_anxiety_attempts(),
        packages_data={"PSY_ANX": {}},
    )

    catalog = build_psy_catalog(dashboard)
    anxiety = next(package for package in catalog["packages"] if package["package_name"] == "PSY_ANX")

    assert anxiety["title"] == "اضطراب"
    assert anxiety["quiz_count"] == 5
    assert anxiety["quizzes"][0]["name"] == "پرسشنامه نگرانی پنسیلوانا"
    assert anxiety["capacity"] == {"allowed": 7, "used": 3, "total": 10}
    assert anxiety["access_count"] == 3
    assert anxiety["report_summary"]["completed_students"] == 1
    assert anxiety["report_summary"]["download_available"] is False


def test_management_report_uses_real_psy_quiz_count_and_name():
    reports = build_student_management_report_response(
        students=[
            {
                "user_id": 10,
                "first_name": "Test",
                "last_name": "Student",
                "access": {"PSY_ANX": {"permission": 1, "limit": 1}},
            }
        ],
        quiz_attempts=_completed_anxiety_attempts(),
        packages_data={"PSY_ANX": {}},
        get_quiz_name=get_quiz_name,
    )

    state = reports[0]["access_state"]["PSY_ANX"]
    assert state["state"] == "completed"
    assert state["current_quiz_name"] == "پرسشنامه اثر اضطراب بر تحصیل"
