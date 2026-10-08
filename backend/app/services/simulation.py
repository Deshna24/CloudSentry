"""Attack simulator. Generates synthetic traffic INSIDE this application only.

A run is a series of 1-second ticks. Each tick records the requests/sec figure for the chart and a
sample of evaluated requests, which go through the real detection engine and audit log.
"""
import asyncio
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.detection_engine import evaluate
from app.database import SessionLocal
from app.models import AuditLog, Instance, SimulationRun, SimulationState, TrafficEvent, TrafficTick, utcnow
from app.services import gamification as gam_svc
from app.services import instances as inst_svc
from app.services import traffic_gen as gen
from app.services.events import record
from app.services.rules import enabled_rule_keys

BASELINE_RPS = 80
RATE_RPM = {80: 60, 250: 280, 300: 350, 500: 650, 700: 900, 850: 1100, 1200: 1700, 1300: 1900}
_tasks: set[asyncio.Task] = set()

INTENSITY_RPS = {
    "LOW": 250,
    "MEDIUM": 500,
    "HIGH": 850,
    "EXTREME": 1300,
}


@dataclass
class Phase:
    rps: int
    seconds: int
    kinds: list[str] = field(default_factory=list)


SCENARIOS: dict[str, list[Phase]] = {
    "full": [Phase(80, 3), Phase(300, 4, ["rate", "brute_low"]), Phase(700, 4, ["rate", "brute", "sqli"]),
             Phase(1200, 5, ["rate", "brute", "sqli", "xss", "traversal"])],
    "rate_abuse": [Phase(80, 2), Phase(700, 5, ["rate"]), Phase(1200, 5, ["rate"])],
    "brute_force": [Phase(80, 2), Phase(80, 8, ["brute"])],
    "sql_injection": [Phase(80, 2), Phase(80, 8, ["sqli"])],
    "xss": [Phase(80, 2), Phase(80, 8, ["xss"])],
    "path_traversal": [Phase(80, 2), Phase(80, 8, ["traversal"])],
}


def run_dict(r: SimulationRun | None) -> dict | None:
    if not r:
        return None
    ach_list = [a.strip() for a in (r.achievements_unlocked or "").split(",") if a.strip()]
    return {
        "simulation_id": r.run_id,
        "run_id": r.run_id,
        "username": r.username,
        "attack_type": r.attack_type,
        "target_endpoint": r.target_endpoint,
        "intensity": r.intensity,
        "duration": r.duration,
        "status": r.status,
        "current_phase": r.current_phase,
        "phase_index": r.phase_index,
        "requests_generated": r.requests_generated,
        "risk_score": r.risk_score,
        "threat_type": r.threat_type,
        "action": r.action,
        "xp_earned": r.xp_earned,
        "achievements_unlocked": ach_list,
        "started_at": r.started_at.isoformat() + "Z" if r.started_at else None,
        "completed_at": r.completed_at.isoformat() + "Z" if r.completed_at else None,
    }


def state_dict(db: Session) -> dict:
    st = db.get(SimulationState, 1)
    latest_run_obj = db.scalar(select(SimulationRun).order_by(SimulationRun.id.desc()).limit(1))
    latest_run = run_dict(latest_run_obj)

    if not st:
        return {"active": False, "latest_run": latest_run}
    stale = st.updated_at is None or (utcnow() - st.updated_at).total_seconds() > 10
    active = bool(st.active and not stale)
    return {
        "active": active,
        "scenario": st.scenario if active else "",
        "phase": st.phase if active else 0,
        "phases_total": st.phases_total,
        "current_rps": st.current_rps if active else 0,
        "started_at": st.started_at.isoformat(timespec="seconds") + "Z" if st.started_at else None,
        "latest_run": latest_run,
    }


def get_run(db: Session, run_id: str) -> dict | None:
    r = db.scalar(select(SimulationRun).where(SimulationRun.run_id == run_id))
    return run_dict(r)


def _emit(db, rng, ctx, enabled, up, source="simulation"):
    det = evaluate(ctx, enabled)
    record(db, ctx, det, rng.choice(up), source=source, commit=False)
    return det


