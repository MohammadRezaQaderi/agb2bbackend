from services.student import student_service


def test_student_psy_catalog_returns_only_granted_packages_with_progress(monkeypatch):
    monkeypatch.setattr(
        student_service,
        "_load_student_access",
        lambda _user_id: {
            "AG": {"permission": 1, "limit": 1},
            "PSY_ANX": {"permission": 1, "limit": 1},
            "PSY_DEP": {"permission": 0, "limit": 0},
        },
    )
    monkeypatch.setattr(
        student_service,
        "build_psy_catalog",
        lambda _dashboard, package_names: {
            "packages": [
                {
                    "package_name": package_names[0],
                    "quiz_count": 2,
                }
            ]
        },
    )
    monkeypatch.setattr(
        student_service.answer_store,
        "get_attempts",
        lambda _user_id, _kind: [
            {"quiz_id": 1, "state": 2},
            {"quiz_id": 2, "state": 1},
        ],
    )
    monkeypatch.setattr(student_service, "get_tracking_code", lambda: "tracking")

    token, catalog, message = student_service.select_student_psy_catalog(
        request_data={},
        info={"user_id": 10},
    )

    assert token == "tracking"
    assert message == ""
    assert [item["package_name"] for item in catalog["packages"]] == ["PSY_ANX"]
    assert catalog["packages"][0]["student_progress"] == {
        "state": "in-progress",
        "completed_quizzes": 1,
        "in_progress_quizzes": 1,
        "total_quizzes": 2,
        "percentage": 50,
        "report_permission": 1,
    }


def test_student_psy_catalog_marks_finished_package_completed(monkeypatch):
    monkeypatch.setattr(
        student_service,
        "_load_student_access",
        lambda _user_id: {"PSY_ANX": {"permission": 1, "limit": 0}},
    )
    monkeypatch.setattr(
        student_service,
        "build_psy_catalog",
        lambda _dashboard, package_names: {"packages": [{"package_name": package_names[0], "quiz_count": 2}]},
    )
    monkeypatch.setattr(
        student_service.answer_store,
        "get_attempts",
        lambda _user_id, _kind: [
            {"quiz_id": 1, "state": 2},
            {"quiz_id": 2, "state": 2},
        ],
    )
    monkeypatch.setattr(student_service, "get_tracking_code", lambda: "tracking")

    _, catalog, _ = student_service.select_student_psy_catalog({}, {"user_id": 10})

    progress = catalog["packages"][0]["student_progress"]
    assert progress["state"] == "completed"
    assert progress["percentage"] == 100


def test_student_psy_catalog_does_not_fall_back_to_all_packages(monkeypatch):
    monkeypatch.setattr(
        student_service,
        "_load_student_access",
        lambda _user_id: {"AG": {"permission": 1, "limit": 1}},
    )
    monkeypatch.setattr(student_service, "get_tracking_code", lambda: "tracking")

    token, catalog, message = student_service.select_student_psy_catalog({}, {"user_id": 10})

    assert token == "tracking"
    assert message == ""
    assert catalog == {"packages": []}
