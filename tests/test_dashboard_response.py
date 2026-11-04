from helper.response.dashboard_response import build_dashboard_info_response


def test_dashboard_quiz_report_uses_consistent_attempt_counts():
    response = build_dashboard_info_response(
        capacity_packages=[],
        student_count=2,
        package_counts={"AG": 2},
        quiz_attempts=[
            {"user_id": 1, "quiz_kind": "AG", "quiz_id": 1, "state": 2},
            {"user_id": 1, "quiz_kind": "AG", "quiz_id": 2, "state": 1},
            {"user_id": 2, "quiz_kind": "AG", "quiz_id": 1, "state": 2},
            {"user_id": 2, "quiz_kind": "AG", "quiz_id": 2, "state": 2},
        ],
        packages_data={"AG": {}, "SCL": {}},
    )

    ag_report = response["quiz_report"]["AG"]
    assert ag_report["completed_attempts"] == 3
    assert ag_report["in_progress_attempts"] == 1
    assert ag_report["total_attempts"] == 4
    assert ag_report["c_quiz"] == 3
    assert ag_report["nc_quiz"] == 1

    assert response["quiz_report"]["SCL"]["completed_attempts"] == 0
    assert response["quiz_report"]["SCL"]["in_progress_attempts"] == 0
    assert response["quiz_report"]["SCL"]["total_attempts"] == 0
