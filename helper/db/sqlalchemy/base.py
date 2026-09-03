from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_time: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now, nullable=True)
    edited_time: Mapped[datetime | None] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=True,
    )
