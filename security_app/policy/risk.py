# security_app/policy/risk.py
"""
Đánh giá risk level của commands
"""
import re
from dataclasses import dataclass

SENSITIVE_PATHS = [
    r"/etc\b", r"/boot\b", r"/var/log\b", r"/var/lib\b", r"/root\b",
    r"/proc/sys\b", r"/(passwd|shadow|sudoers)\b", r"/ssh(_|d_)?config\b",
]
WRITE_PATTERNS = [
    r">\s*/\S+", r">>\s*/\S+", r"\|\s*tee(\s+-a)?\b", r"\bsed\s+-i\b",
    r"\brm\s+-r?f?\b", r"\bchmod\b", r"\bchown\b", r"\bmv\b", r"\bcp\s+-f\b",
    r"\bdd\s+of=", r"\bmount\b", r"\bsysctl\s+-w\b",
    r"\bsystemctl\b\s+(enable|disable|restart|stop|mask|unmask)\b",
    r"\bapt(-get)?\s+(install|remove)\b", r"\bdpkg\s+-i\b",
    r"\b(iptables|nft|ufw)\b", r"\b(useradd|usermod|passwd)\b",
    r"\bip\s+(route|link|addr)\b\s+(add|del|set)\b",
]
SCOPE_FLAGS = [r"\s-[Rr]\b", r"[\*\?\[]", r"\bfind\s+/\b", r"\|.*\|.*\|"]  # >2 pipes

DRYRUN_HINTS = [r"\b--dry-run\b", r"\b--check\b", r"\s-(n|C)\b"]
HOME_HINT = r"\s~/"

@dataclass
class Risk:
    level: str
    score: int
    factors: list[str]

def compute_risk(cmd: str) -> Risk:
    s = cmd.strip()
    score, factors = 0, []

    # destructive / write class
    if any(re.search(p, s) for p in WRITE_PATTERNS):
        score += 40 
        factors.append("write/state-change")
    if re.search(r"\brm\s+-r?f?\s+/", s) or re.search(r"\bdd\s+of=/dev/", s):
        score += 80 
        factors.append("destructive")

    # sensitive paths
    sp_hits = [p for p in SENSITIVE_PATHS if re.search(p, s, re.I)]
    if sp_hits:
        mult = 1.0
        if re.search(r"/etc\b", s): 
            mult *= 1.5
        if re.search(r"/var/log\b", s): 
            mult *= 1.3
        if re.search(r"\s/(\s|$)", s): 
            mult *= 1.8
        score = int(score * mult)
        factors += [f"path:{h}" for h in sp_hits[:3]]

    # scope amplifiers
    if any(re.search(p, s) for p in SCOPE_FLAGS):
        score += 25 
        factors.append("wide-scope")

    # mitigations
    if any(re.search(p, s) for p in DRYRUN_HINTS):
        score -= 20 
        factors.append("dry-run")
    if re.search(HOME_HINT, s):
        score -= 10 
        factors.append("home-scope")

    score = max(0, score)
    level = "low" if score < 30 else "medium" if score < 60 else "high" if score < 80 else "critical"
    return Risk(level, score, factors[:5])
