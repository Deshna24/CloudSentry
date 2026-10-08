from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import client_ip, get_current_user, require_admin
from app.database import get_db
from app.models import Instance, User
from app.schemas.schemas import AttackRequest, InstanceFailureRequest, LaunchSimulationRequest
from app.services import gamification as gam_svc
from app.services import instances as inst_svc
from app.services import simulation as sim
from app.services.events import admin_audit

router = APIRouter(prefix="/simulation", tags=["simulation"])


def _inst(request: Request) -> str:
    return getattr(request.state, "instance_id", "API-01")


@router.get("/status")
def status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return sim.state_dict(db)


@router.get("/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    run_info = sim.get_run(db, run_id)
    if not run_info:
        raise HTTPException(404, f"Simulation run '{run_id}' not found")
    return run_info


@router.post("/launch")
async def launch(
    body: LaunchSimulationRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Launch a staged Attack Lab simulation (100% synthetic, contained in CloudSentry)."""
    current_state = sim.state_dict(db)
    if current_state.get("active"):
        raise HTTPException(409, "A simulation is already in progress")

    run_info = sim.launch(
        db=db,
        username=admin.username,
        attack_type=body.attack_type,
        target_endpoint=body.target_endpoint,
        intensity=body.intensity,
        duration=body.duration,
    )
    admin_audit(
        db,
        admin.username,
        f"Attack Lab simulation launched ({body.attack_type} on {body.target_endpoint}, {body.intensity})",
        client_ip(request),
        _inst(request),
    )
    return run_info


@router.post("/attack")
async def attack(
    body: AttackRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Start a simulated attack scenario (all traffic is synthetic and stays inside CloudSentry)."""
    if sim.state_dict(db)["active"]:
        raise HTTPException(409, "A simulation is already running")
    run_id = sim.start(db, body.scenario)
    admin_audit(db, admin.username, f"Attack simulation started ({body.scenario})", client_ip(request), _inst(request))
    return {
        "status": "started",
        "run_id": run_id,
        "scenario": body.scenario,
        "phases": [{"rps": p.rps, "seconds": p.seconds} for p in sim.SCENARIOS[body.scenario]],
    }


@router.post("/normal")
def normal(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """One second of ordinary traffic - the dashboard 'Live traffic' toggle calls this."""
    return sim.normal_tick()


@router.post("/reset")
def reset(request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    sim.reset(db)
    inst_svc.invalidate_cache()
    admin_audit(
        db,
        admin.username,
        "Simulation reset (simulated data cleared, instances restored)",
        client_ip(request),
        _inst(request),
    )
    return {"status": "reset"}


@router.post("/{run_id}/reset")
def reset_run(run_id: str, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    sim.reset(db)
    inst_svc.invalidate_cache()
    admin_audit(
        db,
        admin.username,
        f"Simulation {run_id} reset",
        client_ip(request),
        _inst(request),
    )
    return {"status": "reset", "run_id": run_id}


@router.post("/instance-failure")
def instance_failure(
    body: InstanceFailureRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    inst = db.get(Instance, body.instance_id)
    if not inst:
        raise HTTPException(404, f"Instance '{body.instance_id}' is not registered (is it running?)")
    inst.forced_down = body.down
    db.commit()
    inst_svc.invalidate_cache()

    admin_audit(
        db,
        admin.username,
        f"Instance {body.instance_id} {'failure simulated' if body.down else 'recovered'}",
        client_ip(request),
        _inst(request),
    )

    gam_reward = None
    if body.down:
        gam_reward = gam_svc.record_failover(db, admin.username)

    return {
        "instance_id": body.instance_id,
        "status": "DOWN" if body.down else "HEALTHY",
        "gamification": gam_reward,
    }
