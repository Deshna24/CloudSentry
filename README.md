# CloudSentry

**Cloud-Based API Threat Detection & Automated Response Platform** - a Cloud Computing mini-project.

CloudSentry scores every API request from 0 to 100, detects brute force, request floods, SQL injection, XSS and
path traversal with a transparent rule engine, responds automatically (allow, monitor, throttle, block), and shows it all
on a Security Operations Center style dashboard. It runs as two load-balanced backend instances over PostgreSQL and
survives the loss of an instance.

> **Scope, stated plainly.** CloudSentry is an *educational simulation*. Login attempts and the Request Inspector go through
> the real detection engine live; the traffic on the charts comes from a built-in simulator and seeded telemetry. Nothing is
> ever sent to an external system and no payload is executed. See [Known limitations](#known-limitations).

## Problem statement
APIs are attacked constantly. Small teams usually find out from an outage or a breach report, and cloud-native apps add
a second problem: the security tooling must itself stay available when an instance fails. Commercial WAFs and SIEMs are
expensive and opaque, which makes them hard to learn from.

## Solution
A small cloud-native platform that makes the full loop visible and explainable: **request, detection, risk score, threat type,
automated action, audit log**, running on free-tier infrastructure with a load balancer and fault tolerance.

## Features
- Login with JWT and role-based access (ADMIN, ANALYST)
- Rule-based detection with risk score 0-100 and severity (low, medium, high, critical)
- Automated response: 0-29 allow, 30-59 monitor, 60-79 throttle (HTTP 429), 80-100 block (HTTP 403)
- Live dashboard: KPIs, requests/sec chart, threat level, threat distribution, system health, threat feed
- **Attack simulator** (traffic ramps 80 to 300 to 700 to 1200 req/s) with a live detection pipeline, plus reset
- Threat detail pages, searchable and filterable audit log, traffic analytics by endpoint, method, status and instance
- **Load balancing and failover**: two API instances behind Nginx, "simulate instance failure" with zero user-visible errors
- Admin-toggleable detection rules and a Request Inspector to try payloads safely
- Health endpoints, Swagger docs, Docker, Vercel/Render deployment guide, automated tests

## Architecture
```
 User -> React dashboard (Vercel / nginx)
              |
         Load balancer (Nginx)
          /            \
   FastAPI API-01   FastAPI API-02     <- same code, different INSTANCE_ID, heartbeat every 10 s
          \            /
     CloudSentry detection engine       <- a Python module inside each API instance
              |
          PostgreSQL                    <- events, audit log, rules, instance registry, simulation state
```
Details and diagrams in [docs/architecture.md](docs/architecture.md).

## Technology stack
| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, Tailwind CSS, Recharts, React Router |
| Backend | Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2 |
| Database | PostgreSQL (SQLite fallback for quick local runs) |
| Auth | JWT (PyJWT), bcrypt, role-based access control |
| Load balancer | Nginx |
| Packaging | Docker, Docker Compose |
| Hosting target | Vercel (frontend), Render (backend, database, LB), GitHub |

## Threat detection
| Threat | Trigger | Risk | Action |
|--------|---------|------|--------|
| Rate abuse | more than 500 requests/min from one IP | 85+ | throttle (block above 1500/min) |
| Brute force | more than 20 failed logins in 10 min | 90+ | block |
| SQL injection | UNION SELECT, DROP TABLE, OR 1=1, SQL comments, stacked queries | 95+ | block |
| XSS | `<script`, `javascript:`, `onerror=` and similar | 90+ | block |
| Path traversal | `../`, `..\`, URL-encoded variants | 88+ | block |

Below the limits, early-warning zones score 45-75 (rate 250-500/min, 5-20 failed logins) so monitor and throttle actually occur.
Normal traffic scores 5-29. Full rules and scoring in [docs/security.md](docs/security.md).

## Cloud architecture, load balancing and fault tolerance
Each backend instance is stateless: all shared state lives in PostgreSQL. Instances register with a heartbeat. The load
balancer alternates requests between them and retries a request on the other instance when one fails. "Simulate instance
failure" flags an instance as down in the database; it then answers 503, Nginx transparently retries on the other
instance, and the dashboard shows `API-01 down, API-02 healthy, load balancer healthy`. Every response carries an
`X-Instance-Id` header and every log row records the serving instance.

## Security
JWT with expiry, bcrypt password hashes, RBAC enforced on the server, typed input validation on every endpoint, parameterised
queries via the ORM, CORS allow-list, no secrets in code (all from environment variables), sanitized error responses
(no stack traces), and an audit trail of every decision and admin action.

## Dataset
On first start the backend seeds about 2,500 synthetic requests (configurable, up to 20,000) spread over 24 hours:
`request_id, timestamp, source_ip, endpoint, method, status_code, response_time, request_count, failed_logins,
payload_size, user_role, threat_type, risk_score, severity, action, instance_id`. Records are generated, then scored by the
same engine used live, so the data is consistent. Attacker IPs come from the documentation ranges (203.0.113.0/24,
198.51.100.0/24, 192.0.2.0/24). Re-seed: `python -m app.services.seed --count 3000 --reset`.

## Local setup (without Docker)
Requires Python 3.11+ and Node 18+. Without `DATABASE_URL` the backend uses a local SQLite file.
```bash
cd backend
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export SEED_ADMIN_PASSWORD='choose-a-password' SEED_ANALYST_PASSWORD='choose-another'   # optional
export REGISTER_INSTANCES=API-01,API-02     # one process plays both instances, for the failover demo
uvicorn app.main:app --reload               # API on http://localhost:8000, Swagger at /docs

cd frontend
npm install
npm run dev                                 # http://localhost:5173 (uses .env.development -> localhost:8000)
```
If you skip the password variables, random passwords are generated and printed once in the backend log.
`REGISTER_INSTANCES` is optional "logical instance" mode (the Instances page labels it); use Docker for real separate instances.

## Docker setup (recommended)
```bash
git clone <repo-url> && cd cloudsentry
docker compose up --build
```
| URL | What |
|-----|------|
| http://localhost:3000 | Dashboard |
| http://localhost:8080/docs | API docs through the load balancer |
| http://localhost:8001, :8002 | API-01 and API-02 directly |

Demo logins (local only, override in a root `.env`): **admin / Admin@CloudSentry1**, **analyst / Analyst@CloudSentry1**.
Stop with `Ctrl+C`; reset everything with `docker compose down -v`.

## AWS deployment (live)
CloudSentry is deployed on AWS (ap-south-1, Mumbai).

| Part | URL |
|------|-----|
| Frontend (S3 static website) | http://cloudsentry-28.s3-website.ap-south-1.amazonaws.com |
| Backend API (Application Load Balancer) | http://cs-alb-938746541.ap-south-1.elb.amazonaws.com |
| Swagger docs | http://cs-alb-938746541.ap-south-1.elb.amazonaws.com/docs |

```
 Browser -> S3 static website (React build)
              |
         Application Load Balancer (HTTP:80, health check /health/instance)
          /                    \
   EC2 cs-api-01 (AZ 1a)    EC2 cs-api-02 (AZ 1b)     <- Docker, FastAPI, INSTANCE_ID API-01 / API-02
          \                    /
        RDS PostgreSQL (private, encrypted)
 CloudWatch Logs + CloudWatch alarm (UnHealthyHostCount) -> SNS email
```

- **Security:** layered security groups (internet -> ALB only, app servers only from the ALB, database only from the app servers), private encrypted RDS, IAM role instead of access keys, Session Manager instead of SSH, secrets kept in a root-only env file outside the repository, CORS restricted to the S3 site.
- **High availability:** two instances in different Availability Zones behind the ALB; "Simulate instance failure" turns one target unhealthy while the other keeps serving.
- **Monitoring:** container logs in CloudWatch Logs and a CloudWatch alarm that emails through SNS when a target is unhealthy.

Full architecture, steps and verification notes: [docs/aws-deployment.md](docs/aws-deployment.md). The Render/Vercel route below remains as an alternative.

## Cloud deployment
Full steps in [docs/deployment.md](docs/deployment.md). Summary:
1. **Database** - Render PostgreSQL (or Supabase). Copy its connection string.
2. **Backend (Render)** - Web service, root directory `backend`, build `pip install -r requirements.txt`, start
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health check `/health`. Set `DATABASE_URL`, `JWT_SECRET`,
   `CORS_ORIGINS`, `ENVIRONMENT=production`, `INSTANCE_ID`.
3. **Second instance** - repeat with `INSTANCE_ID=API-02`, same `DATABASE_URL` and same `JWT_SECRET`; add the Nginx load
   balancer service (`lb/`, `LB_MODE=public`). Or use the free single-service "logical instance" fallback.
4. **Frontend (Vercel)** - import the repo, root directory `frontend`, set `VITE_API_URL` to the load balancer (or backend) URL.
5. Put the Vercel URL into the backend's `CORS_ORIGINS` and redeploy.

## Environment variables
| Variable | Where | Purpose |
|----------|-------|---------|
| `DATABASE_URL` | backend | PostgreSQL URL (`postgres://` and `postgresql://` both accepted). Empty = local SQLite |
| `JWT_SECRET` | backend | Signing key. Required in production, identical on every instance |
| `CORS_ORIGINS` | backend | Comma-separated allowed frontend origins |
| `INSTANCE_ID` | backend | Name of this instance, e.g. `API-01` |
| `EXPECTED_INSTANCES` | backend | Instances the dashboard expects (default `API-01,API-02`) |
| `REGISTER_INSTANCES` | backend | Optional logical mode: one process, several instance IDs |
| `ENVIRONMENT` | backend | `production` enforces `JWT_SECRET` |
| `AUTO_SEED`, `SEED_RECORDS` | backend | Seed demo telemetry when the DB is empty (default on, 2500) |
| `SEED_ADMIN_PASSWORD`, `SEED_ANALYST_PASSWORD` | backend | Demo user passwords (random if empty) |
| `TRUST_PROXY_HEADERS` | backend | Use `X-Forwarded-For` for client IP (default true; needed behind the LB) |
| `VITE_API_URL` | frontend (build time) | Backend or load balancer URL |

Samples: [.env.example](.env.example), [backend/.env.example](backend/.env.example), [frontend/.env.example](frontend/.env.example).

## API documentation
Swagger UI at `/docs`, summary in [docs/api.md](docs/api.md). Main routes: `POST /auth/login`, `GET /health`,
`GET /health/database`, `GET /health/detailed`, `GET /dashboard/summary`, `GET /traffic`, `GET /threats`, `GET /threats/{id}`,
`GET /instances`, `GET /audit-logs`, `POST /simulation/attack`, `POST /simulation/reset`, `POST /simulation/instance-failure`,
`GET /security-rules`, `PUT /security-rules/{id}`.

## Tests
```bash
cd backend && pytest -q                       # 31 tests: engine, auth, RBAC, detection, simulation, failover
cd frontend && VITE_API_URL=http://localhost:8000 SMOKE_USER=admin SMOKE_PASS=<password> npm test   # UI smoke test vs a running backend
```

## Demo instructions (3-5 minutes)
Full script with talking points in [docs/demo.md](docs/demo.md).
1. **Healthy system** - open the dashboard, show two healthy instances and the green status pill.
2. **Normal traffic** - switch on *Normal traffic*; show about 80 req/s, low threat level, requests allowed.
3. **Simulate attack** - click *Simulate attack*; watch traffic climb, the pipeline light up, risk rise, the source IP appear.
4. **Automatic response** - the chart turns amber (throttled) then red (blocked); the feed fills with incidents.
5. **Threat details** - open a threat: why it was detected, risk, action, serving instance.
6. **Instance failure** - Instances page, *Simulate instance failure* on API-01; API-02 keeps serving, no errors.
7. **Audit logs** - filter by threat type, show the full trail. Click *Reset simulation* to run again.

## Known limitations
- **Demo-grade detection.** Pattern matching, not a WAF. It can be evaded and can produce false positives.
- **Simulated traffic.** CloudSentry is not an inline proxy for another API. Only logins and the Request Inspector are
  evaluated live; chart traffic is simulated.
- **Derived load-balancer status.** It is healthy while at least one instance is up; there is no separate probe of Nginx.
- **Free-tier behaviour.** Render free services sleep when idle and show `DOWN` until woken (no heartbeat); wake both before a demo.
- **Simulation runs inside one instance.** If that instance restarts mid-run the run stops (detected after 10 s).
- **Client IP trust.** `X-Forwarded-For` is trusted by default; only expose the backend through your load balancer.
- **Basics only.** Two seeded accounts and no user-management UI; the JWT is kept in browser storage.
- **Not exercised here:** the Docker images and the Vercel/Render deployments themselves (see [docs/deployment.md](docs/deployment.md)
  for what was verified and how).

## Future scope
Inline proxy/middleware mode to protect a real API, Redis-backed sliding-window rate limits, optional anomaly detection
(isolation forest) as a second opinion, email/Slack alerts, IP allow/deny lists with expiry, user management, SIEM export,
and an AWS version (ALB, ECS/EC2, RDS) of the same architecture.
