# Database

CloudSentry uses **PostgreSQL** in production and local Docker. Tables are created automatically on first start
(`Base.metadata.create_all`), and users, rules and 2,500 synthetic telemetry records are seeded if the database is empty,
so an empty database just works.

* `schema.sql` – the generated schema, for the project report / ER diagram. Running it by hand is optional.
* Re-seed manually: `cd backend && python -m app.services.seed --count 3000 --reset`

| Table | Purpose |
|-------|---------|
| `users` | ADMIN / ANALYST accounts (bcrypt hashes) |
| `traffic_events` | every evaluated request + risk score, threat type, action, serving instance |
| `audit_logs` | security trail: one row per evaluated request and per admin action |
| `security_rules` | detection rules that ADMIN can enable/disable |
| `instances` | backend heartbeat registry (also stores simulated-failure flag) |
| `traffic_ticks` | requests/second samples behind the live traffic chart |
| `simulation_state` | single row shared by all instances for the attack simulator |
