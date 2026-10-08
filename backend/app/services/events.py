import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.detection_engine import Detection, RequestContext
from app.models import AuditLog, TrafficEvent, utcnow

ACTION_STATUS = {"BLOCK": 403, "THROTTLE": 429}


def audit_text(ctx: RequestContext, det: Detection) -> str:
    if det.threat_type == "NORMAL":
        return f"Request allowed: {ctx.method} {ctx.endpoint[:80]}"
    verb = {"BLOCK": "blocked", "THROTTLE": "throttled", "MONITOR": "flagged for monitoring"}.get(det.action, "allowed")
    return f"{det.threat_type.replace('_', ' ').title()} detected, request {verb}"


def make_event(ctx: RequestContext, det: Detection, instance_id: str, source: str = "live",
               username: str | None = None, ts: datetime | None = None,
               status_code: int | None = None) -> tuple[TrafficEvent, AuditLog]:
    ts = ts or utcnow()
    status = status_code or ACTION_STATUS.get(det.action, ctx.status_code)
    ev = TrafficEvent(
        request_id=str(uuid.uuid4()), timestamp=ts, source_ip=ctx.source_ip,
        endpoint=ctx.endpoint[:300], method=ctx.method, status_code=status,
        response_time=round(ctx.response_time, 1), request_count=ctx.request_count,
        failed_logins=ctx.failed_logins, payload_size=len(ctx.payload or ""),
        payload=(ctx.payload or "")[:500], user_role=ctx.user_role, username=username,
        threat_type=det.threat_type, risk_score=det.risk_score, severity=det.severity,
        action=det.action, reason=det.reason, instance_id=instance_id, source=source)
    log = AuditLog(
        timestamp=ts, user=username or "anonymous", event=audit_text(ctx, det),
        source_ip=ctx.source_ip, threat_type=det.threat_type, risk_score=det.risk_score,
        severity=det.severity, action=det.action, instance_id=instance_id, source=source)
    return ev, log


def record(db: Session, ctx: RequestContext, det: Detection, instance_id: str,
           source: str = "live", username: str | None = None, status_code: int | None = None,
           commit: bool = True) -> TrafficEvent:
    ev, log = make_event(ctx, det, instance_id, source, username, None, status_code)
    db.add(ev)
    db.flush()
    log.event_id = ev.id
    db.add(log)
    if commit:
        db.commit()
    return ev


def admin_audit(db: Session, user: str, event: str, ip: str, instance_id: str) -> None:
    db.add(AuditLog(user=user, event=event, source_ip=ip, instance_id=instance_id, source="admin"))
    db.commit()


def failed_logins_for_ip(db: Session, ip: str, minutes: int = 10) -> int:
    """Failed (401) and throttled (429) login attempts - throttled ones still count so abuse escalates to BLOCK."""
    since = utcnow() - timedelta(minutes=minutes)
    return db.scalar(select(func.count()).select_from(TrafficEvent).where(
        TrafficEvent.source == "live", TrafficEvent.endpoint == "/auth/login",
        TrafficEvent.status_code.in_((401, 429)), TrafficEvent.source_ip == ip,
        TrafficEvent.timestamp >= since)) or 0


def requests_last_minute(db: Session, ip: str) -> int:
    since = utcnow() - timedelta(minutes=1)
    return db.scalar(select(func.count()).select_from(TrafficEvent).where(
        TrafficEvent.source == "live", TrafficEvent.source_ip == ip,
        TrafficEvent.timestamp >= since)) or 0


def event_dict(e: TrafficEvent) -> dict:
    return {
        "id": e.id, "threat_id": f"CS-{1000 + e.id}", "request_id": e.request_id,
        "timestamp": e.timestamp.isoformat(timespec="seconds") + "Z", "source_ip": e.source_ip,
        "endpoint": e.endpoint, "method": e.method, "status_code": e.status_code,
        "response_time": e.response_time, "request_count": e.request_count,
        "failed_logins": e.failed_logins, "payload_size": e.payload_size,
        "user_role": e.user_role, "threat_type": e.threat_type, "risk_score": e.risk_score,
        "severity": e.severity, "action": e.action, "reason": e.reason,
        "instance_id": e.instance_id, "source": e.source,
    }
