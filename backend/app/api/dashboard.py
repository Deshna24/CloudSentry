import time
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.detection_engine import severity_for
from app.core.security import get_current_user
from app.database import get_db
from app.models import TrafficEvent, TrafficTick, User, utcnow
from app.services import gamification as gam_svc
from app.services import instances as inst_svc
from app.services import simulation
from app.services.events import event_dict

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    now = utcnow()
    d24, h1 = now - timedelta(hours=24), now - timedelta(hours=1)
    E = TrafficEvent

    def count(*conds):
        return db.scalar(select(func.count()).select_from(E).where(E.timestamp >= d24, *conds)) or 0

    tick = db.scalar(select(TrafficTick).order_by(TrafficTick.timestamp.desc()).limit(1))
    ticks = db.scalars(select(TrafficTick).order_by(TrafficTick.timestamp.desc()).limit(60)).all()[::-1]
    dist = dict(db.execute(select(E.threat_type, func.count()).where(E.timestamp >= d24)
                           .group_by(E.threat_type)).all())
    peak = db.scalar(select(func.max(E.risk_score)).where(E.timestamp >= now - timedelta(minutes=2),
                                                  E.source != "seed"))  # seed history must not raise the live threat level
    recent = db.scalars(select(E).where(E.threat_type != "NORMAL").order_by(E.timestamp.desc(), E.id.desc())
                        .limit(10)).all()
    return {
        "instance_id": inst_svc_id(),
        "kpis": {
            "requests_per_second": tick.rps if tick else 0,
            "rps_age_seconds": int((now - tick.timestamp).total_seconds()) if tick else None,
            "active_users": db.scalar(select(func.count(func.distinct(E.source_ip))).where(E.timestamp >= h1)) or 0,
            "threats_detected": count(E.threat_type != "NORMAL"),
            "requests_blocked": count(E.action == "BLOCK"),
            "requests_throttled": count(E.action == "THROTTLE"),
            "requests_evaluated": count(),
            "uptime_seconds": int(time.time() - inst_svc.START_TIME),
        },
        "threat_level": {"level": severity_for(peak or 0), "risk": peak or 0},
        "threat_distribution": [{"type": k, "count": v} for k, v in
                                sorted(dist.items(), key=lambda kv: -kv[1])],
        "timeseries": [{"timestamp": t.timestamp.isoformat(timespec="seconds") + "Z", "rps": t.rps,
                        "blocked": t.blocked_rps, "throttled": t.throttled_rps} for t in ticks],
        "recent_threats": [event_dict(e) for e in recent],
        "simulation": simulation.state_dict(db),
        "gamification": gam_svc.get_user_progress(db, user.username),
    }


def inst_svc_id() -> str:
    from app.config import settings
    return settings.instance_id
