"""Seed realistic synthetic telemetry.   Usage:  python -m app.services.seed --count 3000 [--reset]"""
import argparse
import random
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.detection_engine import evaluate
from app.models import AuditLog, TrafficEvent, TrafficTick, utcnow
from app.services import traffic_gen as gen
from app.services.events import make_event
from app.services.rules import enabled_rule_keys


def seed_events(db: Session, count: int = 2500, rng: random.Random | None = None) -> int:
    rng = rng or random.Random()
    enabled = enabled_rule_keys(db)
    now = utcnow()
    kinds = ["normal", "rate", "brute", "sqli", "xss", "traversal"]
    weights = [88, 4, 3, 2.2, 1.4, 1.4]
    events, logs = [], []
    for _ in range(count):
        kind = rng.choices(kinds, weights)[0]
        if kind == "normal":
            ctx = gen.normal_ctx(rng)
        elif kind == "rate":
            ctx = gen.rate_ctx(rng, rng.choice([280, 340, 420, 560, 700, 900, 1300, 1800]))
        elif kind == "brute":
            ctx = gen.brute_ctx(rng, rng.choice([6, 9, 14, 19, 24, 35, 60, 87, 140]))
        elif kind == "sqli":
            ctx = gen.sqli_ctx(rng)
        elif kind == "xss":
            ctx = gen.xss_ctx(rng)
        else:
            ctx = gen.traversal_ctx(rng)
        # half of the records fall in the last hour so charts look alive, the rest in the last 24h
        minutes = rng.uniform(0, 60) if rng.random() < 0.5 else rng.uniform(60, 24 * 60)
        ts = now - timedelta(minutes=minutes)
        instance = "API-01" if rng.random() < 0.48 else "API-02"
        det = evaluate(ctx, enabled)
        ev, log = make_event(ctx, det, instance, "seed", ts=ts)
        events.append(ev)
        logs.append((ev, log))
    db.add_all(events)
    db.flush()
    for ev, log in logs:
        log.event_id = ev.id
    db.add_all([log for _, log in logs])
    for i in range(60):  # last 5 minutes of requests/sec samples
        db.add(TrafficTick(timestamp=now - timedelta(seconds=5 * (60 - i)), rps=rng.randint(68, 96),
                           source="seed"))
    db.commit()
    return count


def main() -> None:
    from app.database import SessionLocal, init_db
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=2500)
    parser.add_argument("--reset", action="store_true", help="delete existing telemetry first")
    args = parser.parse_args()
    init_db()
    with SessionLocal() as db:
        if args.reset:
            for model in (AuditLog, TrafficEvent, TrafficTick):
                db.execute(delete(model))
            db.commit()
        n = seed_events(db, max(100, min(args.count, 20000)))
        total = db.scalar(select(func.count()).select_from(TrafficEvent))
        print(f"Seeded {n} events (total now {total}).")


if __name__ == "__main__":
    main()