def run_tick(run_id: str, phase_idx: int, phase: Phase, tick_no: int, total_phases: int) -> bool:
    """Write one second of simulated traffic. Returns False if the run was cancelled/reset."""
    rng = random.Random()
    with SessionLocal() as db:
        st = db.get(SimulationState, 1)
        if not st or not st.active or st.run_id != run_id:
            return False
        rps = int(phase.rps * rng.uniform(0.95, 1.05))
        st.phase, st.phases_total, st.current_rps, st.updated_at = phase_idx + 1, total_phases, rps, utcnow()
        up = inst_svc.up_ids(db)
        if not up:  # every instance is down: nothing can serve requests
            db.add(TrafficTick(rps=0, source="simulation"))
            db.commit()
            return True
        enabled = enabled_rule_keys(db)
        for _ in range(8):
            _emit(db, rng, gen.normal_ctx(rng), enabled, up)
        attackers = rng.sample(gen.ATTACKER_IPS, 3)
        blocked = throttled = 0
        attack_rps = max(0, rps - BASELINE_RPS)
        for kind in phase.kinds:
            if kind == "rate":
                rpm = int(RATE_RPM.get(phase.rps, phase.rps * 1.4) * rng.uniform(0.92, 1.08))
                for ip in attackers:
                    det = _emit(db, rng, gen.rate_ctx(rng, rpm, ip), enabled, up)
                if det.action == "BLOCK":
                    blocked = attack_rps
                elif det.action == "THROTTLE":
                    throttled = attack_rps
            elif kind == "brute_low":
                _emit(db, rng, gen.brute_ctx(rng, rng.randint(8, 18), attackers[0]), enabled, up)
            elif kind == "brute":
                _emit(db, rng, gen.brute_ctx(rng, min(160, 25 + tick_no * 8 + rng.randint(0, 6)), attackers[0]), enabled, up)
            elif kind == "sqli":
                for _ in range(2):
                    _emit(db, rng, gen.sqli_ctx(rng, attackers[1]), enabled, up)
            elif kind == "xss":
                _emit(db, rng, gen.xss_ctx(rng, attackers[2]), enabled, up)
            elif kind == "traversal":
                _emit(db, rng, gen.traversal_ctx(rng, attackers[2]), enabled, up)
        db.add(TrafficTick(rps=rps, blocked_rps=blocked, throttled_rps=throttled, source="simulation"))
        db.commit()
        return True


def normal_tick() -> dict:
    """One second of ordinary traffic (the 'Live traffic' toggle calls this)."""
    rng = random.Random()
    with SessionLocal() as db:
        st = db.get(SimulationState, 1)
        if st and state_dict(db)["active"]:
            return state_dict(db)
        up = inst_svc.up_ids(db)
        rps = int(BASELINE_RPS * rng.uniform(0.85, 1.15)) if up else 0
        if up:
            enabled = enabled_rule_keys(db)
            for _ in range(6):
                _emit(db, rng, gen.normal_ctx(rng), enabled, up)
        db.add(TrafficTick(rps=rps, source="simulation"))
        db.commit()
        return {"active": False, "rps": rps}


async def run_scenario(run_id: str, scenario: str) -> None:
    phases = SCENARIOS[scenario]
    try:
        for idx, phase in enumerate(phases):
            for t in range(phase.seconds):
                ok = await asyncio.to_thread(run_tick, run_id, idx, phase, t, len(phases))
                if not ok:
                    return
                await asyncio.sleep(1)
    finally:
        def _finish():
            with SessionLocal() as db:
                st = db.get(SimulationState, 1)
                if st and st.run_id == run_id:
                    st.active = False
                    db.commit()
        try:
            await asyncio.to_thread(_finish)
        except Exception:
            pass


def start(db: Session, scenario: str) -> str:
    run_id = str(uuid.uuid4())
    st = db.get(SimulationState, 1) or SimulationState(id=1)
    st.active, st.run_id, st.scenario = True, run_id, scenario
    st.phase, st.phases_total, st.current_rps = 0, len(SCENARIOS[scenario]), 0
    st.started_at = st.updated_at = utcnow()
    db.add(st)
    db.commit()
    task = asyncio.create_task(run_scenario(run_id, scenario))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return run_id


