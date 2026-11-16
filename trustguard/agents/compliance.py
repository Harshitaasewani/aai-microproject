"""Agent 8 — Compliance Mapping Agent.

Maps every flag to a policy clause and region-specific regulatory reference, and writes a structured,
tamper-evident audit trail (each finding's evidence is hashed with SHA-256). The mapping is a
deterministic lookup table, deliberately not LLM-decided, so every mapping can be audited.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from ..data_loader import load_config
from ..models import AgentResult

NAME = "Compliance Mapping"
SEV_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}
MAX_EVIDENCE = 25


def run(results: dict[str, AgentResult], region: str) -> tuple[AgentResult, list[dict]]:
    pol = load_config("policies.json")
    reg = load_config("regions.json").get(region) or load_config("regions.json")["IN"]
    findings = []
    for agent_key, res in results.items():
        for f in res.flags:
            key = f.flag_type
            ctype = f.title.replace("Unverified ", "").replace(" claim", "") if key == "unverified_claim" else ""
            clause_id = pol["flag_to_clause"].get(f"{key}:{ctype}") or pol["flag_to_clause"].get(key, "7.2")
            clause = pol["clauses"][clause_id]
            area = clause["regulatory_area"]
            evidence_full = json.dumps(f.evidence, sort_keys=True, default=str)
            findings.append({
                "agent": res.agent, "agent_key": agent_key, "flag_type": key, "title": f.title, "detail": f.detail,
                "severity": f.severity, "confidence": round(res.confidence, 2),
                "policy_clause": f"Policy {clause_id}: {clause['title']}", "policy_category": clause["category"],
                "regulatory_exposure": area in pol["high_exposure_areas"],
                "regulatory_reference": reg["references"].get(area) if area else None,
                "evidence": f.evidence[:MAX_EVIDENCE], "evidence_count": len(f.evidence),
                "evidence_sha256": hashlib.sha256(evidence_full.encode()).hexdigest(),
                "recorded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })
    # regulatory exposure first, then severity, then confidence
    findings.sort(key=lambda x: (x["regulatory_exposure"], SEV_RANK[x["severity"]], x["confidence"]), reverse=True)
    for i, f in enumerate(findings, 1):
        f["finding_id"] = f"F-{i:03d}"
    clauses = sorted({f["policy_clause"] for f in findings})
    exposure = any(f["regulatory_exposure"] for f in findings)
    res = AgentResult(NAME, 0.0, 1.0, [], {
        "findings": len(findings), "clauses": clauses, "regulatory_exposure": exposure, "region": region,
        "region_name": reg["name"]}, f"{len(findings)} findings mapped to {len(clauses)} policy clauses"
                                     + (" — regulatory exposure present" if exposure else ""))
    return res, findings
