import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api import audit, auth, dashboard, gamification, health, instances, rules, simulation, threats, traffic
from app.config import settings
from app.database import init_db
from app.services import instances as inst_svc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("cloudsentry")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await asyncio.to_thread(init_db)
    except Exception as exc:  # keep serving /health; the heartbeat loop retries init
        log.error("Database initialisation failed (%s). Will retry in background.", type(exc).__name__)
    task = asyncio.create_task(inst_svc.heartbeat_loop())
    yield
    task.cancel()


app = FastAPI(title="CloudSentry API", version="1.0.0",
              description="Cloud-based API threat detection & automated response platform.",
              lifespan=lifespan)

# Paths that keep working while this instance is in *simulated* failure
_ALWAYS_UP = ("/health", "/simulation", "/gamification", "/missions", "/achievements", "/profile", "/docs", "/openapi.json", "/redoc")


@app.middleware("http")
async def instance_gate(request: Request, call_next):
    """Tags every response with the serving instance and refuses traffic while simulated-down."""
    instance_id, refuse = await inst_svc.serving_instance()
    request.state.instance_id = instance_id
    if refuse and request.method != "OPTIONS" and not request.url.path.startswith(_ALWAYS_UP):
        resp = JSONResponse(status_code=503, content={"detail": "Instance unavailable", "instance_id": instance_id})
    else:
        resp = await call_next(request)
    resp.headers["X-Instance-Id"] = instance_id
    return resp


# Added last => outermost, so even 503/500 responses carry CORS headers
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Instance-Id"])


@app.exception_handler(SQLAlchemyError)
async def db_error(request: Request, exc: SQLAlchemyError):
    log.error("Database error on %s: %s", request.url.path, type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "Database unavailable. Please try again shortly."})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    errors = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "Invalid request: " + "; ".join(
        f"{e['field']} {e['message']}" for e in errors), "errors": errors})


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


for r in (health.router, auth.router, dashboard.router, traffic.router, threats.router,
          instances.router, audit.router, rules.router, simulation.router, gamification.router):
    app.include_router(r)


@app.get("/", tags=["health"])
def root():
    return {"service": "cloudsentry-api", "docs": "/docs", "health": "/health"}
