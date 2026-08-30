from __future__ import annotations

from sqlalchemy.orm import Session

from helper.db.sqlalchemy.queries.auth import create_user
from helper.db.sqlalchemy.queries.consultants import create_consultant_profile
from helper.db.sqlalchemy.queries.institutes import create_institute_profile
from helper.db.sqlalchemy.queries.owner_consultants import create_owner_consultant_profile
from helper.db.sqlalchemy.queries.schools import create_school_profile
from helper.db.sqlalchemy.queries.students import create_capacity_with_packages, create_student_profile


def create_signup_account(
    session: Session,
    phone: str,
    encrypted_password: str,
    role: str,
    request_data: dict,
    package_names: list[str],
) -> int:
    user_id = create_user(session=session, phone=phone, password=encrypted_password, role=role)

    if role == "ins":
        create_institute_profile(session=session, user_id=user_id, name=request_data["name"])
    elif role == "sch":
        create_school_profile(session=session, user_id=user_id, name=request_data["name"])
    elif role == "ocon":
        create_owner_consultant_profile(
            session=session,
            user_id=user_id,
            first_name=request_data["first_name"],
            last_name=request_data["last_name"],
            sex=request_data.get("sex") or 1,
        )
    else:
        raise ValueError(f"Unsupported signup role: {role}")

    create_capacity_with_packages(session=session, user_id=user_id, package_names=package_names)
    return user_id


def create_consultant_account(
    session: Session,
    phone: str,
    encrypted_password: str,
    request_data: dict,
    owner_user_id: int,
) -> int:
    user_id = create_user(session=session, phone=phone, password=encrypted_password, role="con")
    create_consultant_profile(
        session=session,
        user_id=user_id,
        owner_user_id=owner_user_id,
        editor_id=owner_user_id,
        first_name=request_data["first_name"],
        last_name=request_data["last_name"],
        sex=request_data["sex"],
    )
    return user_id


def create_student_account(
    session: Session,
    phone: str,
    encrypted_password: str,
    request_data: dict,
    user_info: dict,
) -> int:
    role = user_info["role"]
    if role in {"ins", "sch"}:
        owner_user_id = user_info["user_id"]
        consultant_user_id = request_data["con_id"]
    elif role == "ocon":
        owner_user_id = request_data["user_id"]
        consultant_user_id = user_info["user_id"]
    else:
        raise ValueError(f"Unsupported student owner role: {role}")

    user_id = create_user(session=session, phone=phone, password=encrypted_password, role="stu")
    create_student_profile(
        session=session,
        user_id=user_id,
        owner_user_id=owner_user_id,
        consultant_user_id=consultant_user_id,
        adder_id=user_info["user_id"],
        first_name=request_data["first_name"],
        last_name=request_data["last_name"],
        sex=request_data["sex"],
        city=request_data["city"],
        birth_date=request_data["birth_date"],
    )
    return user_id
