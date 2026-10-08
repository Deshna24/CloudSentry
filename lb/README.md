# CloudSentry load balancer

Tiny Nginx reverse proxy for the load-balancing and fault-tolerance demo. Two modes (`LB_MODE`):

| Mode | Use for | Variables |
|------|---------|-----------|
| `internal` (default) | docker compose / same network | `UPSTREAM_1=api1:8000`, `UPSTREAM_2=api2:8000` |
| `public` | two hosted services reachable by HTTPS URL (Render) | `UPSTREAM_1_HOST=cloudsentry-api-01.onrender.com`, `UPSTREAM_2_HOST=...`, `UPSTREAM_PORT=443`, `UPSTREAM_SCHEME=https` |

`PORT` (default 80) is the port the proxy listens on. Both modes retry a request on the other instance when one
answers 502/503/504 or is unreachable, which is what makes the "simulate instance failure" demo work.
