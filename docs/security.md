# Security

## Detection rules
All rules live in `backend/app/core/detection_engine.py` and are simple enough to read in one sitting.

| Rule key | Threat type | Trigger | Risk |
|----------|-------------|---------|------|
| `RATE_LIMITING` | RATE_ABUSE | requests/min above 500 | 85 + 1 per extra 100/min (max 99); 250-500/min scores 45-75 |
| `BRUTE_FORCE` | BRUTE_FORCE | failed logins above 20 | 90 + 1 per extra 10 (max 99); 5-20 failures score 45-75 |
| `SQL_INJECTION` | SQL_INJECTION | UNION SELECT, SELECT...FROM, DROP TABLE, OR 1=1, quote tautology, SQL comments, stacked queries, INSERT INTO, sleep() | 95-99 |
| `XSS` | XSS | `<script`, `javascript:`, `onerror=`/`onload=`/..., `<iframe` | 90-98 |
| `PATH_TRAVERSAL` | PATH_TRAVERSAL | `../`, `..\`, `%2e%2e%2f` (URL-decoded twice before matching) | 88-96 |

Payload rules inspect the endpoint plus payload text. If several rules fire, the highest risk wins and each extra rule adds 3.
Normal traffic scores 5-29 (small bumps for higher request rates, 401/403 responses and slow responses).

## Automated response
| Risk | Severity | Action | HTTP effect on login |
|------|----------|--------|----------------------|
| 0-29 | LOW | ALLOW | proceeds |
| 30-59 | MEDIUM | MONITOR | proceeds, flagged for analysts |
| 60-79 | HIGH | THROTTLE | 429 |
| 80-100 | CRITICAL | BLOCK | 403 |

**Design decision:** the brief gives rate abuse the action THROTTLE but also maps risk 80+ to BLOCK. CloudSentry resolves this as
follows: rate abuse is *throttled* even at 85+ risk, and blocked only above 1500 requests/min. Every other threat follows the
risk bands.

Failed *and throttled* login attempts count toward brute force, so persistent guessing escalates from monitor to throttle to
block instead of stalling at throttle. A login username that contains SQL injection is blocked and logged before any database lookup.

## Platform protections
| Control | Implementation |
|---------|----------------|
| Authentication | JWT (HS256, 8 h expiry), bcrypt hashes, secret from `JWT_SECRET`, startup refuses to run in production without it |
| Authorisation | `ADMIN`: rules, simulations, instance failure. `ANALYST`: read-only access to dashboard, threats, traffic, instances, logs |
| Input validation | Pydantic schemas (types, lengths, enums, ranges), sanitized 422 messages |
| Injection safety | SQLAlchemy parameterised queries only; captured payloads stored as inert text and rendered escaped by React |
| CORS | Allow-list from `CORS_ORIGINS` |
| Secrets | Only from environment; `.env` is git-ignored |
| Error handling | No stack traces or internals in responses; database outage returns a generic 503 |
| Audit logging | Every evaluated request and every admin action (rule changes, simulations, instance failure) |

## Safety of the simulator
All generated traffic is synthetic rows written to CloudSentry's own database. The code makes no outbound network calls, and
attack payload strings are never executed, only pattern-matched. Attacker addresses use reserved documentation IP ranges.

## Limitations
Regex detection can be bypassed and can false-positive; client IPs come from `X-Forwarded-For` (spoofable if the backend is
exposed directly); the JWT is kept in browser storage; there is no password reset or MFA. These are acceptable for a teaching project, not for production.
