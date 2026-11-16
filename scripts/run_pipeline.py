"""CLI: run the multi-agent pipeline on one or all products and write reports.

    python scripts/run_pipeline.py P001             # one product, prints the summary table
    python scripts/run_pipeline.py --all            # all products -> reports/
    python scripts/run_pipeline.py P001 --region EU # region-aware thresholds
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trustguard import report  # noqa: E402
from trustguard.orchestrator import Orchestrator  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("product_id", nargs="?", default="P001")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--region", choices=["IN", "EU", "US"])
    ap.add_argument("--evidence", action="store_true", help="also write the evidence package zip")
    a = ap.parse_args()

    orch = Orchestrator()
    ids = orch.market.products.product_id.tolist() if a.all else [a.product_id]
    out = ROOT / "reports"
    for pid in ids:
        r = orch.run(pid, region=a.region)
        j, m = report.save(r, out)
        if a.evidence:
            (out / f"{r['case_id']}_evidence.zip").write_bytes(report.evidence_package(r, orch.market))
        print(f"{pid:5s} {r['product']['title'][:30]:30s} {r['risk_score']:5.1f}/100  {r['tier']:8s} "
              f"{r['decision']['status']:20s} -> {r['decision']['queue']}")
        if not a.all:
            print()
            for k, v in r["summary_table"].items():
                print(f"  {k:22s} {v}")
            print(f"\n  Report: {m}")


if __name__ == "__main__":
    main()
