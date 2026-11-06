from helper.response.report_response import build_student_report_response


def test_student_report_response_filters_access_to_requested_package():
    students = [
        {
            "stu_id": 1,
            "user_id": 10,
            "access": {
                "AG": {"permission": 1, "limit": 1},
                "SCL": {"permission": 1, "limit": 1},
                "PSY_ANX": {"permission": 1, "limit": 1},
            },
        }
    ]

    response = build_student_report_response(students, package_name="ag")

    assert response[0]["access"] == {"AG": {"permission": 1, "limit": 1}}


def test_student_report_response_keeps_all_access_without_package_filter():
    access = {
        "AG": {"permission": 1, "limit": 1},
        "SCL": {"permission": 1, "limit": 1},
    }

    response = build_student_report_response(
        [{"stu_id": 1, "user_id": 10, "access": access}],
    )

    assert response[0]["access"] == access
