from contextlib import nullcontext
from unittest.mock import Mock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from helper.db.sqlalchemy.base import Base
from helper.db.sqlalchemy.filters import StudentFilters
from helper.db.sqlalchemy.models import Student, User
from helper.db.sqlalchemy.queries.auth import get_user_auth_by_phone
from helper.db.sqlalchemy.queries.dashboard import count_students_for_scope
from helper.db.sqlalchemy.queries.students import (
    get_student_legacy_access,
    get_student_profile,
    list_student_options,
    list_students_without_package_access,
    paginate_students,
    set_student_archive_state,
)
import services.management_gateway as management_gateway
import services.student_management_service as student_management_service


def _seed_students(session):
    session.add_all(
        [
            User(user_id=10, phone="owner", password="x", role="ins"),
            User(user_id=20, phone="ocon", password="x", role="ocon"),
            User(user_id=30, phone="09120000001", password="x", role="stu"),
            User(user_id=31, phone="09120000002", password="x", role="stu"),
            Student(
                user_id=30,
                owner_user_id=10,
                consultant_user_id=20,
                first_name="فعال",
                last_name="نمونه",
            ),
            Student(
                user_id=31,
                owner_user_id=10,
                consultant_user_id=20,
                first_name="بایگانی",
                last_name="نمونه",
                access='{"AG":{"permission":1,"limit":1}}',
                is_archived=True,
                archived_by=10,
            ),
        ]
    )
    session.commit()


def test_student_lists_default_to_active_and_support_archived_only():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        _seed_students(session)
        active_page = paginate_students(
            session=session,
            scope="owner",
            user_id=10,
            filters=StudentFilters(),
            page=1,
            page_size=20,
        )
        archived_page = paginate_students(
            session=session,
            scope="owner",
            user_id=10,
            filters=StudentFilters(archived=True),
            page=1,
            page_size=20,
        )
        options = list_student_options(session=session, scope="owner", user_id=10)
        access_options = list_students_without_package_access(
            session=session,
            scope="owner",
            user_id=10,
            package_name="AG",
        )

        assert [row["user_id"] for row in active_page.items] == [30]
        assert [row["user_id"] for row in archived_page.items] == [31]
        assert [row["user_id"] for row in options] == [30]
        assert [row["stu_id"] for row in access_options] == [30]
        assert count_students_for_scope(session, "owner", 10) == 1


def test_archive_state_is_owned_reversible_and_idempotent():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        _seed_students(session)

        archived = set_student_archive_state(
            session=session,
            student_user_id=30,
            scope="owner",
            actor_user_id=10,
            archived=True,
        )
        archived_again = set_student_archive_state(
            session=session,
            student_user_id=30,
            scope="owner",
            actor_user_id=10,
            archived=True,
        )
        unrelated = set_student_archive_state(
            session=session,
            student_user_id=30,
            scope="owner",
            actor_user_id=999,
            archived=False,
        )
        restored = set_student_archive_state(
            session=session,
            student_user_id=30,
            scope="consultant",
            actor_user_id=20,
            archived=False,
        )
        restored_again = set_student_archive_state(
            session=session,
            student_user_id=30,
            scope="consultant",
            actor_user_id=20,
            archived=False,
        )

        assert archived["changed"] is True
        assert archived["is_archived"] is True
        assert archived["archived_by"] == 10
        assert archived["archived_at"] is not None
        assert archived_again["changed"] is False
        assert archived_again["archived_at"] == archived["archived_at"]
        assert unrelated is None
        assert restored == {
            "student_id": 30,
            "is_archived": False,
            "archived_at": None,
            "archived_by": None,
            "changed": True,
        }
        assert restored_again == {**restored, "changed": False}


def test_archived_student_login_profile_and_access_remain_available():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        _seed_students(session)
        auth = get_user_auth_by_phone(session=session, phone="09120000002")
        profile = get_student_profile(session=session, user_id=31)
        access = get_student_legacy_access(session=session, user_id=31)

    assert auth is not None
    assert auth["role"] == "stu"
    assert profile is not None
    assert profile["user_id"] == 31
    assert profile["phone"] == "09120000002"
    assert access == '{"AG":{"permission":1,"limit":1}}'


def test_archive_service_allows_only_ins_and_ocon(monkeypatch):
    set_state = Mock(
        return_value={
            "student_id": 30,
            "is_archived": True,
            "archived_at": None,
            "archived_by": 10,
            "changed": True,
        }
    )
    monkeypatch.setattr(student_management_service, "set_student_archive_state", set_state)
    monkeypatch.setattr(
        student_management_service,
        "session_scope",
        lambda: nullcontext(Mock()),
    )

    tracking_code, data, message = student_management_service.archive_student(
        {"student_id": 30},
        {"user_id": 10, "role": "ins"},
    )
    denied = student_management_service.archive_student(
        {"student_id": 30},
        {"user_id": 10, "role": "sch"},
    )

    assert tracking_code
    assert data["is_archived"] is True
    assert message == "دانش‌آموز با موفقیت بایگانی شد."
    assert set_state.call_args.kwargs["scope"] == "owner"
    assert denied[0] is None


def test_archive_gateway_rejects_unauthorized_roles():
    response = management_gateway.archive_student(
        {"student_id": 30},
        {"user_id": 10, "role": "con"},
    )
    archived_list_response = management_gateway.get_students(
        {"archived": True},
        {"user_id": 10, "role": "sch"},
    )
    archived_alias_response = management_gateway.get_students(
        {"filters": {"is_archived": "true"}},
        {"user_id": 10, "role": "con"},
    )

    assert response["tracking_code"] is None
    assert archived_list_response["tracking_code"] is None
    assert archived_alias_response["tracking_code"] is None
