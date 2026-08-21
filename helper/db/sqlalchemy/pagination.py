from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


@dataclass(frozen=True)
class Page:
    items: list[dict[str, Any]]
    page: int
    page_size: int
    total: int

    @property
    def pages(self) -> int:
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


def normalize_page(page: int | str | None, page_size: int | str | None) -> tuple[int, int]:
    try:
        normalized_page = int(page or DEFAULT_PAGE)
    except (TypeError, ValueError):
        normalized_page = DEFAULT_PAGE

    try:
        normalized_page_size = int(page_size or DEFAULT_PAGE_SIZE)
    except (TypeError, ValueError):
        normalized_page_size = DEFAULT_PAGE_SIZE

    normalized_page = max(1, normalized_page)
    normalized_page_size = min(MAX_PAGE_SIZE, max(1, normalized_page_size))
    return normalized_page, normalized_page_size


def paginate_mappings(
    session: Session,
    statement: Select,
    page: int | str | None = None,
    page_size: int | str | None = None,
) -> Page:
    normalized_page, normalized_page_size = normalize_page(page, page_size)
    count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
    total = int(session.execute(count_statement).scalar_one() or 0)

    rows = session.execute(
        statement.offset((normalized_page - 1) * normalized_page_size).limit(normalized_page_size)
    ).mappings().all()

    return Page(
        items=[dict(row) for row in rows],
        page=normalized_page,
        page_size=normalized_page_size,
        total=total,
    )
