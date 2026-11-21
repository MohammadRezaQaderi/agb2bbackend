import json
from contextlib import nullcontext
from unittest.mock import Mock

import services.student.student_service as student_service
import services.student_management_service as management_service


def test_student_dashboard_includes_scl_scores(monkeypatch):
    monkeypatch.setattr(
        student_service,
        "_load_student_access",
        lambda _user_id: {
            "AG": {"permission": 1, "limit": 1},
            "SCL": {"permission": 1, "limit": 1},
        },
    )
    monkeypatch.setattr(
        student_service,
        "get_package_quiz_counts",
        lambda _packages: {"AG": 7, "SCL": 4},
    )
    monkeypatch.setattr(
        student_service,
        "list_quiz_attempts_for_users",
        lambda **_kwargs: [
            {"user_id": 9324, "quiz_kind": "SCL", "quiz_id": quiz_id, "state": 2}
            for quiz_id in range(1, 5)
        ],
    )
    monkeypatch.setattr(
        student_service,
        "get_latest_ag_score_summary",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        student_service,
        "get_latest_scl_score_summary",
        lambda **_kwargs: {
            "scl_date": json.dumps(
                {
                    "adhd": {
                        "name": "بیش فعالی و عدم تمرکز",
                        "value": 0.5,
                    }
                }
            )
        },
    )
    monkeypatch.setattr(student_service, "get_result_state", lambda **_kwargs: None)
    monkeypatch.setattr(
        student_service,
        "session_scope",
        lambda: nullcontext(Mock()),
    )

    dashboard = student_service.load_student_dashboard_data(
        9324,
        include_notifications=False,
    )

    assert dashboard["scores"]["scl_date"]["adhd"]["value"] == 0.5
    assert dashboard["scores"]["SCL"]["scl_date"]["adhd"]["name"] == "بیش فعالی و عدم تمرکز"
    assert dashboard["quiz"]["SCL"] == {
        "completed": 4,
        "remaining": 0,
        "total": 4,
    }
    assert dashboard["access_state"]["SCL"]["state"] == "completed"


def test_management_student_options_use_role_scope(monkeypatch):
    options = [
        {
            "user_id": 9324,
            "first_name": "پوریا",
            "last_name": "شریفی",
            "phone": "09123456789",
        }
    ]
    list_options = Mock(return_value=options)
    monkeypatch.setattr(management_service, "list_student_options", list_options)
    monkeypatch.setattr(
        management_service,
        "session_scope",
        lambda: nullcontext(Mock()),
    )

    tracking_code, data, message = management_service.get_student_options(
        {},
        {"user_id": 1147, "role": "ins"},
    )

    assert tracking_code
    assert data == options
    assert message == ""
    assert list_options.call_args.kwargs["scope"] == "owner"
    assert list_options.call_args.kwargs["user_id"] == 1147


def test_management_student_detail_checks_relation(monkeypatch):
    monkeypatch.setattr(
        management_service,
        "session_scope",
        lambda: nullcontext(Mock()),
    )
    monkeypatch.setattr(
        management_service,
        "get_student_access_for_relation",
        lambda **_kwargs: {"owner_user_id": 1147, "consultant_user_id": 1155},
    )
    load_dashboard = Mock(return_value={"student_info": {"user_id": 9324}})
    monkeypatch.setattr(
        management_service,
        "load_student_dashboard_data",
        load_dashboard,
    )

    tracking_code, data, message = management_service.get_student_management(
        {"student_id": 9324},
        {"user_id": 1147, "role": "ins"},
    )

    assert tracking_code
    assert data["student_info"]["user_id"] == 9324
    assert message == ""
    load_dashboard.assert_called_once_with(
        9324,
        include_notifications=False,
        include_student_info=True,
    )
