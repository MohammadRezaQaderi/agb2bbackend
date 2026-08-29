from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session, sessionmaker

from helper.db.sqlalchemy.engine import get_engine


SessionLocal = sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


def create_session() -> Session:
    """Create a SQLAlchemy session bound to the shared engine."""
    return SessionLocal(bind=get_engine())


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional SQLAlchemy session scope."""
    session = create_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
