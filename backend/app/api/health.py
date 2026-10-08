import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, check_db, get_db
from app.services import instances as inst_svc

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request):
    """Liveness probe (no database access). Use this for Render/Docker health checks."""
    return {"status": "healthy", "service": "cloudsentry-api",
            "instance_id": getattr(request.state, "instance_id", settings.instance_id)}


@router.get("/health/instance")
async def health_instance():
    """Returns 503 while this instance is in simulated failure (useful for load balancers)."""
    _, refuse = await inst_svc.serving_instance()
    if refuse:
        return JSONResponse(status_code=503, content={"status": "down", "instance_id": settings.instance_id})
    return {"status": "healthy", "instance_id": settings.instance_id}


@router.get("/health/database")
def health_database():
    ok, ms = check_db()
    body = {"status": "healthy" if ok else "down", "latency_ms": ms}
    return JSONResponse(status_code=200 if ok else 503, content=body)


@router.get("/health/detailed")
def health_detailed(request: Request):
    """Used by the dashboard: database, every backend instance and the load balancer."""
    ok, ms = check_db()
    items, lb = [], {"status": "DOWN", "detail": "Database unavailable"}
    if ok:
        with SessionLocal() as db:
            items = inst_svc.status_list(db)
        lb = inst_svc.load_balancer(items)
    up = [i for i in items if i["status"] != "DOWN"]
    if not ok or not up:
        overall = "DOWN"
    elif len(up) < len(items) or any(i["status"] == "WARNING" for i in items):
        overall = "DEGRADED"
    else:
        overall = "OPERATIONAL"
    return {"status": overall, "service": "cloudsentry-api",
            "instance_id": getattr(request.state, "instance_id", settings.instance_id),
            "uptime_seconds": int(time.time() - inst_svc.START_TIME),
            "database": {"status": "HEALTHY" if ok else "DOWN", "latency_ms": ms,
                         "detail": "Connected" if ok else "Database unreachable"},
            "load_balancer": lb, "instances": items}
