from fastapi import FastAPI

import helper.api_metrics as api_metrics
from routers.actions import router as actions_router
from routers.files import router as files_router
from routers.health import router as health_router
from routers.reports import router as reports_router
from routers.static_data import router as static_data_router
from routers.uploads import router as uploads_router

app = FastAPI()
app.middleware("http")(api_metrics.prometheus_http_middleware)
app.include_router(actions_router)
app.include_router(files_router)
app.include_router(health_router)
app.include_router(reports_router)
app.include_router(static_data_router)
app.include_router(uploads_router)
