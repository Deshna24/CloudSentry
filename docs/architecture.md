# Architecture

## Overview
```
 Browser
   |  HTTPS
 React SPA  (Vercel in the cloud, nginx container locally)
   |  fetch + JWT bearer token
 Load balancer  (Nginx: round robin + retry on failure)
   |------------------------|
 FastAPI API-01        FastAPI API-02
   |  detection_engine.evaluate()  (in-process module)
   |------------------------|
 PostgreSQL (shared state)
```

## Components
| Component | Responsibility |
|-----------|----------------|
| React dashboard | Pages: Dashboard, Threats, Threat detail, Traffic, Instances, Security rules, Audit logs. Polls the API every 2-5 s |
| Load balancer | Alternates requests across instances; on connection errors or 502/503/504 retries on the other one |
| FastAPI instance | Stateless API. Knows its `INSTANCE_ID`, tags every response with `X-Instance-Id`, sends a heartbeat every 10 s |
| Detection engine | `app/core/detection_engine.py`. Pure function: request context in, risk score, threat type, severity, action and reason out |
| PostgreSQL | All state: users, traffic events, audit logs, rules, instance registry, simulation state |

## Request lifecycle (for evaluated requests)
```
Request -> build RequestContext (ip, endpoint, method, requests/min, failed logins, payload, status, latency, role)
        -> evaluate() against the enabled rules -> threat type + risk 0-100 + severity
        -> action band (allow / monitor / throttle / block)
        -> enforce (HTTP 403 / 429 for logins) and write traffic_events + audit_logs rows
```
Live: `POST /auth/login` and `POST /inspect`. Simulated: the attack simulator and seed script use the same code path.

## Load balancing and fault tolerance
* Instances share nothing in memory; any instance can serve any request. The JWT secret is identical on all instances.
* **Heartbeat:** each instance upserts `instances.last_heartbeat` every 10 s. Status = HEALTHY (under 20 s), WARNING (20-30 s), DOWN (over 30 s or flagged).
* **Simulated failure:** `POST /simulation/instance-failure` sets `forced_down`. That instance (cached for 1 s) answers 503 to everything except `/health`, `/simulation` and docs, so an admin can always bring it back. Nginx retries 503s on the other instance.
* **Load balancer status** on the dashboard is derived: healthy while at least one instance is up, down if none.
* **Failure handling:** database errors return a clean 503 JSON message; the heartbeat loop retries database initialisation in the background.

## Attack simulator
`POST /simulation/attack` starts an asyncio task that writes one tick per second: a requests/sec sample for the chart plus a
sample of evaluated requests (normal users plus three attacker IPs). Load levels: 80, 300, 700, 1200 req/s. Per-attacker
rates are 350, 900 and 1700 requests/min, which land in the monitor/throttle zone, the throttle zone and the block zone.
Brute-force, SQL injection, XSS and traversal events join in later phases. Run state is in the `simulation_state` table, so any
instance reports the same progress. `POST /simulation/reset` stops the run, deletes simulated and live telemetry and restores instances.

## Data model
See [database/schema.sql](../database/schema.sql) and [database/README.md](../database/README.md).

## Portability to AWS / Azure
The backend is a stateless container with env-based config. Mapping: Vercel to S3+CloudFront or Static Web Apps; Render
services to ECS Fargate or App Service; Nginx to an Application Load Balancer / Azure Load Balancer; PostgreSQL to RDS or
Azure Database for PostgreSQL. No code changes are needed, only environment variables.
