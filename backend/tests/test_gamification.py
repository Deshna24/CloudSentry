import time
import pytest
from app.services import instances as inst_svc


def test_gamification_progress_endpoint(client, admin, analyst):
    r = client.get("/gamification/progress", headers=admin)
    assert r.status_code == 200
    data = r.json()
    assert "xp" in data
    assert "level" in data
    assert "title" in data
    assert "next_level_xp" in data
    assert "progress_percent" in data
    assert data["level"] >= 1

    # Profile alias
    r2 = client.get("/profile/progress", headers=admin)
    assert r2.status_code == 200
    assert r2.json()["username"] == "admin"


def test_gamification_missions_and_achievements(client, admin):
    # Missions
    r = client.get("/gamification/missions", headers=admin)
    assert r.status_code == 200
    missions = r.json()
    assert len(missions) == 4
    m_ids = [m["id"] for m in missions]
    assert "mission_01" in m_ids
    assert "mission_02" in m_ids
    assert "mission_03" in m_ids
    assert "mission_04" in m_ids

    # Mission alias
    r_alias = client.get("/missions", headers=admin)
    assert r_alias.status_code == 200

    # Achievements
    r_ach = client.get("/gamification/achievements", headers=admin)
    assert r_ach.status_code == 200
    achievements = r_ach.json()
    assert len(achievements) >= 6
    keys = [a["key"] for a in achievements]
    assert "first_defense" in keys
    assert "high_availability" in keys
    assert "login_guard" in keys
    assert "threat_hunter" in keys
    assert "rapid_response" in keys
    assert "cloud_sentinel" in keys


def test_attack_lab_launch_and_telemetry(client, admin):
    # Reset simulation first
    client.post("/simulation/reset", headers=admin)
    time.sleep(0.5)

    launch_payload = {
        "attack_type": "BRUTE_FORCE",
        "target_endpoint": "/login",
        "intensity": "HIGH",
        "duration": 10,
    }
    r = client.post("/simulation/launch", json=launch_payload, headers=admin)
    assert r.status_code == 200
    res = r.json()
    assert res["attack_type"] == "BRUTE_FORCE"
    assert res["target_endpoint"] == "/login"
    assert res["intensity"] == "HIGH"
    assert res["status"] in ("running", "complete")
    run_id = res["run_id"]

    # Poll status
    st = client.get("/simulation/status", headers=admin).json()
    assert "latest_run" in st
    assert st["latest_run"]["run_id"] == run_id

    # Poll run detail
    r_run = client.get(f"/simulation/{run_id}", headers=admin)
    assert r_run.status_code == 200
    assert r_run.json()["target_endpoint"] == "/login"

    # Reset lab
    r_reset = client.post(f"/simulation/{run_id}/reset", headers=admin)
    assert r_reset.status_code == 200


def test_attack_lab_launch_sqli(client, admin):
    client.post("/simulation/reset", headers=admin)
    time.sleep(0.5)

    r = client.post(
        "/simulation/launch",
        json={
            "attack_type": "SQL_INJECTION",
            "target_endpoint": "/search",
            "intensity": "MEDIUM",
            "duration": 8,
        },
        headers=admin,
    )
    assert r.status_code == 200
    assert r.json()["attack_type"] == "SQL_INJECTION"
    client.post("/simulation/reset", headers=admin)


def test_failover_awards_xp_and_achievement(client, admin):
    prog_before = client.get("/gamification/progress", headers=admin).json()
    xp_before = prog_before["xp"]

    r = client.post(
        "/simulation/instance-failure",
        json={"instance_id": "API-01", "down": True},
        headers=admin,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "DOWN"
    assert r.json()["gamification"] is not None

    prog_after = client.get("/gamification/progress", headers=admin).json()
    assert prog_after["xp"] > xp_before
    assert prog_after["failovers_survived"] >= 1

    # Check high_availability achievement is unlocked
    ach = client.get("/gamification/achievements", headers=admin).json()
    ha = next(a for a in ach if a["key"] == "high_availability")
    assert ha["unlocked"] is True

    # Recover
    client.post(
        "/simulation/instance-failure",
        json={"instance_id": "API-01", "down": False},
        headers=admin,
    )
