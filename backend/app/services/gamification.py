"""Gamification service: XP, levels, missions, achievements and user progression."""
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import UserAchievement, UserProgress, utcnow

ACHIEVEMENTS = [
    {
        "key": "first_defense",
        "title": "FIRST DEFENSE",
        "description": "Contained your first threat.",
        "icon": "shield",
        "xp_reward": 100,
    },
    {
        "key": "rapid_response",
        "title": "RAPID RESPONSE",
        "description": "Contained a threat in under 10 seconds.",
        "icon": "zap",
        "xp_reward": 150,
    },
    {
        "key": "high_availability",
        "title": "HIGH AVAILABILITY",
        "description": "Survived an API instance failure.",
        "icon": "cloud",
        "xp_reward": 300,
    },
    {
        "key": "login_guard",
        "title": "LOGIN GUARD",
        "description": "Contained a brute-force simulation.",
        "icon": "lock",
        "xp_reward": 150,
    },
    {
        "key": "threat_hunter",
        "title": "THREAT HUNTER",
        "description": "Detected 3 different threat types.",
        "icon": "flame",
        "xp_reward": 200,
    },
    {
        "key": "cloud_sentinel",
        "title": "CLOUD SENTINEL",
        "description": "Completed all core missions.",
        "icon": "trophy",
        "xp_reward": 500,
    },
]

LEVEL_THRESHOLDS = [
    (1, "SECURITY ROOKIE", 0, 250),
    (2, "TRAFFIC ANALYST", 250, 500),
    (3, "THREAT HUNTER", 500, 720),
    (4, "CLOUD DEFENDER", 720, 1000),
    (5, "CYBER SENTINEL", 1000, 1500),
    (6, "CHIEF DEFENDER", 1500, 2500),
]


def calculate_level_info(xp: int) -> dict:
    level = 1
    title = "SECURITY ROOKIE"
    level_min = 0
    level_max = 250

    for lvl, name, l_min, l_max in LEVEL_THRESHOLDS:
        if xp >= l_min:
            level = lvl
            title = name
            level_min = l_min
            level_max = l_max
        else:
            break

    if xp >= 2500:
        level = 7
        title = "CLOUD GUARDIAN"
        level_min = 2500
        level_max = 5000

    current_in_level = max(0, xp - level_min)
    needed_for_next = max(1, level_max - level_min)
    percent = min(100, int((current_in_level / needed_for_next) * 100))

    return {
        "level": level,
        "title": title,
        "current_xp": xp,
        "level_min_xp": level_min,
        "next_level_xp": level_max,
        "level_progress_percent": percent,
        "display_xp": xp,
        "display_target": level_max,
    }


