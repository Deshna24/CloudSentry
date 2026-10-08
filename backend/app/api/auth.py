from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.detection_engine import RequestContext, evaluate
from app.core.security import client_ip, create_token, get_current_user, verify_password
from app.database import get_db
from app.models import User
from app.schemas.schemas import LoginRequest
from app.services.events import failed_logins_for_ip, record, requests_last_minute
from app.services.rules import enabled_rule_keys

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Login. Attempts are themselves run through the detection engine (brute force, SQLi in username)."""
    ip, instance = client_ip(request), getattr(request.state, "instance_id", "API-01")
    enabled = enabled_rule_keys(db)
    ctx = RequestContext(source_ip=ip, endpoint="/auth/login", method="POST",
                         request_count=requests_last_minute(db, ip) + 1,
                         failed_logins=failed_logins_for_ip(db, ip), payload=body.username,
                         user_role="ANONYMOUS")
    det = evaluate(ctx, enabled)
    if det.action in ("BLOCK", "THROTTLE"):
        record(db, ctx, det, instance)
        code = 403 if det.action == "BLOCK" else 429
        raise HTTPException(code, "Request blocked by CloudSentry" if code == 403
                            else "Too many requests - slow down")
    user = db.scalar(select(User).where(User.username == body.username))
    if not user or not verify_password(body.password, user.password_hash):
        ctx.failed_logins += 1
        ctx.status_code = 401
        record(db, ctx, evaluate(ctx, enabled), instance, status_code=401)
        raise HTTPException(401, "Invalid username or password")
    ctx.user_role, ctx.status_code = user.role, 200
    record(db, ctx, det, instance, username=user.username, status_code=200)
    return {"access_token": create_token(user.username, user.role), "token_type": "bearer",
            "username": user.username, "role": user.role, "instance_id": instance}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"username": user.username, "role": user.role}
