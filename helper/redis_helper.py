from __future__ import annotations

from walrus import Database

from config import REDIS_DB, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT


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
    except Exception as e:
        print(f"[Redis] Connection failed: {e}")
        raise


async def close_redis_connection(redis_db: Database | None) -> None:
    try:
        if redis_db is not None:
            redis_db.close()
    except Exception as e:
        print(f"[Redis] Error closing connection: {e}")
