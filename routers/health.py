from fastapi import APIRouter

import helper.api_metrics as api_metrics
import helper.health as health_helper

router = APIRouter()


@router.get("/ag_api/metrics")
async def metrics():
    return api_metrics.metrics_response()


@router.get("/ag_api/health")
async def health_check():
    return await health_helper.health_payload("ag_api")


@router.get("/ag_api/ready")
async def ready_check():
    return await health_helper.readiness_payload("ag_api")


@router.get("/ag_api/live")
async def live_check():
    return await health_helper.liveness_payload("ag_api")


@router.get("/ags_api/metrics")
async def student_metrics():
    return api_metrics.metrics_response()


@router.get("/ags_api/health")
async def student_health_check():
    return await health_helper.health_payload("ags_api")


@router.get("/ags_api/ready")
async def student_ready_check():
    return await health_helper.readiness_payload("ags_api")


@router.get("/ags_api/live")
async def student_live_check():
    return await health_helper.liveness_payload("ags_api")
