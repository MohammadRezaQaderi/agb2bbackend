from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StudentFilters:
    search: str | None = None
    name: str | None = None
    phone: str | None = None
    consultant_name: str | None = None
    education: str | None = None
    sex: int | None = None
    city: str | None = None
    package_name: str | None = None
    access_permission: int | None = None
    archived: bool = False

    @classmethod
    def from_request(cls, request_data: dict | None) -> "StudentFilters":
        request_data = request_data or {}
        column_filters = request_data.get("filters")
        if not isinstance(column_filters, dict):
            column_filters = {}

        def value(*keys: str):
            for key in keys:
                if key in request_data:
                    return request_data[key]
                if key in column_filters:
                    return column_filters[key]
            return None

        return cls(
            search=_clean_string(value("search")),
            name=_clean_string(value("name", "full_name")),
            phone=_clean_string(value("phone")),
            consultant_name=_clean_string(value("consultant_name", "con_name")),
            education=_clean_string(value("education")),
            sex=_clean_int(value("sex")),
            city=_clean_string(value("city")),
            package_name=_clean_string(value("package_name")),
            access_permission=_clean_int(value("access_permission")),
            archived=_clean_bool(value("archived", "is_archived")) is True,
        )


@dataclass(frozen=True)
class ConsultantFilters:
    search: str | None = None
    name: str | None = None
    phone: str | None = None
    sex: int | None = None

    @classmethod
    def from_request(cls, request_data: dict | None) -> "ConsultantFilters":
        request_data = request_data or {}
        column_filters = request_data.get("filters")
        if not isinstance(column_filters, dict):
            column_filters = {}

        def value(*keys: str):
            for key in keys:
                if key in request_data:
                    return request_data[key]
                if key in column_filters:
                    return column_filters[key]
            return None

        return cls(
            search=_clean_string(value("search")),
            name=_clean_string(value("name", "full_name")),
            phone=_clean_string(value("phone")),
            sex=_clean_int(value("sex")),
        )


def _clean_string(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _clean_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clean_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no", ""}:
            return False
    return None
