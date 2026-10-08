import time

from sqlalchemy import text

from app.database import check_db, engine


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy" and r.json()["service"] == "cloudsentry-api"
    assert r.headers["x-instance-id"] == "API-01"


def test_database_connection_and_health(client):
    ok, _ = check_db()
    assert ok
    with engine.connect() as c:
        assert c.execute(text("SELECT 1")).scalar() == 1
    assert client.get("/health/database").json()["status"] == "healthy"
    assert client.get("/health/detailed").json()["database"]["status"] == "HEALTHY"


def test_empty_database_bootstraps_users_rules_and_seed(client, admin):
    assert len(client.get("/security-rules", headers=admin).json()) >= 9
    assert client.get("/audit-logs?limit=1", headers=admin).json()["total"] >= 300


def test_auth_required_and_invalid_credentials(client):
    assert client.get("/dashboard/summary").status_code == 401
    assert client.get("/threats", headers={"Authorization": "Bearer garbage"}).status_code == 401
    r = client.post("/auth/login", json={"username": "admin", "password": "wrong"},
                    headers={"X-Forwarded-For": "10.2.2.2"})
    assert r.status_code == 401 and "Traceback" not in r.text


def test_malformed_requests_are_rejected_cleanly(client):
    r = client.post("/auth/login", json={"username": ""})
    assert r.status_code == 422 and "detail" in r.json()
    assert client.post("/auth/login", content="not json", headers={"Content-Type": "application/json"}).status_code == 422


def test_login_ok_and_roles(client, admin, analyst):
    assert client.get("/auth/me", headers=admin).json()["role"] == "ADMIN"
    assert client.get("/auth/me", headers=analyst).json()["role"] == "ANALYST"


def test_rbac_analyst_cannot_run_simulations_or_edit_rules(client, analyst):
    assert client.post("/simulation/attack", json={}, headers=analyst).status_code == 403
    assert client.post("/simulation/reset", headers=analyst).status_code == 403
    assert client.put("/security-rules/1", json={"enabled": False}, headers=analyst).status_code == 403
    assert client.get("/threats", headers=analyst).status_code == 200


