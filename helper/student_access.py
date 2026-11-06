import json
import logging
from typing import Any, Mapping, Optional, Tuple

from helper.constants import PACKAGES_DATA, get_kind_name
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.students import (
    consume_capacity_package,
    count_student_packages_for_relation,
    get_capacity_package,
    get_student_access_for_relation,
    list_student_package_access,
    save_student_package_access,
    update_student_access,
)
from helper.service_errors import service_exception_error_logging
from helper.tracking import get_tracking_code


logger = logging.getLogger(__name__)


def upsert_student_package_access(
        stu_user_id: int,
        owner_user_id: int | None,
        consultant_user_id: int | None,
        package_name: str,
        permission: int,
        limit: int,
) -> None:
    try:
        with session_scope() as session:
            save_student_package_access(
                session=session,
                stu_user_id=stu_user_id,
                owner_user_id=owner_user_id,
                consultant_user_id=consultant_user_id,
                package_name=package_name,
                permission=permission,
                limit=limit,
            )
    except Exception:
        # The new table is additive. Keep the old JSON path working if a deployment
        # temporarily runs before the schema migration.
        logger.exception("student_package_access sync skipped")


def get_student_package_access_counts(
        user_id: int,
        relation_column: str,
) -> dict[str, int] | None:
    if relation_column not in {"owner_user_id", "consultant_user_id"}:
        return None

    try:
        with session_scope() as session:
            return count_student_packages_for_relation(
                session=session,
                relation_column=relation_column,
                user_id=user_id,
            )
    except Exception:
        logger.exception("student_package_access count fallback")
        return None


def _parse_access(raw_access: Any) -> dict[str, Any]:
    if isinstance(raw_access, dict):
        return dict(raw_access)
    if not raw_access:
        return {}
    try:
        parsed = json.loads(raw_access)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _access_flag(value: Any) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    return 1 if int(value or 0) else 0


def _access_limit(value: Any) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    return max(0, int(value or 0))


def _is_granted(access: Mapping[str, Any], package_name: str) -> bool:
    value = access.get(package_name)
    if isinstance(value, dict):
        return bool(value.get("permission", 0))
    return bool(value)


def _prepare_access_updates(request_data: Mapping[str, Any]) -> tuple[list[dict[str, int | str]] | None, str]:
    raw_updates = request_data.get("updates")
    if not isinstance(raw_updates, list) or not raw_updates:
        return None, "حداقل یک تغییر دسترسی باید ارسال شود."
    if len(raw_updates) > 1000:
        return None, "تعداد تغییرات دسترسی بیشتر از حد مجاز است."

    prepared_by_key: dict[tuple[int, str], dict[str, int | str]] = {}
    try:
        for raw_update in raw_updates:
            if not isinstance(raw_update, Mapping):
                return None, "ساختار تغییرات دسترسی معتبر نیست."

            stu_user_id = int(raw_update.get("stu_id") or 0)
            package_name = str(raw_update.get("kind") or "").strip().upper()
            if stu_user_id <= 0:
                return None, "شناسه دانش‌آموز معتبر نیست."
            if package_name not in PACKAGES_DATA:
                return None, f"نوع بسته {package_name} معتبر نیست."

            prepared_by_key[(stu_user_id, package_name)] = {
                "stu_id": stu_user_id,
                "kind": package_name,
                "permission": _access_flag(raw_update.get("permission", 0)),
                "limit": _access_limit(raw_update.get("limit", 0)),
            }
    except (TypeError, ValueError):
        return None, "مقادیر تغییر دسترسی معتبر نیست."

    return list(prepared_by_key.values()), ""