def get_or_create_progress(db: Session, username: str) -> UserProgress:
    row = db.scalar(select(UserProgress).where(UserProgress.username == username))
    if not row:
        initial_xp = 720 if username == "admin" else 150
        row = UserProgress(
            username=username,
            xp=initial_xp,
            level=4 if username == "admin" else 1,
            simulations_run=3 if username == "admin" else 0,
            threats_contained=2 if username == "admin" else 0,
            failovers_survived=1 if username == "admin" else 0,
            threat_types_seen="BRUTE_FORCE,RATE_ABUSE" if username == "admin" else "",
            updated_at=utcnow(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        # Unlock initial achievement for admin demo
        if username == "admin":
            if not db.scalar(select(UserAchievement).where(
                UserAchievement.username == username,
                UserAchievement.achievement_key == "first_defense"
            )):
                db.add(UserAchievement(username=username, achievement_key="first_defense", unlocked_at=utcnow()))
                db.commit()
    return row


def get_user_progress(db: Session, username: str) -> dict:
    row = get_or_create_progress(db, username)
    level_info = calculate_level_info(row.xp)
    unlocked_achievements = db.scalars(
        select(UserAchievement.achievement_key).where(UserAchievement.username == username)
    ).all()

    seen_types = [t.strip() for t in (row.threat_types_seen or "").split(",") if t.strip()]

    return {
        "username": username,
        "xp": row.xp,
        "level": level_info["level"],
        "title": level_info["title"],
        "current_level_xp": row.xp,
        "next_level_xp": level_info["next_level_xp"],
        "progress_percent": level_info["level_progress_percent"],
        "simulations_run": row.simulations_run,
        "threats_contained": row.threats_contained,
        "failovers_survived": row.failovers_survived,
        "threat_types_seen": seen_types,
        "achievements_count": len(unlocked_achievements),
        "total_achievements": len(ACHIEVEMENTS),
    }


def award_xp(db: Session, username: str, amount: int, reason: str = "") -> tuple[int, list[str]]:
    row = get_or_create_progress(db, username)
    row.xp += amount
    level_info = calculate_level_info(row.xp)
    row.level = level_info["level"]
    row.updated_at = utcnow()
    db.commit()

    newly_unlocked = check_and_unlock_achievements(db, username)
    return row.xp, newly_unlocked


def unlock_achievement(db: Session, username: str, key: str) -> bool:
    existing = db.scalar(select(UserAchievement).where(
        UserAchievement.username == username,
        UserAchievement.achievement_key == key
    ))
    if existing:
        return False

    ach = next((a for a in ACHIEVEMENTS if a["key"] == key), None)
    db.add(UserAchievement(username=username, achievement_key=key, unlocked_at=utcnow()))
    if ach and ach.get("xp_reward"):
        row = get_or_create_progress(db, username)
        row.xp += ach["xp_reward"]
        row.level = calculate_level_info(row.xp)["level"]
    db.commit()
    return True


def check_and_unlock_achievements(db: Session, username: str) -> list[str]:
    row = get_or_create_progress(db, username)
    unlocked = set(db.scalars(
        select(UserAchievement.achievement_key).where(UserAchievement.username == username)
    ).all())

    new_keys = []
    seen = set([t.strip() for t in (row.threat_types_seen or "").split(",") if t.strip()])

    if row.threats_contained >= 1 and "first_defense" not in unlocked:
        if unlock_achievement(db, username, "first_defense"):
            new_keys.append("first_defense")

    if row.failovers_survived >= 1 and "high_availability" not in unlocked:
        if unlock_achievement(db, username, "high_availability"):
            new_keys.append("high_availability")

    if "BRUTE_FORCE" in seen and "login_guard" not in unlocked:
        if unlock_achievement(db, username, "login_guard"):
            new_keys.append("login_guard")

    if len(seen) >= 3 and "threat_hunter" not in unlocked:
        if unlock_achievement(db, username, "threat_hunter"):
            new_keys.append("threat_hunter")

    # Cloud Sentinel: all 4 core missions completed
    m1 = "BRUTE_FORCE" in seen
    m2 = "RATE_ABUSE" in seen
    m3 = row.failovers_survived >= 1
    m4 = len(seen) >= 3
    if m1 and m2 and m3 and m4 and "cloud_sentinel" not in unlocked:
        if unlock_achievement(db, username, "cloud_sentinel"):
            new_keys.append("cloud_sentinel")

    return new_keys


def record_simulation_completion(
    db: Session,
    username: str,
    threat_type: str,
    duration_seconds: int,
    contained: bool = True
) -> dict:
    row = get_or_create_progress(db, username)
    row.simulations_run += 1
    if contained:
        row.threats_contained += 1

    seen = set([t.strip() for t in (row.threat_types_seen or "").split(",") if t.strip()])
    normalized_type = threat_type.upper().replace(" ", "_")
    if normalized_type and normalized_type != "NORMAL":
        seen.add(normalized_type)
    row.threat_types_seen = ",".join(sorted(seen))
    row.updated_at = utcnow()
    db.commit()

    xp_gained = 200 if contained else 50
    row.xp += xp_gained
    row.level = calculate_level_info(row.xp)["level"]
    db.commit()

    newly_unlocked = []
    if duration_seconds <= 10 and "rapid_response" not in db.scalars(
        select(UserAchievement.achievement_key).where(UserAchievement.username == username)
    ).all():
        if unlock_achievement(db, username, "rapid_response"):
            newly_unlocked.append("rapid_response")

    more_unlocked = check_and_unlock_achievements(db, username)
    newly_unlocked.extend(more_unlocked)

    return {
        "xp_earned": xp_gained,
        "total_xp": row.xp,
        "level": row.level,
        "achievements_unlocked": list(set(newly_unlocked)),
    }


def record_failover(db: Session, username: str) -> dict:
    row = get_or_create_progress(db, username)
    row.failovers_survived += 1
    row.xp += 300
    row.level = calculate_level_info(row.xp)["level"]
    row.updated_at = utcnow()
    db.commit()

    newly_unlocked = []
    if unlock_achievement(db, username, "high_availability"):
        newly_unlocked.append("high_availability")

    more = check_and_unlock_achievements(db, username)
    newly_unlocked.extend(more)

    return {
        "xp_earned": 300,
        "total_xp": row.xp,
        "level": row.level,
        "achievements_unlocked": list(set(newly_unlocked)),
    }


def get_achievements(db: Session, username: str) -> list[dict]:
    unlocked_map = {
        a.achievement_key: a.unlocked_at
        for a in db.scalars(
            select(UserAchievement).where(UserAchievement.username == username)
        ).all()
    }

    result = []
    for a in ACHIEVEMENTS:
        unlocked = a["key"] in unlocked_map
        result.append({
            "key": a["key"],
            "title": a["title"],
            "description": a["description"],
            "icon": a["icon"],
            "xp_reward": a["xp_reward"],
            "unlocked": unlocked,
            "unlocked_at": unlocked_map[a["key"]].isoformat() + "Z" if unlocked and unlocked_map[a["key"]] else None,
        })
    return result


def get_missions(db: Session, username: str) -> list[dict]:
    row = get_or_create_progress(db, username)
    seen = set([t.strip() for t in (row.threat_types_seen or "").split(",") if t.strip()])

    # Mission 1: Stop the Brute Force
    m1_done = "BRUTE_FORCE" in seen
    m1_pct = 100 if m1_done else (80 if row.simulations_run > 0 else 0)

    # Mission 2: Survive the Traffic Surge
    m2_done = "RATE_ABUSE" in seen
    m2_pct = 100 if m2_done else (50 if row.simulations_run > 0 else 0)

    # Mission 3: Keep the Cloud Alive
    m3_done = row.failovers_survived >= 1
    m3_pct = 100 if m3_done else 0

    # Mission 4: Complete Defender Training (3 different threat types)
    m4_count = min(3, len(seen))
    m4_done = len(seen) >= 3
    m4_pct = int((m4_count / 3.0) * 100)

    return [
        {
            "id": "mission_01",
            "title": "Stop the Brute Force",
            "code": "MISSION 01",
            "icon": "lock",
            "goal": "Trigger and contain a brute-force attack.",
            "reward_xp": 200,
            "progress_percent": m1_pct,
            "completed": m1_done,
        },
        {
            "id": "mission_02",
            "title": "Survive the Traffic Surge",
            "code": "MISSION 02",
            "icon": "wave",
            "goal": "Trigger rate abuse and activate throttling.",
            "reward_xp": 250,
            "progress_percent": m2_pct,
            "completed": m2_done,
        },
        {
            "id": "mission_03",
            "title": "Keep the Cloud Alive",
            "code": "MISSION 03",
            "icon": "cloud",
            "goal": "Simulate API-01 failure while maintaining service availability.",
            "reward_xp": 300,
            "progress_percent": m3_pct,
            "completed": m3_done,
        },
        {
            "id": "mission_04",
            "title": "Complete Defender Training",
            "code": "MISSION 04",
            "icon": "shield",
            "goal": "Successfully contain 3 different threat types.",
            "reward_xp": 500,
            "progress_percent": m4_pct,
            "completed": m4_done,
        },
    ]
