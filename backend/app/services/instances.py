"""Backend instance registry: heartbeats, simulated failures, derived load-balancer status."""
import asyncio
import logging
import random
import time
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, init_db, is_ready
from app.models import Instance, utcnow

log = logging.getLogger("cloudsentry.instances")
START_TIME = time.time()
_cache = {"at": 0.0, "self_down": False, "up": []}


def beat(db: Session) -> None:
    """Upsert a heartbeat row for every instance id this process represents."""
    mode = "logical" if settings.virtual_mode else "container"
    for iid in settings.registered_list:
        row = db.get(Instance, iid)
        if row is None:
            db.add(Instance(id=iid, mode=mode))
        else:
            row.last_heartbeat = utcnow()
            row.mode = mode
    db.commit()


async def heartbeat_loop() -> None:
    while True:
        try:
            if not is_ready():
                await asyncio.to_thread(init_db, 1)
            await asyncio.to_thread(_beat_sync)
        except Exception as exc:  # database may be down; keep trying
            log.warning("heartbeat/init failed: %s", type(exc).__name__)
        await asyncio.sleep(settings.heartbeat_seconds)


def _beat_sync() -> None:
    with SessionLocal() as db:
        beat(db)


def status_list(db: Session) -> list[dict]:
    now = utcnow()
    hb = settings.heartbeat_seconds
    rows = {r.id: r for r in db.scalars(select(Instance))}
    ids = list(dict.fromkeys(settings.expected_list + list(rows)))
    out = []
    for iid in ids:
        r = rows.get(iid)
        if r is None:
            out.append({"id": iid, "status": "DOWN", "detail": "No heartbeat received (not deployed or unreachable)",
                        "last_heartbeat": None, "started_at": None, "mode": "-", "forced_down": False})
            continue
        age = (now - r.last_heartbeat).total_seconds()
        if r.forced_down:
            status, detail = "DOWN", "Failure simulated by an administrator"
        elif age > 3 * hb:
            status, detail = "DOWN", f"Heartbeat lost ({int(age)}s ago)"
        elif age > 2 * hb:
            status, detail = "WARNING", f"Heartbeat delayed ({int(age)}s ago)"
        else:
            status, detail = "HEALTHY", "Serving traffic"
        out.append({"id": iid, "status": status, "detail": detail,
                    "last_heartbeat": r.last_heartbeat.isoformat(timespec="seconds") + "Z",
                    "started_at": r.started_at.isoformat(timespec="seconds") + "Z",
                    "mode": r.mode, "forced_down": r.forced_down})
    return out


def up_ids(db: Session) -> list[str]:
    return [i["id"] for i in status_list(db) if i["status"] != "DOWN"]


def load_balancer(items: list[dict]) -> dict:
    up = [i for i in items if i["status"] != "DOWN"]
    if not up:
        return {"status": "DOWN", "detail": "No healthy backend instances to route to"}
    return {"status": "HEALTHY", "detail": f"Routing to {len(up)} of {len(items)} instances"}


def _refresh() -> None:
    with SessionLocal() as db:
        items = status_list(db)
    mine = {i["id"]: i for i in items}
    _cache["self_down"] = any(mine.get(i, {}).get("forced_down") for i in settings.registered_list)
    _cache["up"] = [i["id"] for i in items if i["status"] != "DOWN"]
    _cache["at"] = time.time()


def invalidate_cache() -> None:
    _cache["at"] = 0.0


async def gate_state() -> dict:
    """Cached (1s) view of 'am I simulated-down' and 'which instances are up'."""
    if time.time() - _cache["at"] > 1.0:
        try:
            await asyncio.to_thread(_refresh)
        except Exception:
            _cache["at"] = time.time()
    return _cache


async def serving_instance() -> tuple[str, bool]:
    """(instance id to report for this request, whether this process must refuse it)."""
    st = await gate_state()
    if settings.virtual_mode:
        live = [i for i in st["up"] if i in settings.registered_list]
        return (random.choice(live) if live else settings.instance_id), not live
    return settings.instance_id, bool(st["self_down"])
