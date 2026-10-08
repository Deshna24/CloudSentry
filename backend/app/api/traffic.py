from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models import TrafficEvent, User, utcnow
from app.services.events import event_dict

router = APIRouter(tags=["traffic"])


@router.get("/traffic")
def traffic(minutes: int = Query(60, ge=5, le=1440), db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    E = TrafficEvent
    now = utcnow()
    since = now - timedelta(minutes=minutes)
    rows = db.execute(select(E.timestamp, E.response_time).where(E.timestamp >= since)).all()
    bucket_min = 1 if minutes <= 120 else 15
    buckets: dict = {}
    for ts, rt in rows:
        key = ts.replace(second=0, microsecond=0, minute=(ts.minute // bucket_min) * bucket_min if bucket_min > 1 else ts.minute)
        b = buckets.setdefault(key, [0, 0.0])
        b[0] += 1
        b[1] += rt
    timeline = [{"timestamp": k.isoformat(timespec="seconds") + "Z", "requests": v[0],
                 "avg_response_time": round(v[1] / v[0], 1)} for k, v in sorted(buckets.items())]

    def grouped(col):
        return [{"label": str(k), "count": c} for k, c in
                db.execute(select(col, func.count()).where(E.timestamp >= since).group_by(col)
                           .order_by(func.count().desc())).all()]

    total = len(rows)
    inst = grouped(E.instance_id)
    for i in inst:
        i["percent"] = round(100 * i["count"] / total, 1) if total else 0
    codes = [{"label": c["label"], "count": c["count"]} for c in grouped(E.status_code)]
    avg_rt = db.scalar(select(func.avg(E.response_time)).where(E.timestamp >= since))
    recent = db.scalars(select(E).order_by(E.timestamp.desc(), E.id.desc()).limit(25)).all()
    return {"window_minutes": minutes, "total_requests": total,
            "avg_response_time": round(avg_rt or 0, 1), "timeline": timeline,
            "by_endpoint": grouped(E.endpoint)[:8], "by_method": grouped(E.method),
            "status_codes": sorted(codes, key=lambda c: c["label"]), "by_instance": inst,
            "recent_requests": [event_dict(e) for e in recent]}
