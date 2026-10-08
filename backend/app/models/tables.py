from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    """Naive UTC timestamps everywhere (works the same on SQLite and PostgreSQL)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(16))  # ADMIN | ANALYST
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TrafficEvent(Base):
    """One evaluated API request plus the detection result."""
    __tablename__ = "traffic_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    source_ip: Mapped[str] = mapped_column(String(64), index=True)
    endpoint: Mapped[str] = mapped_column(String(300))
    method: Mapped[str] = mapped_column(String(10))
    status_code: Mapped[int] = mapped_column(Integer)
    response_time: Mapped[float] = mapped_column(Float)  # ms
    request_count: Mapped[int] = mapped_column(Integer, default=1)  # requests/min from this IP
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    payload_size: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[str] = mapped_column(Text, default="")  # truncated, stored as inert text
    user_role: Mapped[str] = mapped_column(String(16), default="ANONYMOUS")
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    threat_type: Mapped[str] = mapped_column(String(24), index=True, default="NORMAL")
    risk_score: Mapped[int] = mapped_column(Integer, default=5)
    severity: Mapped[str] = mapped_column(String(10), default="LOW")
    action: Mapped[str] = mapped_column(String(10), default="ALLOW", index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    instance_id: Mapped[str] = mapped_column(String(32), default="API-01")
    source: Mapped[str] = mapped_column(String(12), default="live", index=True)  # seed|simulation|live


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    user: Mapped[str] = mapped_column(String(64), default="anonymous")
    event: Mapped[str] = mapped_column(String(300))
    source_ip: Mapped[str] = mapped_column(String(64), default="-")
    threat_type: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(10), nullable=True)
    action: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    instance_id: Mapped[str] = mapped_column(String(32), default="API-01")
    event_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(12), default="live", index=True)  # seed|simulation|live|admin


class SecurityRule(Base):
    __tablename__ = "security_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(16))  # detection | platform
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    toggleable: Mapped[bool] = mapped_column(Boolean, default=True)


class Instance(Base):
    __tablename__ = "instances"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    forced_down: Mapped[bool] = mapped_column(Boolean, default=False)
    mode: Mapped[str] = mapped_column(String(10), default="container")  # container | logical


class TrafficTick(Base):
    """Requests-per-second sample used by the live traffic chart."""
    __tablename__ = "traffic_ticks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    rps: Mapped[int] = mapped_column(Integer)
    blocked_rps: Mapped[int] = mapped_column(Integer, default=0)
    throttled_rps: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(12), default="seed")


class SimulationState(Base):
    __tablename__ = "simulation_state"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    run_id: Mapped[str] = mapped_column(String(36), default="")
    scenario: Mapped[str] = mapped_column(String(24), default="")
    phase: Mapped[int] = mapped_column(Integer, default=0)
    phases_total: Mapped[int] = mapped_column(Integer, default=0)
    current_rps: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UserProgress(Base):
    """Gamification: XP and level for each user."""
    __tablename__ = "user_progress"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    simulations_run: Mapped[int] = mapped_column(Integer, default=0)
    threats_contained: Mapped[int] = mapped_column(Integer, default=0)
    failovers_survived: Mapped[int] = mapped_column(Integer, default=0)
    threat_types_seen: Mapped[str] = mapped_column(Text, default="")  # comma-sep list
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UserAchievement(Base):
    """Gamification: unlocked achievements per user."""
    __tablename__ = "user_achievements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), index=True)
    achievement_key: Mapped[str] = mapped_column(String(64))
    unlocked_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SimulationRun(Base):
    """Detailed record of an Attack Lab simulation."""
    __tablename__ = "simulation_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(64), index=True)
    attack_type: Mapped[str] = mapped_column(String(32))  # brute_force, rate_abuse, etc.
    target_endpoint: Mapped[str] = mapped_column(String(300), default="/login")
    intensity: Mapped[str] = mapped_column(String(16), default="MEDIUM")  # LOW|MEDIUM|HIGH|EXTREME
    duration: Mapped[int] = mapped_column(Integer, default=20)  # seconds
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|running|complete
    current_phase: Mapped[str] = mapped_column(String(32), default="preparing")
    phase_index: Mapped[int] = mapped_column(Integer, default=0)
    requests_generated: Mapped[int] = mapped_column(Integer, default=0)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    threat_type: Mapped[str] = mapped_column(String(32), default="")
    action: Mapped[str] = mapped_column(String(16), default="")
    xp_earned: Mapped[int] = mapped_column(Integer, default=0)
    achievements_unlocked: Mapped[str] = mapped_column(Text, default="")  # comma-sep list
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
