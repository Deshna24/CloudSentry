"""Pure unit tests of the detection engine (no database, no HTTP)."""
from app.core.detection_engine import RequestContext, action_for, evaluate, severity_for


def ctx(**kw):
    return RequestContext(source_ip="1.2.3.4", endpoint=kw.pop("endpoint", "/api/products"), **kw)


def test_normal_request_is_allowed_with_low_risk():
    d = evaluate(ctx(request_count=5))
    assert (d.threat_type, d.risk_score, d.action, d.severity) == ("NORMAL", 5, "ALLOW", "LOW")


def test_brute_force_blocks_above_20_failures():
    d = evaluate(ctx(endpoint="/auth/login", method="POST", failed_logins=87))
    assert d.threat_type == "BRUTE_FORCE" and d.risk_score >= 90 and d.action == "BLOCK"


def test_brute_force_below_limit_is_not_blocked():
    d = evaluate(ctx(endpoint="/auth/login", failed_logins=8))
    assert d.threat_type == "BRUTE_FORCE" and d.action == "MONITOR" and 30 <= d.risk_score < 60


def test_rate_abuse_is_throttled_above_500_per_minute():
    d = evaluate(ctx(request_count=700))
    assert d.threat_type == "RATE_ABUSE" and d.risk_score >= 85 and d.action == "THROTTLE"


def test_extreme_rate_abuse_is_blocked():
    assert evaluate(ctx(request_count=1800)).action == "BLOCK"


def test_rate_at_limit_is_not_abuse():
    assert evaluate(ctx(request_count=500)).threat_type == "RATE_ABUSE"  # early-warning zone
    assert evaluate(ctx(request_count=500)).action != "BLOCK"
    assert evaluate(ctx(request_count=100)).threat_type == "NORMAL"


def test_sql_injection_variants_are_blocked():
    for p in ["' OR 1=1 --", "1 UNION SELECT user,pass FROM users", "'; DROP TABLE users; --",
              "SELECT * FROM accounts"]:
        d = evaluate(ctx(payload=p))
        assert d.threat_type == "SQL_INJECTION" and d.risk_score >= 95 and d.action == "BLOCK", p


def test_xss_variants_are_blocked():
    for p in ["<script>alert(1)</script>", "javascript:alert(1)", "<img src=x onerror=alert(1)>"]:
        d = evaluate(ctx(payload=p))
        assert d.threat_type == "XSS" and d.action == "BLOCK", p


def test_path_traversal_is_blocked_including_encoded():
    for e in ["/files/../../etc/passwd", "/dl?f=..\\..\\win.ini", "/dl?f=%2e%2e%2fsecret", "/dl?f=%252e%252e%252fx"]:
        d = evaluate(ctx(endpoint=e))
        assert d.threat_type == "PATH_TRAVERSAL" and d.action == "BLOCK", e


def test_harmless_text_is_not_flagged():
    for p in ['{"q": "select a good laptop"}', '{"note": "well-known brand"}', "weather in Pune"]:
        assert evaluate(ctx(payload=p)).threat_type == "NORMAL", p


def test_disabled_rule_is_skipped():
    d = evaluate(ctx(payload="' OR 1=1 --"), enabled={"XSS"})
    assert d.threat_type == "NORMAL"


def test_risk_bands_and_automated_response():
    assert [action_for(r) for r in (0, 29, 30, 59, 60, 79, 80, 100)] == \
        ["ALLOW", "ALLOW", "MONITOR", "MONITOR", "THROTTLE", "THROTTLE", "BLOCK", "BLOCK"]
    assert [severity_for(r) for r in (5, 45, 75, 95)] == ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def test_risk_always_between_0_and_100():
    d = evaluate(ctx(payload="' OR 1=1 -- <script>", endpoint="/../x", failed_logins=999, request_count=99999))
    assert 0 <= d.risk_score <= 100
