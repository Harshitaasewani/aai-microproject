"""Agent 7 — Seller Risk Correlation Agent.

Correlates product-level anomalies with seller history: account age vs review volume, prior flags /
takedowns, and rapid relisting after a takedown. Runs AFTER the product detectors because it uses
their results ("young seller" alone is not suspicious; "young seller + review ring" is).
"""
from __future__ import annotations

import pandas as pd

from ..models import AgentResult, CaseData, Flag

NAME = "Seller Risk Correlation"


def run(case: CaseData, upstream: dict[str, "AgentResult"]) -> AgentResult:
    m = case.market
    s = case.seller
    age = max(1, case.summary["seller_account_age_days"])
    flags: list[Flag] = []

    # review volume across the whole seller catalog relative to account age
    seller_products = m.products[m.products.seller_id == s["seller_id"]].product_id
    seller_reviews = int(((m.reviews.product_id.isin(seller_products)) & (m.reviews.timestamp_utc <= case.as_of)).sum())
    per_day = seller_reviews / age
    baseline_day = upstream["statistical"].metrics.get("category_weekly_baseline", 15) / 7
    velocity_ratio = per_day / max(0.1, baseline_day)

    ev = case.seller_events
    recent = ev[ev.date >= case.as_of - pd.Timedelta(days=30)]
    n_flags = int((recent.event == "flag").sum())
    n_warn = int((recent.event == "warning").sum())
    takedowns = ev[ev.event == "takedown"]
    relists = ev[ev.event == "relist"]
    rapid_relist = []
    for _, t in takedowns.iterrows():
        r = relists[(relists.date >= t.date) & (relists.date <= t.date + pd.Timedelta(days=7))]
        rapid_relist += r.assign(date=r.date.dt.date.astype(str)).to_dict("records")

    if age <= 60 and velocity_ratio >= 3:
        flags.append(Flag(
            "young_seller_high_volume", "Seller age inconsistent with review volume",
            f"Account is {age} days old but has {seller_reviews} reviews across {len(seller_products)} listing(s) "
            f"({per_day:.1f}/day vs category ~{baseline_day:.1f}/day per listing)", "high"))
    if n_flags or n_warn:
        flags.append(Flag(
            "prior_flags", "Prior flags / warnings on file",
            f"{n_flags} flag(s) and {n_warn} warning(s) in the last 30 days", "high" if n_flags >= 2 else "medium",
            recent.assign(date=recent.date.dt.date.astype(str)).to_dict("records")))
    if rapid_relist:
        flags.append(Flag(
            "rapid_relisting", "Rapid relisting after takedown",
            f"{len(rapid_relist)} listing(s) re-created within 7 days of a takedown", "high", rapid_relist))

    # correlation with product anomalies found upstream
    product_signal = max(upstream[k].score for k in ("statistical", "linguistic", "network", "claims", "visual"))
    youth = 1.0 if age <= 30 else 0.6 if age <= 90 else 0.1
    history = min(1.0, 0.35 * n_flags + 0.2 * n_warn + 0.4 * bool(rapid_relist))
    velocity = min(1.0, max(0.0, (velocity_ratio - 1.5) / 6)) if age <= 90 else 0.0
    score = min(1.0, 0.4 * history + 0.3 * velocity + 0.3 * youth * product_signal)
    tier = "High" if score >= 0.6 else "Medium" if score >= 0.3 else "Low"
    metrics = {"seller_account_age_days": age, "seller_total_reviews": seller_reviews, "listings": int(len(seller_products)),
               "reviews_per_day": round(per_day, 2), "velocity_vs_category_x": round(velocity_ratio, 1),
               "flags_30d": n_flags, "warnings_30d": n_warn, "rapid_relists": len(rapid_relist),
               "seller_risk_tier": tier, "seller_region": s["region"]}
    return AgentResult(NAME, float(score), 0.85, flags, metrics,
                       f"Seller {s['name']} ({age}d old) — risk tier {tier}")
