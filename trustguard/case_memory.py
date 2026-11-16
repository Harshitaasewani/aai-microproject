"""Historical Case Memory (advanced feature 3).

Finds the k most similar past cases by their agent-score vector and reports how they were resolved,
e.g. "82% of similar cases were confirmed review fraud". Production version: a vector DB of case
embeddings (scores + text summary) instead of a CSV.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

COLS = ["statistical", "linguistic", "network", "claims", "visual", "seller"]
LABELS = {"confirmed_review_fraud": "confirmed review fraud", "confirmed_counterfeit": "confirmed counterfeit",
          "confirmed_incentivized": "confirmed incentivized-review violations", "cleared": "cleared"}


def similar_cases(cases: pd.DataFrame, scores: dict[str, float], k: int = 25) -> dict:
    X = cases[COLS].to_numpy(float)
    q = np.array([scores[c] for c in COLS])
    d = np.linalg.norm(X - q, axis=1)
    idx = np.argsort(d)[:k]
    near = cases.iloc[idx].assign(distance=d[idx])
    dist = near.outcome.value_counts(normalize=True)
    top, share = dist.index[0], float(dist.iloc[0])
    return {
        "k": k, "outcome_distribution": {LABELS.get(o, o): round(float(p), 2) for o, p in dist.items()},
        "headline": f"{share:.0%} of the {k} most similar past cases were {LABELS.get(top, top)}",
        "nearest": near.head(5)[["case_id", "category", "outcome", "closed_on", "distance"]]
        .round({"distance": 3}).to_dict("records"),
    }
