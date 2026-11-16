"""Before/After Trust Score Timeline (advanced feature 6).

Re-runs the pipeline "as of" successive dates, so you can see exactly when the score jumped relative
to a review spike or seller change. Claims/visual results are cached by the orchestrator, so each
step only recomputes review-dependent agents — the same incremental re-scoring used for live updates.
"""
from __future__ import annotations

import pandas as pd

from .orchestrator import Orchestrator


def score_timeline(orch: Orchestrator, product_id: str, points: int = 14, region: str | None = None) -> pd.DataFrame:
    m = orch.market
    listed = pd.Timestamp(m.products.set_index("product_id").loc[product_id, "listed_date"], tz="UTC")
    start = listed + pd.Timedelta(days=2)
    dates = pd.date_range(start, m.as_of, periods=points)
    rows = []
    for d in dates:
        r = orch.run(product_id, region=region, as_of=d, use_llm=False)
        rows.append({"as_of": d, "risk_score": r["risk_score"], "tier": r["tier"], "reviews": r["product"]["reviews"],
                     **{f"{k}": v for k, v in r["scoring"]["agent_scores"].items()}})
    return pd.DataFrame(rows)
