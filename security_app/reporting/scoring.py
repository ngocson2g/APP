# security_app/reporting/scoring.py
"""
Compliance Score — điểm tuân thủ có trọng số theo severity.
Điểm 0–100: critical nặng hơn low (10:1).

Công thức:
  score = Σ(rules_ok × weight) / Σ(rules_total × weight) × 100
"""
from __future__ import annotations

from typing import Any

# Trọng số: critical ảnh hưởng gấp 10x so với low
SEVERITY_WEIGHTS: dict[str, int] = {
    "critical": 10,
    "high": 5,
    "medium": 2,
    "low": 1,
    "unknown": 1,
}


def compute_compliance_score(stats: dict[str, Any]) -> float:
    """
    Trả về điểm compliance 0.0–100.0, có trọng số severity.

    Parameters
    ----------
    stats : dict
        Output của ``compute_stats()`` — cần key ``by_severity``.

    Returns
    -------
    float
        Điểm compliance (0.0 nếu không có rule nào).
    """
    by_sev = stats.get("by_severity") or {}
    if not by_sev:
        return 0.0

    total_weight = 0
    passed_weight = 0

    for sev, data in by_sev.items():
        w = SEVERITY_WEIGHTS.get(str(sev).lower(), 1)
        rules = int(data.get("rules", 0))
        rules_fail = int(data.get("rules_fail", 0))
        rules_ok = rules - rules_fail

        total_weight += rules * w
        passed_weight += rules_ok * w

    if total_weight <= 0:
        return 0.0

    return round(passed_weight / total_weight * 100.0, 1)


def score_grade(score: float) -> str:
    """Chữ cái xếp hạng dựa trên điểm compliance."""
    if score >= 95:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 50:
        return "D"
    return "F"