def test_dashboard_summary_shape(client, analyst):
    d = client.get("/dashboard/summary", headers=analyst).json()
    for key in ("requests_per_second", "active_users", "threats_detected", "requests_blocked",
                "requests_throttled", "uptime_seconds"):
        assert key in d["kpis"]
    assert d["threat_level"]["level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert len(d["timeseries"]) > 0


def _inspect(client, admin, **body):
    body.setdefault("endpoint", "/api/products")
    r = client.post("/inspect", json=body, headers=admin)
    assert r.status_code == 200, r.text
    return r.json()


def test_normal_request_allowed(client, admin):
    r = _inspect(client, admin, request_count=3, source_ip="10.3.0.1")
    assert r["action"] == "ALLOW" and r["risk_score"] == 5


def test_rate_abuse_detected_via_api(client, admin):
    r = _inspect(client, admin, request_count=900, source_ip="10.3.0.2")
    assert r["threat_type"] == "RATE_ABUSE" and r["action"] == "THROTTLE"


def test_sql_injection_xss_traversal_via_api(client, admin):
    assert _inspect(client, admin, payload="' OR 1=1 --", source_ip="10.3.0.3")["threat_type"] == "SQL_INJECTION"
    assert _inspect(client, admin, payload="<script>alert(1)</script>", source_ip="10.3.0.4")["action"] == "BLOCK"
    assert _inspect(client, admin, endpoint="/files/../../etc/passwd", source_ip="10.3.0.5")["threat_type"] == "PATH_TRAVERSAL"


def test_real_brute_force_gets_blocked_and_audited(client):
    ip, last = "10.4.0.9", None
    for _ in range(25):
        last = client.post("/auth/login", json={"username": "admin", "password": "nope"},
                           headers={"X-Forwarded-For": ip})
    assert last.status_code == 403  # blocked after >20 failures
    # even the right password is refused for that IP now
    assert client.post("/auth/login", json={"username": "admin", "password": "AdminPass#123"},
                       headers={"X-Forwarded-For": ip}).status_code == 403


def test_sql_injection_in_login_username_is_blocked(client):
    r = client.post("/auth/login", json={"username": "admin' OR 1=1 --", "password": "x"},
                    headers={"X-Forwarded-For": "10.4.0.20"})
    assert r.status_code == 403


def test_threat_feed_detail_and_audit_trail(client, admin):
    feed = client.get("/threats?threat_type=BRUTE_FORCE&action=BLOCK", headers=admin).json()
    assert feed["total"] > 0
    t = feed["items"][0]
    detail = client.get(f"/threats/{t['threat_id']}", headers=admin).json()
    for key in ("threat_id", "timestamp", "source_ip", "endpoint", "method", "threat_type", "risk_score",
                "severity", "reason", "action", "instance_id", "explanation"):
        assert key in detail
    assert client.get("/threats/CS-999999", headers=admin).status_code == 404
    logs = client.get("/audit-logs?threat_type=SQL_INJECTION&action=BLOCK", headers=admin).json()
    assert logs["total"] > 0 and logs["items"][0]["instance_id"] in ("API-01", "API-02")


def test_rule_toggle_changes_detection_and_is_audited(client, admin):
    rules = {r["key"]: r for r in client.get("/security-rules", headers=admin).json()}
    sqli = rules["SQL_INJECTION"]
    assert client.put(f"/security-rules/{sqli['id']}", json={"enabled": False}, headers=admin).json()["enabled"] is False
    assert _inspect(client, admin, payload="' OR 1=1 --", source_ip="10.5.0.1")["threat_type"] == "NORMAL"
    client.put(f"/security-rules/{sqli['id']}", json={"enabled": True}, headers=admin)
    assert _inspect(client, admin, payload="' OR 1=1 --", source_ip="10.5.0.2")["threat_type"] == "SQL_INJECTION"
    jwt_rule = rules["JWT_AUTH"]
    assert client.put(f"/security-rules/{jwt_rule['id']}", json={"enabled": False}, headers=admin).status_code == 400


def test_traffic_endpoint(client, analyst):
    d = client.get("/traffic", headers=analyst).json()
    assert d["total_requests"] > 0 and len(d["by_instance"]) >= 1
    assert abs(sum(i["percent"] for i in d["by_instance"]) - 100) < 1


def test_attack_simulation_end_to_end(client, admin):
    client.post("/simulation/reset", headers=admin)
    before = client.get("/dashboard/summary", headers=admin).json()["kpis"]
    r = client.post("/simulation/attack", json={"scenario": "rate_abuse"}, headers=admin)
    assert r.status_code == 200
    assert client.post("/simulation/attack", json={}, headers=admin).status_code == 409
    time.sleep(4.5)
    s = client.get("/dashboard/summary", headers=admin).json()
    assert s["simulation"]["active"] is True
    assert s["kpis"]["threats_detected"] > before["threats_detected"]
    assert max(t["rps"] for t in s["timeseries"]) >= 600
    assert s["threat_level"]["level"] in ("HIGH", "CRITICAL")
    assert client.post("/simulation/attack", json={"scenario": "bogus"}, headers=admin).status_code == 422
    assert client.post("/simulation/reset", headers=admin).status_code == 200
    assert client.get("/simulation/status", headers=admin).json()["active"] is False


def test_instance_failure_and_recovery(client, admin):
    inst = client.get("/instances", headers=admin).json()
    assert any(i["id"] == "API-01" and i["status"] == "HEALTHY" for i in inst["instances"])
    assert client.post("/simulation/instance-failure", json={"instance_id": "NOPE"}, headers=admin).status_code == 404
    client.post("/simulation/instance-failure", json={"instance_id": "API-01", "down": True}, headers=admin)
    time.sleep(1.2)  # gate cache is 1s
    assert client.get("/threats", headers=admin).status_code == 503       # simulated-down instance refuses traffic
    assert client.get("/health").status_code == 200                       # liveness stays up
    assert client.get("/health/instance").status_code == 503
    client.post("/simulation/instance-failure", json={"instance_id": "API-01", "down": False}, headers=admin)
    time.sleep(1.2)
    assert client.get("/threats", headers=admin).status_code == 200