async def run_attack_lab_simulation(
    run_id: str,
    username: str,
    attack_type: str,
    target_endpoint: str,
    intensity: str,
    duration: int,
) -> None:
    """Staged simulation worker: progresses through 7 interactive phases and awards gamification XP."""
    stages = [
        ("preparing", 1, "Preparing simulation..."),
        ("traffic_spike", 2, "Traffic increasing..."),
        ("analysing", 3, "CloudSentry analysing behaviour..."),
        ("detection", 4, "Anomaly detected..."),
        ("classification", 5, "Risk score calculated..."),
        ("response", 6, "Automated response triggered..."),
        ("contained", 7, "Threat contained."),
    ]
    target_rps = INTENSITY_RPS.get(intensity.upper(), 500)
    rng = random.Random()
    total_generated = 0
    threat_type_name = attack_type.upper().replace("-", "_")

    try:
        for second in range(duration):
            # Map second to one of 6 live stages
            pct = second / max(1, duration)
            if pct < 0.15:
                phase_name, phase_idx, phase_desc = stages[0]
                rps_cur = int(BASELINE_RPS * rng.uniform(0.9, 1.1))
            elif pct < 0.35:
                phase_name, phase_idx, phase_desc = stages[1]
                rps_cur = int((BASELINE_RPS + (target_rps - BASELINE_RPS) * 0.45) * rng.uniform(0.92, 1.05))
            elif pct < 0.50:
                phase_name, phase_idx, phase_desc = stages[2]
                rps_cur = int((BASELINE_RPS + (target_rps - BASELINE_RPS) * 0.8) * rng.uniform(0.95, 1.05))
            elif pct < 0.68:
                phase_name, phase_idx, phase_desc = stages[3]
                rps_cur = int(target_rps * rng.uniform(0.96, 1.04))
            elif pct < 0.85:
                phase_name, phase_idx, phase_desc = stages[4]
                rps_cur = int(target_rps * rng.uniform(0.96, 1.04))
            else:
                phase_name, phase_idx, phase_desc = stages[5]
                rps_cur = int(target_rps * rng.uniform(0.95, 1.05))

            total_generated += rps_cur

            def _tick(sec, p_name, p_idx, rps_val, total_reqs):
                with SessionLocal() as db:
                    st = db.get(SimulationState, 1)
                    if not st or not st.active or st.run_id != run_id:
                        return False, None, None, None

                    st.phase = p_idx
                    st.phases_total = 7
                    st.current_rps = rps_val
                    st.updated_at = utcnow()

                    up = inst_svc.up_ids(db)
                    if not up:
                        db.add(TrafficTick(rps=0, source="simulation"))
                        db.commit()
                        return True, 0, "NORMAL", "ALLOW"

                    enabled = enabled_rule_keys(db)
                    for _ in range(5):
                        _emit(db, rng, gen.normal_ctx(rng), enabled, up)

                    attackers = rng.sample(gen.ATTACKER_IPS, 2)
                    last_det = None

                    # Generate attack-specific telemetry targeted at target_endpoint
                    norm_att = attack_type.upper().replace("-", "_").replace(" ", "_")
                    if norm_att in ("BRUTE_FORCE", "BRUTE"):
                        last_det = _emit(db, rng, gen.brute_ctx(rng, 35 + sec * 5, attackers[0], target_endpoint), enabled, up)
                    elif norm_att in ("RATE_ABUSE", "RATE"):
                        last_det = _emit(db, rng, gen.rate_ctx(rng, int(rps_val * 1.5), attackers[0], target_endpoint), enabled, up)
                    elif norm_att in ("SQL_INJECTION", "SQLI"):
                        last_det = _emit(db, rng, gen.sqli_ctx(rng, attackers[0], target_endpoint), enabled, up)
                    elif norm_att in ("XSS",):
                        last_det = _emit(db, rng, gen.xss_ctx(rng, attackers[0], target_endpoint), enabled, up)
                    elif norm_att in ("PATH_TRAVERSAL", "TRAVERSAL"):
                        last_det = _emit(db, rng, gen.traversal_ctx(rng, attackers[0], target_endpoint), enabled, up)
                    else:
                        last_det = _emit(db, rng, gen.brute_ctx(rng, 45, attackers[0], target_endpoint), enabled, up)

                    blocked = 0
                    throttled = 0
                    if last_det.action == "BLOCK":
                        blocked = max(0, rps_val - BASELINE_RPS)
                    elif last_det.action == "THROTTLE":
                        throttled = max(0, rps_val - BASELINE_RPS)

                    db.add(TrafficTick(rps=rps_val, blocked_rps=blocked, throttled_rps=throttled, source="simulation"))

                    # Update SimulationRun row
                    sim_run = db.scalar(select(SimulationRun).where(SimulationRun.run_id == run_id))
                    if sim_run:
                        sim_run.current_phase = p_name
                        sim_run.phase_index = p_idx
                        sim_run.requests_generated = total_reqs
                        sim_run.risk_score = last_det.risk_score
                        sim_run.threat_type = last_det.threat_type
                        sim_run.action = last_det.action
                        sim_run.updated_at = utcnow()

                    db.commit()
                    return True, last_det.risk_score, last_det.threat_type, last_det.action

            ok, risk, th_type, act = await asyncio.to_thread(_tick, second, phase_name, phase_idx, rps_cur, total_generated)
            if not ok:
                return
            await asyncio.sleep(1)

        # Final Phase 7: Threat Contained & Gamification reward
        def _complete():
            with SessionLocal() as db:
                st = db.get(SimulationState, 1)
                if st and st.run_id == run_id:
                    st.active = False
                    st.phase = 7
                    st.current_rps = 0
                    st.updated_at = utcnow()

                sim_run = db.scalar(select(SimulationRun).where(SimulationRun.run_id == run_id))
                if sim_run:
                    sim_run.current_phase = "contained"
                    sim_run.phase_index = 7
                    sim_run.status = "complete"
                    sim_run.completed_at = utcnow()

                    # Gamification record & award
                    res = gam_svc.record_simulation_completion(
                        db=db,
                        username=username,
                        threat_type=sim_run.threat_type or threat_type_name,
                        duration_seconds=duration,
                        contained=True
                    )
                    sim_run.xp_earned = res["xp_earned"]
                    sim_run.achievements_unlocked = ",".join(res["achievements_unlocked"])

                db.commit()

        await asyncio.to_thread(_complete)

    finally:
        def _cleanup_st():
            with SessionLocal() as db:
                st = db.get(SimulationState, 1)
                if st and st.run_id == run_id and st.active:
                    st.active = False
                    db.commit()
        try:
            await asyncio.to_thread(_cleanup_st)
        except Exception:
            pass


