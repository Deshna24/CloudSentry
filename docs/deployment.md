# Deployment guide

Everything below uses free tiers. Check each provider's current free-plan limits before relying on them.

## What has and has not been verified
Verified on a development machine: the backend (31 automated tests), the backend with **real PostgreSQL 16**, two API instances behind **real
Nginx** (round robin, failover for GET and POST, shared simulation state, database outage handling), both load-balancer templates, the
frontend production build, and a UI smoke test against a live API. **Not run in the build environment:** `docker compose` itself (Docker was
unavailable), and the Vercel/Render/Supabase deployments. Their steps follow each provider's standard flow; run through them once before the
demo day and treat `render.yaml` as an unverified convenience.

## Recommended student deployment (free)
GitHub, Vercel (frontend), Render (backend + database + load balancer).

### 1. GitHub
Push the repository. Do not commit `.env`. Keep `frontend/.env.development` (it has no secrets).

### 2. Database (Render PostgreSQL)
1. Render dashboard, **New +**, **PostgreSQL**, name `cloudsentry-db`, Free plan.
2. Copy the **Internal Database URL** if the backend is also on Render in the same region, otherwise the **External** URL.

*Supabase alternative:* create a project, copy the connection string (Database settings), and append `?sslmode=require` if it is missing.

### 3. Backend instance 1 (Render)
1. **New +**, **Web Service**, connect the GitHub repo.
2. Settings: Runtime **Python 3**, **Root Directory** `backend`, Build `pip install -r requirements.txt`,
   Start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, Health check path `/health`, Free plan.
3. Environment variables:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | the database URL from step 2 |
| `JWT_SECRET` | output of `python -c "import secrets; print(secrets.token_urlsafe(48))"` (use the same value on every instance) |
| `CORS_ORIGINS` | your Vercel URL, e.g. `https://cloudsentry.vercel.app` (add it after step 6, then redeploy) |
| `ENVIRONMENT` | `production` |
| `INSTANCE_ID` | `API-01` |
| `SEED_ADMIN_PASSWORD`, `SEED_ANALYST_PASSWORD` | passwords you choose |
| `PYTHON_VERSION` | `3.12.7` (recommended) |

4. Deploy. Open `https://<service>.onrender.com/health` and `/docs`. On first start the tables, users, rules and about 2,500 demo
   records are created automatically.

### 4. Backend instance 2 and load balancer (true multi-instance)
1. Create a **second** Web Service from the same repo with the same settings, but `INSTANCE_ID=API-02`. Use the **same** `DATABASE_URL`
   and **same** `JWT_SECRET`.
2. Create a third service: **New +**, **Web Service**, same repo, Runtime **Docker**, **Root Directory** `lb`. Environment variables:

| Key | Value |
|-----|-------|
| `LB_MODE` | `public` |
| `UPSTREAM_1_HOST` | hostname of instance 1 without `https://`, e.g. `cloudsentry-api-01.onrender.com` |
| `UPSTREAM_2_HOST` | hostname of instance 2, e.g. `cloudsentry-api-02.onrender.com` |

3. Check `https://<lb-service>.onrender.com/lb-health`, then `/health/detailed` through the LB; you should see both instances healthy
   and responses alternate `X-Instance-Id`.
4. The LB URL is your **API URL** from here on.

### 5. Simplest alternative: one service ("logical instances")
Skip step 4. On the single backend service add `REGISTER_INSTANCES=API-01,API-02`. One process then registers both instance IDs and
emulates the routing inside the API, so the dashboard and the failover demo still work. The Instances page labels this mode as *logical*.
Use real separate instances if your report claims true multi-instance deployment.

### 6. Frontend (Vercel)
1. **Add New**, **Project**, import the repo.
2. **Root Directory:** `frontend`. Framework preset **Vite** (build `npm run build`, output `dist`).
3. Environment variable `VITE_API_URL` = the load balancer URL (or the single backend URL), no trailing slash.
4. Deploy. `frontend/vercel.json` rewrites all routes to `index.html` so page refreshes work.
5. Copy the Vercel URL into the backends' `CORS_ORIGINS` and redeploy them. Open the site and sign in.

### Free-tier tips
* Free Render services sleep after about 15 minutes idle and take up to a minute to wake. A sleeping instance sends no heartbeat, so the
  dashboard shows it as Down until it wakes. **Open both service `/health` URLs a few minutes before the demo.**
* Free databases may be time-limited; check the plan and keep a copy of `database/schema.sql` and your seed settings.

## Optional render.yaml
`render.yaml` in the repo root describes the database, both instances and the load balancer for **New +, Blueprint**. After the first
deploy set `CORS_ORIGINS`, the demo passwords and the two `UPSTREAM_*_HOST` values in the dashboard. It was not run in the build environment.

## Local multi-instance demo
`docker compose up --build` starts PostgreSQL, API-01, API-02, the Nginx load balancer and the frontend. See the README.

## Optional AWS deployment (not required)
| CloudSentry part | AWS service |
|------------------|-------------|
| Frontend (`npm run build`) | S3 + CloudFront |
| Backend containers (`backend/Dockerfile`) | ECS Fargate (2 tasks) or two EC2 instances |
| Load balancer | Application Load Balancer, target group health check `/health` (use `/health/instance` to make a simulated failure drain the instance) |
| Database | RDS PostgreSQL, set `DATABASE_URL` |
| Secrets | Secrets Manager or SSM Parameter Store for `JWT_SECRET` |

Set `TRUST_PROXY_HEADERS=true` behind the ALB. Costs money beyond free-tier credits, so it is not part of the recommended path.

## Troubleshooting
| Symptom | Fix |
|---------|-----|
| Dashboard says "Cannot reach the API" | `VITE_API_URL` wrong or not set at build time (rebuild/redeploy after changing it) |
| Browser console shows a CORS error | Add the exact frontend origin (no trailing slash) to `CORS_ORIGINS`, redeploy the backend |
| Login works on one instance and fails on the other | `JWT_SECRET` differs between instances |
| Backend exits at start with "JWT_SECRET must be set" | Set `JWT_SECRET` (required when `ENVIRONMENT=production`) |
| 503 "Database unavailable" | Wrong or unreachable `DATABASE_URL`; check `/health/database` |
| API-02 always Down | The second instance is not deployed, is asleep, or `INSTANCE_ID` does not match `EXPECTED_INSTANCES` |
| Locked out after failed logins | Brute-force protection; wait 10 minutes or ask an admin to run Reset simulation from another IP |