def update_student_accesses_and_capacity(
    request_data: Mapping[str, Any],
    user_info: Mapping[str, Any],
    role_type: str,
    id_field: str,
    end_point: str,
) -> Tuple[Optional[str], Optional[dict], str]:
    """Apply a group of student/package access changes in one transaction."""
    updates, validation_error = _prepare_access_updates(request_data)
    if updates is None:
        return None, None, validation_error

    try:
        user_id = int(user_info["user_id"])
        with session_scope() as session:
            students: dict[int, dict[str, Any]] = {}
            for stu_user_id in {int(update["stu_id"]) for update in updates}:
                student = get_student_access_for_relation(session=session, stu_user_id=stu_user_id)
                if student is None:
                    return None, None, "دانش‌آموز یافت نشد."
                if student.get(id_field) != user_id:
                    return None, None, "این دانش‌آموز به شما تعلق ندارد."

                access = _parse_access(student.get("access"))
                for normalized in list_student_package_access(session=session, user_id=stu_user_id):
                    package_name = str(normalized.get("package_name") or "").upper()
                    if package_name:
                        access[package_name] = {
                            "permission": int(normalized.get("permission") or 0),
                            "limit": int(normalized.get("limit") or 0),
                        }
                students[stu_user_id] = {**student, "access": access}

            required_capacity: dict[str, int] = {}
            for update in updates:
                stu_user_id = int(update["stu_id"])
                package_name = str(update["kind"])
                is_granting = bool(update["permission"])
                was_granted = _is_granted(students[stu_user_id]["access"], package_name)
                if is_granting and not was_granted:
                    required_capacity[package_name] = required_capacity.get(package_name, 0) + 1

            for package_name, required in required_capacity.items():
                capacity = get_capacity_package(session=session, user_id=user_id, package_name=package_name)
                if not capacity:
                    return None, None, f"بسته {get_kind_name(package_name)} برای شما تعریف نشده است."
                if int(capacity.get("allowed") or 0) < required:
                    return None, None, f"ظرفیت بسته {get_kind_name(package_name)} تکمیل شده است."

            for update in updates:
                stu_user_id = int(update["stu_id"])
                package_name = str(update["kind"])
                permission = int(update["permission"])
                limit = int(update["limit"])
                student = students[stu_user_id]
                was_granted = _is_granted(student["access"], package_name)

                if permission and not was_granted:
                    if consume_capacity_package(session, user_id, package_name) != 1:
                        raise RuntimeError(f"Failed to consume capacity for {package_name}")

                student["access"][package_name] = {
                    "permission": permission,
                    "limit": limit,
                }
                save_student_package_access(
                    session=session,
                    stu_user_id=stu_user_id,
                    owner_user_id=student.get("owner_user_id"),
                    consultant_user_id=student.get("consultant_user_id"),
                    package_name=package_name,
                    permission=permission,
                    limit=limit,
                )

            for stu_user_id, student in students.items():
                update_student_access(
                    session=session,
                    stu_user_id=stu_user_id,
                    access_json=json.dumps(student["access"], ensure_ascii=False),
                )

        return (
            get_tracking_code(),
            {"updated": len(updates), "students": len(students)},
            "دسترسی‌ها با موفقیت به‌روزرسانی شدند.",
        )
    except Exception as exc:
        service_exception_error_logging(
            end_point,
            f"update_student_accesses_and_capacity_{role_type}",
            str(exc),
            request_data,
            user_info,
        )
        return None, None, "مشکلی در به‌روزرسانی دسترسی دانش‌آموز رخ داده است."


def update_student_access_and_capacity(
    request_data: Mapping[str, Any],
    user_info: Mapping[str, Any],
    role_type: str,
    id_field: str,
    end_point: str,
) -> Tuple[Optional[str], Optional[dict], str]:
    update = {
        "stu_id": request_data.get("stu_id"),
        "kind": request_data.get("kind"),
        "permission": request_data.get("permission", 0),
        "limit": request_data.get("limit", 0),
    }
    return update_student_accesses_and_capacity(
        request_data={"updates": [update]},
        user_info=user_info,
        role_type=role_type,
        id_field=id_field,
        end_point=end_point,
    )
