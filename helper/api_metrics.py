import os
import time
from functools import wraps

from fastapi import Request
from fastapi.responses import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)
from starlette.routing import Match

API_REQUESTS_TOTAL = Counter(
    "ag_api_action_requests_total",
    "Total API requests by endpoint, action_type, and status_code.",
    ["endpoint", "action_type", "status_code"],
)

API_REQUEST_DURATION_SECONDS = Histogram(
    "ag_api_action_request_duration_seconds",
    "API request duration by endpoint, action_type, and status_code.",
    ["endpoint", "action_type", "status_code"],
)

API_ERRORS_TOTAL = Counter(
    "ag_api_action_errors_total",
    "Total API errors by endpoint and action_type.",
    ["endpoint", "action_type"],
)

HTTP_REQUESTS_TOTAL = Counter(
    "ag_http_requests_total",
    "Total HTTP requests.",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "ag_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "path", "status_code"],
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "ag_http_requests_in_progress",
    "Number of HTTP requests in progress.",
    ["method", "path"],
    multiprocess_mode="livesum",
)

SKIPPED_HTTP_PATHS = {
    "/ag_api/metrics",
    "/ags_api/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
}
UNMATCHED_ROUTE_LABEL = "__unmatched__"


def is_multiprocess_metrics_enabled() -> bool:
    return bool(os.getenv("PROMETHEUS_MULTIPROC_DIR"))


def request_path_template(request: Request) -> str:
    for route in request.app.routes:
        try:
            match, _ = route.matches(request.scope)
        except Exception:
            continue
        if match == Match.FULL:
            return str(getattr(route, "path", request.url.path))

    return UNMATCHED_ROUTE_LABEL


async def get_action_type(request: Request | None) -> str:
    if request is None:
        return "UNKNOWN"

    try:
        body = await request.json()
    except Exception:
        return "UNKNOWN"

    return str(body.get("method_type") or body.get("action_type") or "UNKNOWN")


def response_status_code(response) -> str:
    if isinstance(response, dict):
        return str(response.get("status") or 200)
    return str(getattr(response, "status_code", 200))


def monitor_endpoint(endpoint: str):
    """Measure action-level count, errors, and duration for one API endpoint."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if request is None:
                request = next((arg for arg in args if isinstance(arg, Request)), None)

            action_type = await get_action_type(request)
            status_code = "500"
            start_time = time.perf_counter()

            try:
                response = await func(*args, **kwargs)
                status_code = response_status_code(response)
                API_REQUESTS_TOTAL.labels(endpoint, action_type, status_code).inc()
                if int(status_code) >= 400:
                    API_ERRORS_TOTAL.labels(endpoint, action_type).inc()
                return response
            except Exception:
                API_ERRORS_TOTAL.labels(endpoint, action_type).inc()
                raise
            finally:
                elapsed = time.perf_counter() - start_time
                API_REQUEST_DURATION_SECONDS.labels(endpoint, action_type, status_code).observe(elapsed)

        return wrapper

    return decorator


async def prometheus_http_middleware(request: Request, call_next):
    raw_path = request.url.path
    if raw_path in SKIPPED_HTTP_PATHS:
        return await call_next(request)

    method = request.method
    path = request_path_template(request)
    HTTP_REQUESTS_IN_PROGRESS.labels(method, path).inc()

    start_time = time.perf_counter()
    status_code = "500"
    try:
        response = await call_next(request)
        status_code = str(getattr(response, "status_code", 200))
        return response
    finally:
        elapsed = time.perf_counter() - start_time
        HTTP_REQUESTS_IN_PROGRESS.labels(method, path).dec()
        HTTP_REQUESTS_TOTAL.labels(method, path, status_code).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method, path, status_code).observe(elapsed)


def metrics_response() -> Response:
    if is_multiprocess_metrics_enabled():
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
