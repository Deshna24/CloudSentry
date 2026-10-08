# Demo script (3-5 minutes)

**Before you start:** open the dashboard once and sign in as `admin`. On free hosting, open each backend URL's `/health` first so
no instance is asleep. Click *Reset simulation* so you start clean.

| Step | Do | Say |
|------|----|-----|
| 1. Healthy system | Show the status pill, System health panel (Load balancer, API-01, API-02, Database all healthy) | "Two backend instances sit behind a load balancer over one PostgreSQL database." |
| 2. Normal traffic | Switch on **Normal traffic** | "About 80 requests a second. Risk is low and everything is allowed." |
| 3. Simulate attack | Click **Simulate attack** | "Traffic climbs 80, 300, 700, 1200 req/s. Watch the pipeline: spike, detection, risk score, source IP, action, incident." |
| 4. Automatic response | Point at the chart turning amber then red, and the threat feed | "Rate abuse is throttled; brute force, SQL injection, XSS and traversal are blocked, with no human involved." |
| 5. Threat details | Open an incident (for example brute force) | "Source IP, endpoint, risk, why it was flagged, action, and which instance processed it." |
| 6. Instance failure | Instances page, **Simulate instance failure** on API-01 | "API-01 is down; the load balancer retries on API-02. The dashboard keeps working." Then open Traffic to show 100% on API-02. Recover it. |
| 7. Audit logs | Audit logs page, filter by threat type or action | "Every decision and admin action is recorded with user, IP, risk, action and instance." |

**Bonus (30 s):** Security rules, turn off *SQL Injection Protection*, run the SQL injection preset in the Request Inspector (it is allowed),
turn the rule back on and run it again (blocked). Or fail 25 logins on the login page to see your own IP get throttled, then blocked.

Reset between runs with **Reset simulation** (it also restores failed instances).

## Expected questions
* *Is this real traffic?* Logins and the inspector are live; chart traffic is simulated. Nothing leaves the app.
* *Why not machine learning?* Rules are transparent and explainable, and the platform must work without ML. Anomaly detection is listed as future scope.
* *What if the database goes down?* APIs return a clean 503 and `/health` stays up; the instances reconnect on their own.
