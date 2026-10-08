"""Runs at startup: demo users, default rules, and (if the database is empty) demo telemetry."""
import logging
import secrets

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import hash_password
from app.models import SimulationState, TrafficEvent, User
from app.services import seed
from app.services.rules import ensure_rules

log = logging.getLogger("cloudsentry.bootstrap")


def _ensure_user(db: Session, username: str, role: str, password: str) -> None:
    if db.scalar(select(User).where(User.username == username)):
        return
    if not password:
        password = secrets.token_urlsafe(10)
        log.warning("Generated password for '%s': %s  (set SEED_%s_PASSWORD to choose your own)",
                    username, password, role)
    db.add(User(username=username, password_hash=hash_password(password), role=role))
    db.commit()


def run(db: Session) -> None:
    if db.bind.dialect.name == "postgresql":
        # Only one instance bootstraps at a time (lock is released at commit)
        if not db.execute(text("SELECT pg_try_advisory_xact_lock(727001)")).scalar():
            return
    _ensure_user(db, "admin", "ADMIN", settings.seed_admin_password)
    _ensure_user(db, "analyst", "ANALYST", settings.seed_analyst_password)
    ensure_rules(db)
    if db.get(SimulationState, 1) is None:
        db.add(SimulationState(id=1))
        db.commit()
    if settings.auto_seed and not db.scalar(select(func.count()).select_from(TrafficEvent)):
        n = seed.seed_events(db, max(100, min(settings.seed_records, 20000)))
        log.info("Seeded %s synthetic telemetry records", n)
    db.commit()
