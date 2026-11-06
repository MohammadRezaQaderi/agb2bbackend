from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from helper.db.sqlalchemy import listing
from helper.db.sqlalchemy.base import Base
from helper.db.sqlalchemy.filters import ConsultantFilters, StudentFilters
from helper.db.sqlalchemy.models import Consultant, Student, StudentPackageAccess, User
from helper.db.sqlalchemy.pagination import Page, is_paginated_request, page_payload
from helper.db.sqlalchemy.queries.consultants import paginate_consultants_for_owner
from helper.db.sqlalchemy.queries.students import paginate_students


def test_student_filters_accept_material_table_column_filters():
    filters = StudentFilters.from_request(
        {
            "search": "احمد",
            "filters": {
                "full_name": "رضا",
                "phone": "0912",
                "con_name": "محمدی",
                "education": "دوره دوم تجربی",
            },
        }
    )

    assert filters.search == "احمد"
    assert filters.name == "رضا"
    assert filters.phone == "0912"
    assert filters.consultant_name == "محمدی"
    assert filters.education == "دوره دوم تجربی"


def test_consultant_filters_accept_material_table_column_filters():
    filters = ConsultantFilters.from_request({"filters": {"full_name": "هادی", "phone": "0900"}})

    assert filters.name == "هادی"
    assert filters.phone == "0900"


def test_pagination_request_and_payload_are_backward_compatible():
    page = Page(items=[{"user_id": 1}], page=2, page_size=20, total=45)

    assert not is_paginated_request({})
    assert is_paginated_request({"paginated": "true"})
    assert page_payload(page, page.items) == {
        "items": [{"user_id": 1}],
        "page": 2,
        "page_size": 20,
        "total": 45,
        "pages": 3,
    }


def test_student_listing_only_paginates_when_requested(monkeypatch):
    monkeypatch.setattr(listing, "list_students", lambda **_kwargs: [{"user_id": 1}])
    monkeypatch.setattr(listing, "list_student_package_access_for_users", lambda **_kwargs: {})
    monkeypatch.setattr(
        listing,
        "paginate_students",
        lambda **_kwargs: Page(items=[{"user_id": 2}], page=1, page_size=20, total=21),
    )

    rows, page = listing.fetch_students_for_request(object(), "owner", 10, {})
    assert rows == [{"user_id": 1}]
    assert page is None

    rows, page = listing.fetch_students_for_request(
        object(),
        "owner",
        10,
        {"paginated": True, "page": 1, "page_size": 20},
    )
    assert rows == [{"user_id": 2}]
    assert page is not None
    assert page.total == 21


def test_student_listing_merges_normalized_package_access(monkeypatch):
    monkeypatch.setattr(
        listing,
        "list_student_package_access_for_users",
        lambda **_kwargs: {
            30: {
                "PSY_ANX": {"permission": 1, "limit": 0},
                "PSY_MBTI": {"permission": 1, "limit": 1},
            }
        },
    )
    students = [{"user_id": 30, "access": '{"AG": {"permission": 1, "limit": 1}}'}]

    result = listing.attach_normalized_student_access(object(), students)

    assert result[0]["access"] == {
        "AG": {"permission": 1, "limit": 1},
        "PSY_ANX": {"permission": 1, "limit": 0},
        "PSY_MBTI": {"permission": 1, "limit": 1},
    }


def test_student_pagination_applies_scope_product_filters_and_sorting():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add_all(
            [
                User(user_id=10, phone="owner", password="x", role="ins"),
                User(user_id=20, phone="consultant", password="x", role="con"),
                User(user_id=30, phone="09120000001", password="x", role="stu"),
                User(user_id=31, phone="09120000002", password="x", role="stu"),
                User(user_id=32, phone="09120000003", password="x", role="stu"),
                Consultant(
                    user_id=20,
                    owner_user_id=10,
                    first_name="هادی",
                    last_name="آبادی",
                    sex=0,
                ),
                Student(
                    user_id=30,
                    owner_user_id=10,
                    consultant_user_id=20,
                    first_name="علی",
                    last_name="نمونه",
                    education_level="second",
                    education_field="experimental",
                ),
                Student(
                    user_id=31,
                    owner_user_id=10,
                    consultant_user_id=20,
                    first_name="رضا",
                    last_name="تست",
                    education_level="first",
                ),
                Student(
                    user_id=32,
                    owner_user_id=10,
                    consultant_user_id=20,
                    first_name="بدون",
                    last_name="تحصیلات",
                ),
                StudentPackageAccess(
                    id=1,
                    stu_user_id=30,
                    owner_user_id=10,
                    consultant_user_id=20,
                    package_name="AG",
                    permission=1,
                    limit=1,
                ),
            ]
        )
        session.commit()

        page = paginate_students(
            session=session,
            scope="owner",
            user_id=10,
            filters=StudentFilters.from_request(
                {
                    "package_name": "AG",
                    "access_permission": 1,
                    "filters": {
                        "con_name": "هادی آبادی",
                        "education": "دوره دوم تجربی",
                    },
                }
            ),
            page=1,
            page_size=20,
            sort_by="full_name",
            sort_direction="asc",
        )
        consultant_page = paginate_consultants_for_owner(
            session=session,
            owner_user_id=10,
            filters=ConsultantFilters.from_request({"filters": {"full_name": "هادی آبادی", "phone": "consultant"}}),
            page=1,
            page_size=20,
            sort_by="full_name",
            sort_direction="asc",
        )
        missing_education_page = paginate_students(
            session=session,
            scope="owner",
            user_id=10,
            filters=StudentFilters.from_request({"filters": {"education": "ثبت نشده"}}),
            page=99,
            page_size=20,
        )

    assert page.total == 1
    assert page.pages == 1
    assert page.items[0]["user_id"] == 30
    assert consultant_page.total == 1
    assert consultant_page.items[0]["user_id"] == 20
    assert missing_education_page.total == 1
    assert missing_education_page.page == 1
    assert missing_education_page.items[0]["user_id"] == 32
