"""Agent 2 — Statistical Anomaly Detection Agent.

Looks for non-organic patterns in volume, timing and rating distribution, always relative to the
product's category baseline (computed from peer products, using a median so frauds don't inflate it).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon

from ..models import AgentResult, CaseData, Flag

NAME = "Statistical Anomaly"
WINDOW_H = 72


def _clip(x: float) -> float:
    return float(min(1.0, max(0.0, x)))


def _rating_dist(r: pd.Series) -> np.ndarray:
    c = r.value_counts().reindex([1, 2, 3, 4, 5], fill_value=0).to_numpy(float)
    return (c + 0.5) / (c + 0.5).sum()


def _hour_dist(ts: pd.Series) -> np.ndarray:
    c = ts.dt.hour.value_counts().reindex(range(24), fill_value=0).to_numpy(float)
    return (c + 0.5) / (c + 0.5).sum()


def category_baseline(case: CaseData) -> dict:
    m = case.market
    peers = m.products[(m.products.category == case.product["category"]) &
                       (m.products.product_id != case.product["product_id"])]
    rv = m.reviews[m.reviews.product_id.isin(peers.product_id) & (m.reviews.timestamp_utc <= case.as_of)]
    weekly = []
    for pid, g in rv.groupby("product_id"):
        listed = pd.Timestamp(peers.set_index("product_id").loc[pid, "listed_date"], tz="UTC")
        weeks = max(1.0, (case.as_of - listed).days / 7)
        weekly.append(len(g) / weeks)
    return {
        "peer_products": int(len(peers)),
        "weekly_reviews_median": float(np.median(weekly)) if weekly else 15.0,
        "rating_dist": _rating_dist(rv.rating) if len(rv) else _rating_dist(pd.Series([4, 5])),
        "five_star_share": float((rv.rating == 5).mean()) if len(rv) else 0.5,
        "hour_dist": _hour_dist(rv.timestamp_utc) if len(rv) else np.ones(24) / 24,
    }


def max_window(ts: pd.Series, hours: int = WINDOW_H) -> tuple[int, pd.Timestamp | None, pd.Timestamp | None]:
    if ts.empty:
        return 0, None, None
    t = np.sort(ts.values.astype("datetime64[ns]"))
    end_idx = np.searchsorted(t, t + np.timedelta64(hours, "h"), side="right")
    counts = end_idx - np.arange(len(t))
    i = int(counts.argmax())
    return int(counts[i]), pd.Timestamp(t[i], tz="UTC"), pd.Timestamp(t[end_idx[i] - 1], tz="UTC")


def run(case: CaseData) -> AgentResult:
    rv = case.reviews
    n = len(rv)
    base = category_baseline(case)
    flags: list[Flag] = []
    if n < 5:
        return AgentResult(NAME, 0.0, 0.1, [], {"reviews": n}, "Too few reviews for statistical analysis.")

    # 1) Volume spike: busiest 72h window vs what the category normally gets in 72h
    win_count, win_start, win_end = max_window(rv.timestamp_utc)
    expected = max(1.0, base["weekly_reviews_median"] * WINDOW_H / 168)
    ratio = win_count / expected
    in_win = rv[(rv.timestamp_utc >= win_start) & (rv.timestamp_utc <= win_end)]
    five_in_win = int((in_win.rating == 5).sum())
    weekly_ratio = win_count / max(1.0, base["weekly_reviews_median"])
    volume_s = _clip((np.log(ratio) - np.log(3)) / (np.log(15) - np.log(3))) if ratio > 0 else 0.0
    if ratio >= 3:
        flags.append(Flag(
            "volume_spike", "Review volume spike",
            f"{win_count} reviews ({five_in_win} five-star) in a 72-hour window "
            f"({win_start:%d %b %H:%M}–{win_end:%d %b %H:%M} UTC) vs category baseline of "
            f"{base['weekly_reviews_median']:.0f}/week — {weekly_ratio:.0f}x the weekly baseline, "
            f"{ratio:.0f}x the expected 72h volume",
            "critical" if ratio >= 15 else "high" if ratio >= 6 else "medium",
            in_win.review_id.tolist()))

    # 2) Rating skew: 5-star share and divergence from the category's rating distribution
    five_share = float((rv.rating == 5).mean())
    jsd_rating = float(jensenshannon(_rating_dist(rv.rating), base["rating_dist"]) ** 2)
    skew_s = _clip((five_share - base["five_star_share"] - 0.1) / 0.3)
    if skew_s > 0.3:
        flags.append(Flag(
            "rating_skew", "Unnatural 5-star clustering",
            f"{five_share:.0%} of ratings are 5★ vs {base['five_star_share']:.0%} in category "
            f"(JS divergence {jsd_rating:.2f})", "high" if skew_s > 0.7 else "medium"))

    # 3) Timing: burst share and hour-of-day pattern vs category traffic
    burst_share = win_count / n
    jsd_hour = float(jensenshannon(_hour_dist(rv.timestamp_utc), base["hour_dist"]) ** 2)
    timing_s = _clip(0.6 * _clip((burst_share - 0.15) / 0.4) + 0.4 * _clip((jsd_hour - 0.03) / 0.15))
    if timing_s > 0.4:
        flags.append(Flag(
            "timing_cluster", "Timing inconsistent with organic traffic",
            f"{burst_share:.0%} of all reviews landed in one 72h window; hour-of-day pattern diverges from "
            f"category traffic (JS {jsd_hour:.2f})", "high" if timing_s > 0.7 else "medium"))

    # 4) Price manipulation around the burst (deep discount for reviews, then price restored)
    ph = case.price_history
    price_s = 0.0
    if len(ph) >= 3 and win_start is not None:
        med = float(ph.price_inr.median())
        near = ph[(ph.date >= win_start.normalize() - pd.Timedelta(days=3)) & (ph.date <= win_end + pd.Timedelta(days=1))]
        if len(near) and float(near.price_inr.min()) <= 0.6 * med and volume_s > 0.3:
            drop = 1 - float(near.price_inr.min()) / med
            price_s = _clip(drop)
            flags.append(Flag(
                "price_drop_during_burst", "Price cut coinciding with review burst",
                f"Price fell {drop:.0%} (₹{med:.0f} → ₹{near.price_inr.min():.0f}) during the review spike, then was restored",
                "medium", near.assign(date=near.date.dt.date.astype(str))[["date", "price_inr"]].to_dict("records")))

    parts = [volume_s, skew_s, timing_s, price_s]
    score = 0.6 * max(parts) + 0.4 * float(np.mean(parts))
    confidence = _clip(0.3 + n / 100) * (1.0 if base["peer_products"] >= 2 else 0.6)
    metrics = {
        "reviews": n, "max_72h_count": win_count, "five_star_in_window": five_in_win,
        "category_weekly_baseline": round(base["weekly_reviews_median"], 1),
        "spike_vs_weekly_baseline_x": round(weekly_ratio, 1), "spike_vs_expected_72h_x": round(ratio, 1),
        "five_star_share": round(five_share, 3), "category_five_star_share": round(base["five_star_share"], 3),
        "rating_js_divergence": round(jsd_rating, 3), "hour_js_divergence": round(jsd_hour, 3),
        "burst_share": round(burst_share, 3),
        "window_start_utc": win_start.isoformat() if win_start is not None else None,
        "window_end_utc": win_end.isoformat() if win_end is not None else None,
        "sub_scores": {"volume": round(volume_s, 2), "rating_skew": round(skew_s, 2),
                       "timing": round(timing_s, 2), "price": round(price_s, 2)},
    }
    summary = (f"Peak {win_count} reviews/72h vs baseline {base['weekly_reviews_median']:.0f}/week; "
               f"{five_share:.0%} five-star.")
    return AgentResult(NAME, _clip(score), confidence, flags, metrics, summary)
