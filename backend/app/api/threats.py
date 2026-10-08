from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.detection_engine import RequestContext, evaluate
from app.core.security import client_ip, get_current_user
from app.database import get_db
from app.models import TrafficEvent, User
from app.schemas.schemas import InspectRequest
from app.services.events import event_dict, record
from app.services.rules import enabled_rule_keys
from app.services.utils import parse_day

router = APIRouter(tags=["threats"])

EXPLANATIONS = {
    "BRUTE_FORCE": "The source made many failed authentication attempts in a short window, which is typical of password guessing.",
    "RATE_ABUSE": "The source sent far more requests per minute than a normal client, which can exhaust capacity (DoS-style flooding or scraping).",
    "SQL_INJECTION": "The request contained SQL syntax (for example UNION SELECT or OR 1=1) that tries to alter a database query.",
    "XSS": "The request contained script markup or event handlers that could run in another user's browser.",
    "PATH_TRAVERSAL": "The request used ../ sequences to try to read files outside the allowed directory.",
}
RESPONSES = {
    "BLOCK": "Request rejected with HTTP 403 and recorded in the audit log.",
    "THROTTLE": "Request slowed with HTTP 429 (rate limited) and recorded in the audit log.",
    "MONITOR": "Request allowed but flagged for analyst review.",
    "ALLOW": "Request allowed.",
}


@router.get("/threats")
def list_threats(threat_type: str | None = None, severity: str | None = None, action: str | None = None,
                 q: str | None = Query(None, max_length=100), date_from: str | None = None,
                 date_to: str | None = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conds = [TrafficEvent.threat_type != "NORMAL"]
    if threat_type:
        conds.append(TrafficEvent.threat_type == threat_type.upper())
    if severity:
        conds.append(TrafficEvent.severity == severity.upper())
    if action:
        conds.append(TrafficEvent.action == action.upper())
    if q:
        like = f"%{q}%"
        conds.append(TrafficEvent.source_ip.like(like) | TrafficEvent.endpoint.like(like))
    if (d := parse_day(date_from)):
        conds.append(TrafficEvent.timestamp >= d)
    if (d := parse_day(date_to, True)):
        conds.append(TrafficEvent.timestamp <= d)
    total = db.scalar(select(func.count()).select_from(TrafficEvent).where(*conds)) or 0
    rows = db.scalars(select(TrafficEvent).where(*conds).order_by(TrafficEvent.timestamp.desc(),
                                                                  TrafficEvent.id.desc())
                      .limit(limit).offset(offset)).all()
    return {"total": total, "items": [event_dict(r) for r in rows]}


@router.get("/threats/{threat_id}")
def threat_detail(threat_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Accepts either a database id (42) or a display id (CS-1042)."""
    try:
        pk = int(threat_id[3:]) - 1000 if threat_id.upper().startswith("CS-") else int(threat_id)
    except ValueError:
        raise HTTPException(400, "Invalid threat id")
    ev = db.get(TrafficEvent, pk)
    if not ev:
        raise HTTPException(404, "Threat not found")
    d = event_dict(ev)
    d.update(payload=ev.payload, explanation=EXPLANATIONS.get(ev.threat_type, "No threat detected."),
             response=RESPONSES.get(ev.action, ""))
    return d


@router.post("/inspect")
def inspect(body: InspectRequest, request: Request, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    """Run a request description through the detection engine and log it (Request Inspector)."""
    ctx = RequestContext(source_ip=body.source_ip or client_ip(request), endpoint=body.endpoint,
                         method=body.method, request_count=body.request_count,
                         failed_logins=body.failed_logins, payload=body.payload, user_role=user.role)
    det = evaluate(ctx, enabled_rule_keys(db))
    ev = record(db, ctx, det, getattr(request.state, "instance_id", "API-01"), username=user.username)
    return {"threat_id": f"CS-{1000 + ev.id}", "threat_type": det.threat_type, "risk_score": det.risk_score,
            "severity": det.severity, "action": det.action, "reason": det.reason,
            "instance_id": ev.instance_id}
