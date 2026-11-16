"""Agent 9 — Trust Risk Scoring Agent.

Aggregates agent scores into a 0-100 risk score:
    weighted_mean = Σ(w_i · c_i · s_i) / Σ(w_i · c_i)      (w = category weight, c = confidence, s = score)
    score         = 100 · (0.65 · weighted_mean + 0.35 · mean(top-2 scores))
The top-2 term stops two very strong signals from being diluted by clean categories. A single
critical, high-confidence finding (e.g. IP infringement) sets a floor so it cannot be averaged away.
Tiers are region-aware (config/regions.json). Because claims/visual results are cached by the
orchestrator, re-scoring when new reviews arrive only re-runs review-dependent agents.
"""
from __future__ import annotations

import numpy as np

from ..data_loader import load_config
from ..models import AgentResult

NAME = "Trust Risk Scoring"
DETECTORS = ["statistical", "linguistic", "network", "claims", "visual", "seller"]


def tier_for(score: float, region: str) -> str:
    regions = load_config("regions.json")
    t = (regions.get(region) or regions["IN"])["tiers"]
    if score >= t["Critical"]:
        return "Critical"
    if score >= t["High"]:
        return "High"
    if score >= t["Medium"]:
        return "Medium"
    return "Low"


def run(results: dict[str, AgentResult], findings: list[dict], region: str) -> AgentResult:
    cfg = load_config("weights.json")
    w = cfg["weights"]
    num = sum(w[k] * results[k].confidence * results[k].score for k in DETECTORS)
    den = sum(w[k] * results[k].confidence for k in DETECTORS) or 1
    weighted = num / den
    top2 = float(np.mean(sorted((results[k].score for k in DETECTORS), reverse=True)[:2]))
    score = 100 * (cfg["blend"]["weighted_mean"] * weighted + cfg["blend"]["top2_mean"] * top2)
    floor_applied = False
    fl = cfg["critical_floor"]
    if any(f["severity"] == "critical" and f["confidence"] >= fl["min_confidence"] for f in findings) and score < fl["floor_score"]:
        score, floor_applied = float(fl["floor_score"]), True
    score = round(min(100.0, score), 1)
    tier = tier_for(score, region)
    contrib = {k: round(100 * cfg["blend"]["weighted_mean"] * w[k] * results[k].confidence * results[k].score / den, 1)
               for k in DETECTORS}
    metrics = {"risk_score": score, "tier": tier, "weighted_mean": round(weighted, 3), "top2_mean": round(top2, 3),
               "agent_scores": {k: round(results[k].score, 2) for k in DETECTORS},
               "agent_confidence": {k: round(results[k].confidence, 2) for k in DETECTORS},
               "contribution_points": contrib, "critical_floor_applied": floor_applied, "region": region}
    return AgentResult(NAME, score / 100, 1.0, [], metrics, f"Aggregate risk score {score:.0f}/100 ({tier})")
