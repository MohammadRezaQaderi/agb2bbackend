from contextlib import nullcontext
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

import helper.health as health_helper
import routers.action_helpers as action_helpers
import routers.reports as reports
from routers.health import router as health_router


@pytest.fixture
def action_client():
    app = FastAPI()
    handler = Mock(return_value={"status": 200, "response": {"data": "ok"}})

    @app.post("/single")
    async def single(request: Request):
        return await action_helpers.dispatch_single_action(request, "SELECT", "known", handler)

    @app.post("/authenticated")
    async def authenticated(request: Request):
        return await action_helpers.dispatch_authenticated_action(request, "SELECT", {"known": handler})

    return TestClient(app), handler


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        ({"request_data": {}}, 405),
        ({"action_type": "known"}, 200),
        ({"action_type": "unknown", "request_data": {}}, 405),
    ],
)
def test_action_payload_validation(action_client, payload, expected_status):
    client, handler = action_client

    response = client.post("/single", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == expected_status
    handler.assert_not_called()


def test_rejected_auth_does_not_call_action(action_client, monkeypatch):
    client, handler = action_client
    authorizer = AsyncMock(return_value=(False, "session expired", None))
    monkeypatch.setattr(action_helpers.auth_context, "authorizer", authorizer)

    response = client.post("/authenticated", json={"action_type": "known", "request_data": {"token": "bad"}})

    assert response.json()["status"] == 404
    assert response.json()["error"] == "session expired"
    handler.assert_not_called()
    authorizer.assert_awaited_once()


def test_liveness_never_uses_database(monkeypatch):
    session_scope = Mock(side_effect=AssertionError("liveness opened a database session"))
    monkeypatch.setattr(health_helper, "session_scope", session_scope)
    client = TestClient(FastAPI())
    client.app.include_router(health_router)

    response = client.get("/ags_api/live")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "ags_api"
    session_scope.assert_not_called()


@pytest.mark.parametrize(("connected", "expected"), [(True, "healthy"), (False, "degraded")])
def test_readiness_reflects_database_state(monkeypatch, connected, expected):
    monkeypatch.delenv("AG_HEALTH_CHECK_REDIS", raising=False)
    if connected:
        session = Mock()
        monkeypatch.setattr(health_helper, "session_scope", lambda: nullcontext(session))
    else:
        monkeypatch.setattr(health_helper, "session_scope", Mock(side_effect=RuntimeError("db unavailable")))
    client = TestClient(FastAPI())
    client.app.include_router(health_router)

    response = client.get("/ag_api/ready")

    assert response.status_code == 200
    assert response.json()["status"] == expected
    assert response.json()["database"] == ("connected" if connected else "error")
    if connected:
        session.execute.assert_called_once()


@pytest.mark.parametrize("prefix", ["ag_api", "ags_api"])
def test_report_permission_denied_before_file_lookup(monkeypatch, prefix):
    status_lookup = Mock(return_value={"status": "access_denied"})
    file_lookup = Mock(side_effect=AssertionError("report file was accessed"))
    monkeypatch.setattr(reports, "session_scope", lambda: nullcontext(Mock()))
    monkeypatch.setattr(reports, "get_report_download_status", status_lookup)
    monkeypatch.setattr(reports.file_helper, "safe_storage_path", file_lookup)
    client = TestClient(FastAPI())
    client.app.include_router(reports.router)

    response = client.get(f"/{prefix}/get_ag_first_pdf/09123456789/AG")

    assert response.status_code == 403
    assert response.json()["status"] == 403
    status_lookup.assert_called_once()
    file_lookup.assert_not_called()


def test_wrong_report_kind_does_not_query_database(monkeypatch):
    session_scope = Mock(side_effect=AssertionError("wrong kind opened a database session"))
    monkeypatch.setattr(reports, "session_scope", session_scope)
    client = TestClient(FastAPI())
    client.app.include_router(reports.router)

    response = client.get("/ag_api/get_ag_first_pdf/09123456789/SCL")

    assert response.status_code == 321
    session_scope.assert_not_called()


@pytest.mark.asyncio
async def test_redis_connection_closes_when_action_fails(monkeypatch):
    redis_db = object()
    connect = AsyncMock(return_value=redis_db)
    close = AsyncMock()
    monkeypatch.setattr(action_helpers, "redis_connection", connect)
    monkeypatch.setattr(action_helpers, "close_redis_connection", close)

    def failing_handler(**_kwargs):
        raise RuntimeError("service failed")

    with pytest.raises(RuntimeError, match="service failed"):
        await action_helpers.dispatch_redis_action(failing_handler, {})

    close.assert_awaited_once_with(redis_db=redis_db)