def launch(
    db: Session,
    username: str,
    attack_type: str,
    target_endpoint: str = "/login",
    intensity: str = "MEDIUM",
    duration: int = 20,
) -> dict:
    run_id = str(uuid.uuid4())
    norm_att = attack_type.upper().replace("-", "_").replace(" ", "_")

    # Save SimulationState
    st = db.get(SimulationState, 1) or SimulationState(id=1)
    st.active = True
    st.run_id = run_id
    st.scenario = attack_type.lower()
    st.phase = 1
    st.phases_total = 7
    st.current_rps = BASELINE_RPS
    st.started_at = utcnow()
    st.updated_at = utcnow()
    db.add(st)

    # Create SimulationRun entry
    sim_run = SimulationRun(
        run_id=run_id,
        username=username,
        attack_type=norm_att,
        target_endpoint=target_endpoint,
        intensity=intensity.upper(),
        duration=duration,
        status="running",
        current_phase="preparing",
        phase_index=1,
        requests_generated=0,
        risk_score=20,
        threat_type=norm_att,
        action="ANALYSING",
        xp_earned=0,
        achievements_unlocked="",
        started_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(sim_run)
    db.commit()

    task = asyncio.create_task(
        run_attack_lab_simulation(
            run_id=run_id,
            username=username,
            attack_type=norm_att,
            target_endpoint=target_endpoint,
            intensity=intensity,
            duration=duration,
        )
    )
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)

    return run_dict(sim_run)


def reset(db: Session) -> None:
    """Stop any run, delete simulated/live telemetry, and bring failed instances back."""
    st = db.get(SimulationState, 1)
    if st:
        st.active, st.run_id, st.phase, st.current_rps = False, "", 0, 0
    for model in (TrafficEvent, AuditLog):
        db.execute(delete(model).where(model.source.in_(["simulation", "live"])))
    db.execute(delete(TrafficTick).where(TrafficTick.source == "simulation"))
    for inst in db.query(Instance).all():
        inst.forced_down = False
    db.commit()
