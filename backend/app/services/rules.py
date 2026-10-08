from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.detection_engine import DETECTION_RULES
from app.models import SecurityRule

DEFAULT_RULES = [
    # key, name, description, category, toggleable
    ("RATE_LIMITING", "Rate Limiting", "Flags and throttles IPs above 500 requests/minute (blocks above 1500).", "detection", True),
    ("BRUTE_FORCE", "Brute-force Protection", "Blocks sources with more than 20 failed logins in 10 minutes.", "detection", True),
    ("SQL_INJECTION", "SQL Injection Protection", "Pattern-matches UNION SELECT, DROP TABLE, OR 1=1, SQL comments in paths and payloads.", "detection", True),
    ("XSS", "XSS Protection", "Detects <script>, javascript: URLs and inline event handlers such as onerror=.", "detection", True),
    ("PATH_TRAVERSAL", "Path Traversal Protection", "Detects ../ and ..\\ sequences, including URL-encoded forms.", "detection", True),
    ("JWT_AUTH", "JWT Authentication", "Every dashboard API call needs a signed, expiring bearer token. Always on.", "platform", False),
    ("RBAC", "Role-Based Access Control", "ADMIN can manage rules and run simulations; ANALYST is read-only. Always on.", "platform", False),
    ("INPUT_VALIDATION", "Input Validation", "All request bodies and query parameters are validated by typed schemas. Always on.", "platform", False),
    ("AUDIT_LOGGING", "Audit Logging", "Every evaluated request and admin action is written to the audit log. Always on.", "platform", False),
]


def ensure_rules(db: Session) -> None:
    existing = {r.key for r in db.scalars(select(SecurityRule))}
    for key, name, desc, cat, toggle in DEFAULT_RULES:
        if key not in existing:
            db.add(SecurityRule(key=key, name=name, description=desc, category=cat,
                                enabled=True, toggleable=toggle))
    db.commit()


def enabled_rule_keys(db: Session) -> set[str]:
    rows = db.scalars(select(SecurityRule).where(SecurityRule.enabled.is_(True))).all()
    return {r.key for r in rows if r.key in DETECTION_RULES}
