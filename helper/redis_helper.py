from __future__ import annotations

import logging

from walrus import Database

from config import REDIS_DB, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT


logger = logging.getLogger(__name__)


async def redis_connection() -> Database:
    try:
        redis_db: Database = Database(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD if REDIS_PASSWORD else None,
        )
        redis_db.ping()
        return redis_db
    except Exception:
        logger.exception("Redis connection failed")
        raise


async def close_redis_connection(redis_db: Database | None) -> None:
    try:
        if redis_db is not None:
            redis_db.close()
    except Exception:
        logger.exception("Error closing Redis connection")
