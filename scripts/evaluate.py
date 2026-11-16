"""Evaluation against the planted ground truth.

Product level: does the system escalate (High/Critical or needs_manual_review) the planted fraud,
counterfeit and suspicious products, and leave clean products alone?
Review level: precision / recall of the reviews the agents flag (linguistic flags or ring membership)
against the reviews we planted as fake (ring + incentivized).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from trustguard.orchestrator import Orchestrator  # noqa: E402


def main():
    orch = Orchestrator()
    gt = json.loads((ROOT / "data" / "ground_truth_products.json").read_text())
    labels = pd.read_csv(ROOT / "data" / "ground_truth_reviews.csv").set_index("review_id").label
    rows = []
    tp = fp = fn = tn = 0
    r_tp = r_fp = r_fn = 0
    for pid, truth in gt.items():
        r = orch.run(pid, use_llm=False)
        flagged = r["tier"] in ("High", "Critical") or r["decision"]["status"] == "needs_manual_review"
        bad = truth != "clean"
        tp += flagged and bad
        fp += flagged and not bad
        fn += (not flagged) and bad
        tn += (not flagged) and not bad
        rows.append({"product": pid, "truth": truth, "score": r["risk_score"], "tier": r["tier"],
                     "status": r["decision"]["status"], "escalated": flagged, "correct": flagged == bad})
        # review level
        rv = orch.market.reviews[orch.market.reviews.product_id == pid]
        ring = r["agents"]["network"]["metrics"].get("ring_assignment", {})
        pred = set(r["agents"]["linguistic"]["metrics"].get("flagged_review_ids", [])) | set(
            rv[rv.reviewer_id.isin(ring)].review_id)
        actual = set(rv.review_id[rv.review_id.map(labels) != "genuine"])
        r_tp += len(pred & actual)
        r_fp += len(pred - actual)
        r_fn += len(actual - pred)
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    print(f"\nProduct level: {tp} TP, {fp} FP, {fn} FN, {tn} TN  ->  "
          f"precision {tp / max(1, tp + fp):.2f}, recall {tp / max(1, tp + fn):.2f}, accuracy {(tp + tn) / len(df):.2f}")
    print(f"Review level:  precision {r_tp / max(1, r_tp + r_fp):.3f}, recall {r_tp / max(1, r_tp + r_fn):.3f} "
          f"({r_tp} true flags, {r_fp} false flags, {r_fn} missed)")


if __name__ == "__main__":
    main()
