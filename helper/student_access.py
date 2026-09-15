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


def update_student_access_and_capacity(
        request_data: Mapping[str, Any],
        user_info: Mapping[str, Any],
        role_type: str,
        id_field: str,
        end_point: str,
) -> Tuple[Optional[str], Optional[dict], str]:
    """
    Update student access permissions and manage capacity tracking.

    Access is stored in format: {"AG": {"permission": 1, "limit": 1}}.
    """
    try:
        user_id = user_info["user_id"]
        stu_id = request_data.get("stu_id")

        if not stu_id:
            return None, None, "شناسه دانش‌آموز ارسال نشده است."

        with session_scope() as session:
            res_stu = get_student_access_for_relation(session=session, stu_user_id=int(stu_id))

        if res_stu is None:
            return None, None, "دانش‌آموز یافت نشد."

        org_id = res_stu.get(id_field)
        if org_id != user_id:
            return None, None, "این دانش‌آموز به شما تعلق ندارد."

        current_access_str = res_stu.get("access") or '{}'
        try:
            current_access = json.loads(current_access_str) if current_access_str else {}
        except (json.JSONDecodeError, TypeError):
            current_access = {}

        kind = str(request_data.get("kind") or "").upper()
        if not kind:
            return None, None, "نوع بسته (kind) ارسال نشده است."

        if kind not in PACKAGES_DATA:
            valid_packages = "، ".join(f"{package} ({get_kind_name(package)})" for package in PACKAGES_DATA.keys())
            return None, None, f"نوع بسته {kind} معتبر نیست. بسته‌های معتبر: {valid_packages}"

        permission = request_data.get("permission", 0)
        limit = request_data.get("limit", 0)

        if isinstance(permission, bool):
            permission = 1 if permission else 0
        else:
            permission = int(permission) if permission else 0

        if isinstance(limit, bool):
            limit = 1 if limit else 0
        else:
            limit = int(limit) if limit else 0

        package_exists = kind in current_access

        was_granted = False
        if package_exists:
            prev_data = current_access.get(kind, {})
            if isinstance(prev_data, dict):
                was_granted = bool(prev_data.get("permission", 0))
            else:
                was_granted = bool(prev_data)

        if package_exists:
            current_package_data = current_access[kind]
            if isinstance(current_package_data, dict):
                current_package_data["limit"] = limit
                current_package_data["permission"] = permission
            else:
                current_access[kind] = {
                    "permission": permission,
                    "limit": limit
                }
        else:
            current_access[kind] = {
                "permission": permission,
                "limit": limit
            }

        updated_access_json = json.dumps(current_access, ensure_ascii=False)
        with session_scope() as session:
            is_granting = bool(permission)
            if is_granting != was_granted:
                res_capacity = get_capacity_package(session=session, user_id=user_id, package_name=kind)
                if not res_capacity:
                    return None, None, f"بسته {get_kind_name(kind=kind)} برای شما تعریف نشده است."

                allowed = int(res_capacity.get("allowed") or 0)
                if is_granting:
                    if allowed <= 0:
                        return None, None, f"ظرفیت بسته {get_kind_name(kind=kind)} تکمیل شده است."

                    consume_result = consume_capacity_package(session=session, user_id=user_id, package_name=kind)
                    if consume_result == -1:
                        return None, None, f"ظرفیت بسته {get_kind_name(kind=kind)} تکمیل شده است."
                    if consume_result == 0:
                        return None, None, f"بسته {get_kind_name(kind=kind)} برای شما تعریف نشده است."

            update_student_access(session=session, stu_user_id=int(stu_id), access_json=updated_access_json)
            save_student_package_access(
                session=session,
                stu_user_id=int(stu_id),
                owner_user_id=res_stu.get("owner_user_id"),
                consultant_user_id=res_stu.get("consultant_user_id"),
                package_name=kind,
                permission=permission,
                limit=limit,
            )

        token = get_tracking_code()
        return token, None, "دسترسی دانش‌آموز با موفقیت به‌روزرسانی شد."

    except Exception as e:
        service_exception_error_logging(
            end_point,
            f"update_student_access_and_capacity_{role_type}",
            str(e),
            request_data,
            user_info,
        )
        return None, None, "مشکلی در به‌روزرسانی دسترسی دانش‌آموز رخ داده است."
