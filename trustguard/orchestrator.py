"""Agent 10 — Orchestrator Agent.

Pipeline:
  1. Ingestion                                  (Agent 1)
  2. Detectors in parallel                      (Agents 2-6: statistical, linguistic, network, claims, visual)
  3. Seller risk correlation using 2's output   (Agent 7)
  4. Compliance mapping + audit trail           (Agent 8)
  5. Trust risk scoring                         (Agent 9)
  6. Conflict resolution, case memory, routing  (this module)

The orchestrator never enforces. Its output is a decision *recommendation* plus a queue for humans;
when review-signal agents disagree it marks the case "needs manual review" instead of deciding.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from . import case_memory, llm
from .agents import claims, compliance, ingestion, linguistic, network, scoring, seller, statistical, visual
from .data_loader import MarketData, load_market
from .models import AgentResult

REVIEW_AGENTS = ["statistical", "linguistic", "network"]
AGENT_TITLES = {
    "ingestion": "1 · Review & Metadata Ingestion", "statistical": "2 · Statistical Anomaly Detection",
    "linguistic": "3 · Linguistic Pattern", "network": "4 · Reviewer Network",
    "claims": "5 · Product Claim Verification", "visual": "6 · Visual Counterfeit Signal",
    "seller": "7 · Seller Risk Correlation", "compliance": "8 · Compliance Mapping",
    "scoring": "9 · Trust Risk Scoring", "orchestrator": "10 · Orchestrator",
}


class Orchestrator:
    def __init__(self, market: MarketData | None = None):
        self.market = market or load_market()
        self._static_cache: dict[str, dict[str, AgentResult]] = {}  # claims/visual don't change with new reviews

    # ------------------------------------------------------------------
    def run(self, product_id: str, region: str | None = None, as_of: pd.Timestamp | None = None,
            use_llm: bool = True) -> dict:
        trace = []

        def timed(key, fn, *a):
            t0 = time.perf_counter()
            out = fn(*a)
            trace.append({"agent": AGENT_TITLES[key], "ms": round((time.perf_counter() - t0) * 1000, 1)})
            return out

        case = timed("ingestion", ingestion.run, self.market, product_id, as_of)
        region = region or case.seller["region"]

        # Detectors are independent -> run them concurrently. Claims/visual are cached per product, so
        # a re-score after new reviews only recomputes review-dependent agents (incremental scoring).
        static = self._static_cache.get(product_id)
        jobs = {"statistical": statistical.run, "linguistic": linguistic.run, "network": network.run}
        if static is None:
            jobs |= {"claims": claims.run, "visual": visual.run}
        results: dict[str, AgentResult] = {}
        with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
            futs = {k: ex.submit(timed, k, fn, case) for k, fn in jobs.items()}
            for k, f in futs.items():
                results[k] = f.result()
        if static is None:
            static = {"claims": results["claims"], "visual": results["visual"]}
            self._static_cache[product_id] = static
        else:
            results |= static
            trace.append({"agent": "5/6 · Claims + Visual", "ms": 0.0, "note": "cached (incremental rescore)"})

        results["seller"] = timed("seller", seller.run, case, results)
        comp_res, findings = timed("compliance", compliance.run, results, region)
        score_res = timed("scoring", scoring.run, results, findings, region)

        t0 = time.perf_counter()
        decision = self._decide(results, findings, score_res)
        memory = case_memory.similar_cases(self.market.cases, {k: results[k].score for k in scoring.DETECTORS})
        explanation = (llm.explain(case.summary, findings, score_res.metrics) if use_llm else None) \
            or self._template_explanation(case.summary, findings, results)
        trace.append({"agent": AGENT_TITLES["orchestrator"], "ms": round((time.perf_counter() - t0) * 1000, 1)})

        return {
            "case_id": f"CASE-{product_id}-{case.as_of:%Y%m%d}",
            "generated_at_utc": pd.Timestamp.now("UTC").isoformat(timespec="seconds"),
            "as_of_utc": case.as_of.isoformat(),
            "region": region,
            "product": case.summary,
            "data_quality": case.data_quality,
            "risk_score": score_res.metrics["risk_score"],
            "tier": score_res.metrics["tier"],
            "scoring": score_res.metrics,
            "decision": decision,
            "summary_table": self._summary_table(findings, score_res, decision, explanation),
            "explanation": explanation,
            "explanation_source": "llm" if (use_llm and llm.available()) else "template",
            "findings": findings,
            "compliance": comp_res.metrics,
            "agents": {k: v.to_dict() for k, v in results.items()},
            "case_memory": memory,
            "trace": trace,
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _decide(results: dict[str, AgentResult], findings: list[dict], score_res: AgentResult) -> dict:
        tier = score_res.metrics["tier"]
        confident = {k: results[k].score for k in REVIEW_AGENTS if results[k].confidence >= 0.6}
        conflict = None
        if len(confident) >= 2:
            hi_k, lo_k = max(confident, key=confident.get), min(confident, key=confident.get)
            if confident[hi_k] >= 0.6 and confident[lo_k] <= 0.3:
                conflict = (f"{results[hi_k].agent} signal is high ({confident[hi_k]:.2f}) but "
                            f"{results[lo_k].agent} signal is low ({confident[lo_k]:.2f})")
        types = {f["flag_type"] for f in findings}
        ip = bool(types & {"unauthorized_brand", "brand_image_match"})
        ring = bool(types & {"coordinated_network", "seller_exclusive_reviewers"})
        recs = []
        if tier in ("High", "Critical") and ring:
            recs.append("Escalate to compliance for seller audit (coordinated review activity)")
            recs.append("Suppress rating badge pending investigation")
        if "near_duplicate_text" in types or "coordinated_network" in types:
            n = results["linguistic"].metrics.get("near_duplicate_share", 0)
            recs.append(f"Hold suspected reviews (~{n:.0%} of total) out of the star rating pending human review")
        if "incentivized_disclosure" in types:
            recs.append("Verify incentive-disclosure compliance; exclude incentivized reviews from the star rating")
        if ip:
            recs.append("Route to brand-protection / legal: request proof of authenticity and brand authorization from seller")
        unverified = [c["claim"] for c in results["claims"].metrics.get("claims_found", []) if not c["verified"]]
        if unverified:
            recs.append("Request supporting documents for: " + ", ".join(f"\"{c}\"" for c in unverified))
        if "rapid_relisting" in types:
            recs.append("Review all active listings of this seller for relisting evasion")
        if conflict:
            recs.insert(0, "Signals conflict — manual review required before any action")
        if tier == "Medium" and not recs:
            recs.append("Add to monitoring; re-score as new reviews arrive")
        if tier == "Low" and not recs:
            recs.append("No action — continue routine monitoring")

        if ip:
            queue = "Legal / IP Enforcement"
        elif conflict:
            queue = "Manual Review"
        elif tier in ("High", "Critical"):
            queue = "Trust & Safety — Seller Audit"
        elif tier == "Medium":
            queue = "Monitoring"
        else:
            queue = "None (routine monitoring)"
        status = "needs_manual_review" if conflict else ("escalate" if tier in ("High", "Critical") else
                                                         "monitor" if tier == "Medium" else "no_action")
        return {"status": status, "queue": queue, "conflict": conflict, "recommendations": recs,
                "enforcement": "None taken automatically — all actions require human approval"}

    @staticmethod
    def _template_explanation(summary: dict, findings: list[dict], results: dict[str, AgentResult]) -> str:
        if not findings:
            return "No anomalies detected across review, network, claim, image or seller signals."
        top = [f["title"].lower() for f in findings[:4]]
        parts = [f"Evidence is consistent with {', '.join(dict.fromkeys(top))}."]
        if results["network"].score >= 0.6 and results["statistical"].score >= 0.6:
            parts.append("The review burst is driven by a coordinated cluster of new, single-category accounts, "
                         "matching a known incentivized review-ring signature.")
        if results["seller"].score >= 0.5:
            parts.append(f"Seller account age ({summary['seller_account_age_days']} days) is inconsistent with "
                         f"its review volume and the seller has recent flags on file.")
        types = {f["flag_type"] for f in findings}
        if types & {"brand_image_match", "unauthorized_brand"}:
            parts.append("The listing uses protected brand imagery and authenticity claims from a seller who is not "
                         "an authorized reseller, at a price far below brand MSRP — signals consistent with counterfeit goods.")
        elif "reused_image" in types:
            parts.append("The product photo is not original: the same image appears on listings of unrelated sellers.")
        if "unverified_claim" in types:
            parts.append("Material/origin/certification claims in the listing have no supporting documents on file.")
        if "incentivized_disclosure" in types and results["network"].score < 0.3:
            parts.append("Reviewer accounts look organic (no coordinated network), so the text signal alone points to "
                         "an incentivized-review campaign rather than a fake-account ring; human judgement is needed.")
        return " ".join(parts)

    @staticmethod
    def _summary_table(findings: list[dict], score: AgentResult, decision: dict, explanation: str) -> dict:
        review_side = [f for f in findings if f["agent_key"] in ("statistical",)]
        reviewer_side = [f for f in findings if f["agent_key"] in ("network", "linguistic")]
        anomaly = (review_side or findings or [{"detail": "None detected"}])[0]["detail"]
        issue = (reviewer_side or findings[1:] or [{"detail": "—"}])[0]["detail"]
        return {
            "Anomaly Detected": anomaly,
            "Issue": issue,
            "Risk / Priority Level": f"{score.metrics['tier']} ({score.metrics['risk_score']:.0f}/100)",
            "Explanation": explanation,
            "Recommendation": "; ".join(decision["recommendations"][:3]),
        }
