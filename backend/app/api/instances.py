from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import check_db, get_db
from app.models import TrafficEvent, User, utcnow
from app.services import instances as inst_svc

router = APIRouter(tags=["instances"])


@router.get("/instances")
def instances(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = inst_svc.status_list(db)
    since = utcnow() - timedelta(hours=1)
    counts = dict(db.execute(select(TrafficEvent.instance_id, func.count())
                             .where(TrafficEvent.timestamp >= since).group_by(TrafficEvent.instance_id)).all())
    total = sum(counts.values())
    for i in items:
        c = counts.get(i["id"], 0)
        i["requests_1h"], i["share_percent"] = c, round(100 * c / total, 1) if total else 0
    ok, ms = check_db()
    return {"load_balancer": inst_svc.load_balancer(items), "instances": items,
            "database": {"status": "HEALTHY" if ok else "DOWN", "latency_ms": ms}}
