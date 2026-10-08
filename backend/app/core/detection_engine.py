"""CloudSentry rule-based detection engine.

Pure Python, no database access: easy to read, easy to unit-test.
Every request is turned into a RequestContext and evaluated into a Detection
(threat type, risk score 0-100, severity, automated action, human-readable reason).
"""
import re
from dataclasses import dataclass, field
from urllib.parse import unquote

# Rule keys (stored in the security_rules table, toggled by ADMIN)
RULE_RATE = "RATE_LIMITING"
RULE_BRUTE = "BRUTE_FORCE"
RULE_SQLI = "SQL_INJECTION"
RULE_XSS = "XSS"
RULE_TRAVERSAL = "PATH_TRAVERSAL"
DETECTION_RULES = [RULE_RATE, RULE_BRUTE, RULE_SQLI, RULE_XSS, RULE_TRAVERSAL]

RATE_LIMIT_RPM = 500          # requests/minute above which RATE_ABUSE is declared
RATE_BLOCK_RPM = 1500         # extreme floods are blocked instead of throttled
RATE_WARN_RPM = 250           # early-warning zone (MONITOR / THROTTLE)
BRUTE_LIMIT = 20              # failed logins above which BRUTE_FORCE is declared
BRUTE_WARN = 5

SQLI_PATTERNS = {
    "UNION SELECT": r"\bunion\b[\s\S]{0,20}\bselect\b",
    "SELECT ... FROM": r"\bselect\b[\s\S]+\bfrom\b",
    "DROP TABLE": r"\bdrop\s+(table|database)\b",
    "tautology (OR 1=1)": r"\bor\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+",
    "quote-based tautology": r"['\"]\s*or\s+['\"]?\w+['\"]?\s*=",
    "SQL comment": r"(--\s|--$|/\*[\s\S]*?\*/)",
    "stacked query": r";\s*(drop|delete|insert|update|alter)\b",
    "INSERT INTO": r"\binsert\s+into\b",
    "time-delay function": r"\bsleep\s*\(",
}
XSS_PATTERNS = {
    "<script tag": r"<\s*script",
    "javascript: URL": r"javascript\s*:",
    "inline event handler": r"\bon(error|load|click|mouseover|focus)\s*=",
    "<iframe tag": r"<\s*iframe",
}
TRAVERSAL_PATTERNS = {
    "../ sequence": r"\.\./",
    "..\\ sequence": r"\.\.\\",
    "encoded traversal": r"%2e%2e(%2f|%5c|/|\\)",
}


@dataclass
class RequestContext:
    source_ip: str
    endpoint: str
    method: str = "GET"
    request_count: int = 1          # requests per minute seen from this IP
    failed_logins: int = 0          # recent failed logins from this IP
    payload: str = ""
    status_code: int = 200
    response_time: float = 100.0    # ms
    user_role: str = "ANONYMOUS"


@dataclass
class Detection:
    threat_type: str = "NORMAL"
    risk_score: int = 5
    severity: str = "LOW"
    action: str = "ALLOW"
    reason: str = "No suspicious behaviour detected."
    rules_triggered: list[str] = field(default_factory=list)


def severity_for(risk: int) -> str:
    if risk >= 80:
        return "CRITICAL"
    if risk >= 60:
        return "HIGH"
    if risk >= 30:
        return "MEDIUM"
    return "LOW"


def action_for(risk: int) -> str:
    """0-29 ALLOW, 30-59 MONITOR, 60-79 THROTTLE, 80-100 BLOCK."""
    if risk >= 80:
        return "BLOCK"
    if risk >= 60:
        return "THROTTLE"
    if risk >= 30:
        return "MONITOR"
    return "ALLOW"


def _normalise(text: str) -> str:
    # decode URL-encoding twice so %252e%252e/ style evasion is caught too
    return unquote(unquote(text or ""))


def _matches(patterns: dict[str, str], text: str) -> list[str]:
    return [name for name, rx in patterns.items() if re.search(rx, text, re.IGNORECASE)]


def evaluate(ctx: RequestContext, enabled: set[str] | None = None) -> Detection:
    enabled = set(DETECTION_RULES) if enabled is None else enabled
    inspected = _normalise(f"{ctx.endpoint} {ctx.payload}")
    found: list[tuple[str, int, str]] = []  # (threat, risk, reason)

    if RULE_SQLI in enabled:
        hits = _matches(SQLI_PATTERNS, inspected)
        if hits:
            found.append(("SQL_INJECTION", min(99, 95 + len(hits) - 1),
                          f"SQL injection patterns in request ({', '.join(hits[:3])})."))
    if RULE_XSS in enabled:
        hits = _matches(XSS_PATTERNS, inspected)
        if hits:
            found.append(("XSS", min(98, 90 + 2 * (len(hits) - 1)),
                          f"Script injection patterns in request ({', '.join(hits[:3])})."))
    if RULE_TRAVERSAL in enabled:
        hits = _matches(TRAVERSAL_PATTERNS, inspected)
        if hits:
            found.append(("PATH_TRAVERSAL", min(96, 88 + 2 * (len(hits) - 1)),
                          f"Directory traversal sequence in request path ({', '.join(hits[:2])})."))
    if RULE_BRUTE in enabled and ctx.failed_logins >= BRUTE_WARN:
        if ctx.failed_logins > BRUTE_LIMIT:
            risk = min(99, 90 + (ctx.failed_logins - BRUTE_LIMIT) // 10)
            found.append(("BRUTE_FORCE", risk,
                          f"Abnormally high failed authentication attempts ({ctx.failed_logins} > {BRUTE_LIMIT})."))
        else:
            risk = 45 + (ctx.failed_logins - BRUTE_WARN) * 2
            found.append(("BRUTE_FORCE", risk,
                          f"Repeated failed logins ({ctx.failed_logins}); below block limit, monitoring."))
    if RULE_RATE in enabled and ctx.request_count >= RATE_WARN_RPM:
        rpm = ctx.request_count
        if rpm > RATE_LIMIT_RPM:
            risk = min(99, 85 + (rpm - RATE_LIMIT_RPM) // 100)
            found.append(("RATE_ABUSE", risk,
                          f"Request rate {rpm}/min exceeds the {RATE_LIMIT_RPM}/min limit."))
        else:
            risk = 45 + int((rpm - RATE_WARN_RPM) * 30 / (RATE_LIMIT_RPM - RATE_WARN_RPM))
            found.append(("RATE_ABUSE", risk,
                          f"Request rate {rpm}/min is approaching the {RATE_LIMIT_RPM}/min limit."))

    if not found:
        # Normal traffic: small baseline wobble so risk reflects mild signals
        risk = 5 + min(12, ctx.request_count // 25)
        if ctx.status_code in (401, 403):
            risk += 8
        if ctx.response_time > 1500:
            risk += 4
        risk = min(risk, 29)
        return Detection("NORMAL", risk, severity_for(risk), "ALLOW")

    found.sort(key=lambda f: f[1], reverse=True)
    threat, risk, reason = found[0]
    risk = min(100, risk + 3 * (len(found) - 1))  # multiple rules firing = extra suspicious
    action = action_for(risk)
    if threat == "RATE_ABUSE" and risk >= 60:
        # Rate abuse is throttled (HTTP 429); only extreme floods are blocked outright
        action = "BLOCK" if ctx.request_count > RATE_BLOCK_RPM else "THROTTLE"
    return Detection(threat, risk, severity_for(risk), action, reason, [f[0] for f in found])
