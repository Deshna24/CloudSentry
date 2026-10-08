"""Gamification API endpoints: user progress, missions, and achievements."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models import User
from app.services import gamification as gam_svc

router = APIRouter(tags=["gamification"])


@router.get("/gamification/progress")
@router.get("/profile/progress")
def get_progress(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return gam_svc.get_user_progress(db, user.username)


@router.get("/gamification/missions")
@router.get("/missions")
def get_missions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return gam_svc.get_missions(db, user.username)


@router.get("/gamification/achievements")
@router.get("/achievements")
def get_achievements(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return gam_svc.get_achievements(db, user.username)
