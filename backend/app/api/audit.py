from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models import AuditLog, User
from app.services.utils import iso, parse_day

router = APIRouter(tags=["audit"])


@router.get("/audit-logs")
def audit_logs(threat_type: str | None = None, severity: str | None = None, action: str | None = None,
               q: str | None = Query(None, max_length=100), date_from: str | None = None,
               date_to: str | None = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
               db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    A = AuditLog
    conds = []
    if threat_type:
        conds.append(A.threat_type == threat_type.upper())
    if severity:
        conds.append(A.severity == severity.upper())
    if action:
        conds.append(A.action == action.upper())
    if q:
        like = f"%{q}%"
        conds.append(A.source_ip.like(like) | A.user.like(like) | A.event.like(like))
    if (d := parse_day(date_from)):
        conds.append(A.timestamp >= d)
    if (d := parse_day(date_to, True)):
        conds.append(A.timestamp <= d)
    total = db.scalar(select(func.count()).select_from(A).where(*conds)) or 0
    rows = db.scalars(select(A).where(*conds).order_by(A.timestamp.desc(), A.id.desc())
                      .limit(limit).offset(offset)).all()
    return {"total": total, "items": [
        {"id": r.id, "timestamp": iso(r.timestamp), "user": r.user, "event": r.event,
         "source_ip": r.source_ip, "threat_type": r.threat_type, "risk_score": r.risk_score,
         "severity": r.severity, "action": r.action, "instance_id": r.instance_id,
         "event_id": r.event_id, "threat_id": f"CS-{1000 + r.event_id}" if r.event_id else None}
        for r in rows]}
