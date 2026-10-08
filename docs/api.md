# API reference

Interactive docs: `/docs` (Swagger UI) and `/redoc` on any instance. All routes except `/`, `/health*` and `POST /auth/login`
need `Authorization: Bearer <token>`. Every response includes the header `X-Instance-Id`.

| Method | Path | Role | Purpose |
|--------|------|------|---------|
| POST | `/auth/login` | public | `{username, password}` returns `{access_token, role, instance_id}`. 401 bad credentials, 403 blocked, 429 throttled |
| GET | `/auth/me` | any | current user |
| GET | `/health` | public | liveness: `{"status":"healthy","service":"cloudsentry-api","instance_id":...}` (no DB access) |
| GET | `/health/instance` | public | 503 while this instance is in simulated failure |
| GET | `/health/database` | public | database connectivity and latency (503 if down) |
| GET | `/health/detailed` | public | overall status, database, load balancer and every instance (used by the dashboard) |
| GET | `/dashboard/summary` | any | KPIs, threat level, distribution, last 60 requests/sec samples, recent threats, simulation state |
| GET | `/traffic?minutes=60` | any | timeline, by endpoint, method, status code, instance share, latest requests |
| GET | `/threats` | any | filters: `threat_type, severity, action, q, date_from, date_to, limit, offset` |
| GET | `/threats/{id}` | any | detail; `id` is `CS-1042` or the numeric id |
| POST | `/inspect` | any | evaluate a described request: `{endpoint, method, payload, request_count, failed_logins}` and log it |
| GET | `/instances` | any | load balancer, instances (status, heartbeat, share), database |
| GET | `/audit-logs` | any | same filters as threats plus normal requests and admin actions |
| GET | `/security-rules` | any | list rules |
| PUT | `/security-rules/{id}` | ADMIN | `{enabled}`; platform rules cannot be disabled (400) |
| POST | `/simulation/attack` | ADMIN | `{scenario}`: `full`, `rate_abuse`, `brute_force`, `sql_injection`, `xss`, `path_traversal`; 409 if already running |
| POST | `/simulation/normal` | ADMIN | one second of normal traffic (the dashboard toggle calls this every 2 s) |
| POST | `/simulation/reset` | ADMIN | stop run, clear simulated/live telemetry, restore instances |
| POST | `/simulation/instance-failure` | ADMIN | `{instance_id, down}`; 404 if the instance never registered |
| GET | `/simulation/status` | any | `{active, phase, current_rps, ...}` |

## Error format
```json
{ "detail": "Human readable message" }
```
Codes: 401 not authenticated, 403 forbidden or blocked, 404 not found, 409 conflict, 422 validation, 429 throttled,
503 database unavailable or instance down, 500 unexpected (no internals exposed).

## Example
```bash
TOKEN=$(curl -s -X POST http://localhost:8080/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Admin@CloudSentry1"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -s -X POST http://localhost:8080/inspect -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"endpoint":"/api/search","payload":"1 UNION SELECT user,pass FROM users"}'
# -> {"threat_type":"SQL_INJECTION","risk_score":95+,"action":"BLOCK", ...}
```
