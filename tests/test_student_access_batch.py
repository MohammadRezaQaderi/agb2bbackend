import json
from contextlib import contextmanager

from helper import student_access


@contextmanager
def fake_session_scope():
    yield object()


def test_batch_access_updates_all_packages_in_one_student_document(monkeypatch):
    consumed = []
    saved = []
    updated = []

    monkeypatch.setattr(student_access, "session_scope", fake_session_scope)
    monkeypatch.setattr(
        student_access,
        "get_student_access_for_relation",
        lambda **_kwargs: {
            "owner_user_id": 50,
            "consultant_user_id": 70,
            "access": '{"AG": {"permission": 1, "limit": 1}}',
        },
    )
    monkeypatch.setattr(student_access, "list_student_package_access", lambda **_kwargs: [])
    monkeypatch.setattr(
        student_access,
        "get_capacity_package",
        lambda **_kwargs: {"allowed": 5, "used": 0},
    )
    monkeypatch.setattr(
        student_access,
        "consume_capacity_package",
        lambda _session, _user_id, package_name: consumed.append(package_name) or 1,
    )
    monkeypatch.setattr(
        student_access,
        "save_student_package_access",
        lambda **kwargs: saved.append(kwargs),
    )
    monkeypatch.setattr(
        student_access,
        "update_student_access",
        lambda **kwargs: updated.append(kwargs) or 1,
    )
    monkeypatch.setattr(student_access, "get_tracking_code", lambda: "tracking")

    token, data, message = student_access.update_student_accesses_and_capacity(
        request_data={
            "updates": [
                {"stu_id": 100, "kind": "PSY_ANX", "permission": 1, "limit": 0},
                {"stu_id": 100, "kind": "PSY_MBTI", "permission": 1, "limit": 1},
            ]
        },
        user_info={"user_id": 50},
        role_type="ins",
        id_field="owner_user_id",
        end_point="ag_api/ins",
    )

    assert token == "tracking"
    assert data == {"updated": 2, "students": 1}
    assert message == "دسترسی‌ها با موفقیت به‌روزرسانی شدند."
    assert consumed == ["PSY_ANX", "PSY_MBTI"]
    assert [item["package_name"] for item in saved] == ["PSY_ANX", "PSY_MBTI"]
    assert len(updated) == 1
    access = json.loads(updated[0]["access_json"])
    assert access["AG"] == {"permission": 1, "limit": 1}
    assert access["PSY_ANX"] == {"permission": 1, "limit": 0}
    assert access["PSY_MBTI"] == {"permission": 1, "limit": 1}


def test_batch_access_validates_all_capacity_before_writing(monkeypatch):
    writes = []
    monkeypatch.setattr(student_access, "session_scope", fake_session_scope)
    monkeypatch.setattr(
        student_access,
        "get_student_access_for_relation",
        lambda **_kwargs: {
            "owner_user_id": 50,
            "consultant_user_id": 70,
            "access": "{}",
        },
    )
    monkeypatch.setattr(student_access, "list_student_package_access", lambda **_kwargs: [])
    monkeypatch.setattr(
        student_access,
        "get_capacity_package",
        lambda **kwargs: {"allowed": 0 if kwargs["package_name"] == "PSY_MBTI" else 5, "used": 0},
    )
    monkeypatch.setattr(
        student_access,
        "consume_capacity_package",
        lambda *_args: writes.append("consume") or 1,
    )
    monkeypatch.setattr(
        student_access,
        "save_student_package_access",
        lambda **_kwargs: writes.append("save"),
    )
    monkeypatch.setattr(
        student_access,
        "update_student_access",
        lambda **_kwargs: writes.append("update") or 1,
    )

    token, data, message = student_access.update_student_accesses_and_capacity(
        request_data={
            "updates": [
                {"stu_id": 100, "kind": "PSY_ANX", "permission": 1, "limit": 0},
                {"stu_id": 100, "kind": "PSY_MBTI", "permission": 1, "limit": 0},
            ]
        },
        user_info={"user_id": 50},
        role_type="ins",
        id_field="owner_user_id",
        end_point="ag_api/ins",
    )

    assert token is None
    assert data is None
    assert "ظرفیت" in message
    assert writes == []
