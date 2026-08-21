from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StudentFilters:
    search: str | None = None
    sex: int | None = None
    city: str | None = None
    package_name: str | None = None
    access_permission: int | None = None

    @classmethod
    def from_request(cls, request_data: dict | None) -> "StudentFilters":
        request_data = request_data or {}
        return cls(
            search=_clean_string(request_data.get("search")),
            sex=_clean_int(request_data.get("sex")),
            city=_clean_string(request_data.get("city")),
            package_name=_clean_string(request_data.get("package_name")),
            access_permission=_clean_int(request_data.get("access_permission")),
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
