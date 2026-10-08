"""Synthetic traffic generators used by the seed script and the attack simulator.

Everything here only produces inert text records inside our own database.
Nothing is ever sent to any external system, and no payload is executed.
"""
import random

from app.core.detection_engine import RequestContext

ENDPOINTS = [("/api/products", "GET"), ("/api/products", "GET"), ("/api/orders", "GET"),
             ("/api/orders", "POST"), ("/api/users/me", "GET"), ("/api/search", "GET"),
             ("/api/cart", "POST"), ("/api/payments", "POST"), ("/auth/login", "POST"),
             ("/api/reports", "GET"), ("/api/inventory", "PUT"), ("/api/orders", "DELETE")]
ROLES = ["USER"] * 6 + ["ANALYST", "ADMIN", "ANONYMOUS"]
SAFE_PAYLOADS = ['{"q": "laptop"}', '{"page": 2}', '{"item_id": 4412, "qty": 1}', "", "",
                 '{"q": "running shoes"}', '{"status": "shipped"}']
ATTACKER_IPS = ["203.0.113.14", "203.0.113.77", "198.51.100.23", "198.51.100.200", "192.0.2.58"]

SQLI = ["' OR 1=1 --", "admin' --", "1 UNION SELECT username, password FROM users",
        "'; DROP TABLE users; --", "SELECT * FROM accounts WHERE id=1 OR 1=1"]
XSS = ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "javascript:alert(document.cookie)",
       "<iframe src=javascript:alert(1)>"]
TRAVERSAL = ["/files/../../etc/passwd", "/download?file=..\\..\\windows\\win.ini",
             "/static/../../app/config", "/download?file=%2e%2e%2f%2e%2e%2fsecrets"]


def ip_pool(rng: random.Random, n: int = 45) -> list[str]:
    return [f"{rng.choice([10, 49, 103, 157, 172])}.{rng.randint(1, 250)}.{rng.randint(0, 250)}.{rng.randint(2, 250)}"
            for _ in range(n)]


_POOL = ip_pool(random.Random(7))


def normal_ctx(rng: random.Random) -> RequestContext:
    ep, method = rng.choice(ENDPOINTS)
    status = rng.choices([200, 201, 304, 404, 401, 500], [80, 6, 6, 4, 3, 1])[0]
    payload = rng.choice(SAFE_PAYLOADS) if method != "GET" or ep == "/api/search" else ""
    return RequestContext(
        source_ip=rng.choice(_POOL), endpoint=ep, method=method, request_count=rng.randint(1, 60),
        failed_logins=1 if (ep == "/auth/login" and status == 401) else 0, payload=payload,
        status_code=status, response_time=max(25, rng.lognormvariate(4.9, 0.45)),
        user_role=rng.choice(ROLES))


def rate_ctx(rng: random.Random, rpm: int, ip: str | None = None, endpoint: str | None = None) -> RequestContext:
    ep, method = (endpoint, "GET") if endpoint else rng.choice(ENDPOINTS[:8])
    return RequestContext(source_ip=ip or rng.choice(ATTACKER_IPS), endpoint=ep, method=method,
                          request_count=rpm, status_code=200,
                          response_time=rng.uniform(120, 400) + rpm * 0.4, user_role="ANONYMOUS")


def brute_ctx(rng: random.Random, failed: int, ip: str | None = None, endpoint: str | None = None) -> RequestContext:
    ep = endpoint or "/auth/login"
    return RequestContext(source_ip=ip or rng.choice(ATTACKER_IPS), endpoint=ep, method="POST",
                          request_count=rng.randint(30, 140), failed_logins=failed,
                          payload='{"username": "admin", "password": "***"}', status_code=401,
                          response_time=rng.uniform(90, 260), user_role="ANONYMOUS")


def sqli_ctx(rng: random.Random, ip: str | None = None, endpoint: str | None = None) -> RequestContext:
    ep = endpoint or rng.choice(["/api/search", "/api/products"])
    return RequestContext(source_ip=ip or rng.choice(ATTACKER_IPS), endpoint=ep,
                          method="GET", request_count=rng.randint(5, 80), payload=rng.choice(SQLI),
                          status_code=400, response_time=rng.uniform(60, 220), user_role="ANONYMOUS")


def xss_ctx(rng: random.Random, ip: str | None = None, endpoint: str | None = None) -> RequestContext:
    ep = endpoint or rng.choice(["/api/cart", "/api/orders"])
    return RequestContext(source_ip=ip or rng.choice(ATTACKER_IPS), endpoint=ep,
                          method="POST", request_count=rng.randint(5, 80), payload=rng.choice(XSS),
                          status_code=400, response_time=rng.uniform(60, 220), user_role="ANONYMOUS")


def traversal_ctx(rng: random.Random, ip: str | None = None, endpoint: str | None = None) -> RequestContext:
    if endpoint and (".." in endpoint or "/files" in endpoint):
        ep = endpoint
    elif endpoint:
        ep = f"{endpoint.rstrip('/')}/../../etc/passwd"
    else:
        ep = rng.choice(TRAVERSAL)
    return RequestContext(source_ip=ip or rng.choice(ATTACKER_IPS), endpoint=ep,
                          method="GET", request_count=rng.randint(5, 80), payload="",
                          status_code=404, response_time=rng.uniform(40, 150), user_role="ANONYMOUS")
