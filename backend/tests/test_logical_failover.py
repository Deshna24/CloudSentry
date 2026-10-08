"""Requirement 19: Logical instance fallback automated test.

Proves:
1. Register API-01 and API-02.
2. Force API-01 down.
3. Send GET requests.
4. Send POST requests.
5. Confirm requests still return 200.
6. Confirm API-02 handles them.
7. Recover API-01.
8. Confirm both become available again.
"""
from app.config import settings
from app.database import SessionLocal
from app.models import Instance, utcnow
from app.services import instances as inst_svc


def test_logical_instance_failover_and_recovery(client, admin):
    # Step 1: Register API-01 and API-02 as logical instances
    original_registered = settings.register_instances
    settings.register_instances = "API-01,API-02"
    assert settings.virtual_mode is True
    assert "API-01" in settings.registered_list
    assert "API-02" in settings.registered_list

    with SessionLocal() as db:
        for iid in ["API-01", "API-02"]:
            inst = db.get(Instance, iid)
            if not inst:
                db.add(Instance(id=iid, mode="logical", forced_down=False, last_heartbeat=utcnow()))
            else:
                inst.forced_down = False
                inst.mode = "logical"
                inst.last_heartbeat = utcnow()
        db.commit()

    inst_svc.invalidate_cache()

    try:
        # Step 2: Force API-01 down
        r_fail = client.post(
            "/simulation/instance-failure",
            json={"instance_id": "API-01", "down": True},
            headers=admin,
        )
        assert r_fail.status_code == 200
        assert r_fail.json()["status"] == "DOWN"

        inst_svc.invalidate_cache()

        # Step 3: Send GET requests (e.g. /threats, /audit-logs)
        get_res1 = client.get("/threats", headers=admin)
        get_res2 = client.get("/audit-logs", headers=admin)

        # Step 4: Send POST requests (e.g. /inspect)
        post_res = client.post(
            "/inspect",
            json={"endpoint": "/api/users", "method": "GET", "request_count": 5},
            headers=admin,
        )

        # Step 5: Confirm requests still return 200 (service is not down!)
        assert get_res1.status_code == 200
        assert get_res2.status_code == 200
        assert post_res.status_code == 200

        # Step 6: Confirm API-02 handles them
        assert get_res1.headers.get("x-instance-id") == "API-02"
        assert get_res2.headers.get("x-instance-id") == "API-02"
        assert post_res.headers.get("x-instance-id") == "API-02"
        assert post_res.json()["instance_id"] == "API-02"

        # Step 7: Recover API-01
        r_rec = client.post(
            "/simulation/instance-failure",
            json={"instance_id": "API-01", "down": False},
            headers=admin,
        )
        assert r_rec.status_code == 200
        assert r_rec.json()["status"] == "HEALTHY"

        inst_svc.invalidate_cache()

        # Step 8: Confirm both become available again
        served_instances = set()
        for _ in range(30):
            res = client.get("/threats", headers=admin)
            assert res.status_code == 200
            served_instances.add(res.headers.get("x-instance-id"))
            if "API-01" in served_instances and "API-02" in served_instances:
                break

        assert "API-01" in served_instances, f"API-01 was not returned: {served_instances}"
        assert "API-02" in served_instances, f"API-02 was not returned: {served_instances}"

    finally:
        # Restore configuration and clean up
        settings.register_instances = original_registered
        inst_svc.invalidate_cache()
