from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import client_ip, get_current_user, require_admin
from app.database import get_db
from app.models import SecurityRule, User
from app.schemas.schemas import RuleUpdate
from app.services.events import admin_audit

router = APIRouter(tags=["security-rules"])


def _d(r: SecurityRule) -> dict:
    return {"id": r.id, "key": r.key, "name": r.name, "description": r.description,
            "category": r.category, "enabled": r.enabled, "toggleable": r.toggleable}


@router.get("/security-rules")
def list_rules(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [_d(r) for r in db.scalars(select(SecurityRule).order_by(SecurityRule.id))]


@router.put("/security-rules/{rule_id}")
def update_rule(rule_id: int, body: RuleUpdate, request: Request, db: Session = Depends(get_db),
                admin: User = Depends(require_admin)):
    rule = db.get(SecurityRule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    if not rule.toggleable:
        raise HTTPException(400, f"'{rule.name}' is always on and cannot be disabled")
    rule.enabled = body.enabled
    db.commit()
    admin_audit(db, admin.username, f"Rule '{rule.name}' {'enabled' if body.enabled else 'disabled'}",
                client_ip(request), getattr(request.state, "instance_id", "API-01"))
    return _d(rule)
