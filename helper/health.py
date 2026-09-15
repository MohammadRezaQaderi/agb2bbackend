import logging
import os
from datetime import datetime

from sqlalchemy import text

from config import REDIS_DB, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT
from helper.db.sqlalchemy import session_scope


logger = logging.getLogger(__name__)


async def health_payload(service_name: str):
    return await readiness_payload(service_name)


async def liveness_payload(service_name: str):
    instance_name = os.getenv("INSTANCE_NAME", "unknown")
    port = os.getenv("PORT", "unknown")
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": service_name,
        "instance": instance_name,
        "port": port,
        "version": "1.0.0"
    }


async def readiness_payload(service_name: str):
    instance_name = os.getenv("INSTANCE_NAME", "unknown")
    port = os.getenv("PORT", "unknown")
    try:
        with session_scope() as session:
            session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        logger.exception("Database readiness check failed")
        db_status = "error"

    checks = {"database": db_status}
    include_redis = os.getenv("AG_HEALTH_CHECK_REDIS", "").lower() in {"1", "true", "yes"}
    if include_redis:
        checks["redis"] = _redis_health_status()

    healthy = all(value == "connected" for value in checks.values())
    return {
        "status": "healthy" if healthy else "degraded",
        "timestamp": datetime.now().isoformat(),
        "service": service_name,
        "instance": instance_name,
        "port": port,
        "database": db_status,
        "checks": checks,
        "version": "1.0.0"
    }


def _redis_health_status() -> str:
    from walrus import Database

    redis_db = None
    try:
        redis_db = Database(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD if REDIS_PASSWORD else None,
        )
        redis_db.ping()
        return "connected"
    except Exception:
        logger.exception("Redis readiness check failed")
        return "error"
    finally:
        if redis_db is not None:
            try:
                redis_db.close()
            except Exception:
                logger.exception("Error closing Redis health-check connection")
