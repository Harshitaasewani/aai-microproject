"""Agent 1 — Review & Metadata Ingestion Agent.

Pulls reviews, reviewer metadata, listing, pricing and seller history for one product, normalizes
timestamps to UTC, and produces an analysis-ready CaseData plus a summary such as
{reviews: 512, verified_purchase_rate: 0.34, reviewer_account_age_avg_days: 19}.
"""
from __future__ import annotations

import pandas as pd

from ..data_loader import MarketData
from ..models import CaseData

NAME = "Review & Metadata Ingestion"


def run(market: MarketData, product_id: str, as_of: pd.Timestamp | None = None) -> CaseData:
    as_of = as_of or market.as_of
    prod_rows = market.products[market.products.product_id == product_id]
    if prod_rows.empty:
        raise ValueError(f"Unknown product_id {product_id}")
    product = prod_rows.iloc[0].to_dict()
    seller = market.sellers[market.sellers.seller_id == product["seller_id"]].iloc[0].to_dict()

    rv = market.reviews[(market.reviews.product_id == product_id) & (market.reviews.timestamp_utc <= as_of)].copy()
    rv = rv.merge(market.reviewers, on="reviewer_id", how="left")
    quality = []
    missing_meta = int(rv["account_created"].isna().sum())
    if missing_meta:
        quality.append(f"{missing_meta} reviews have no reviewer metadata")
    dupes = int(rv.duplicated(["reviewer_id"]).sum())
    if dupes:
        quality.append(f"{dupes} repeat reviews from the same reviewer")
    rv["account_created"] = pd.to_datetime(rv["account_created"], utc=True)
    rv["account_age_at_review_days"] = (rv["timestamp_utc"] - rv["account_created"]).dt.total_seconds() / 86400
    rv = rv.sort_values("timestamp_utc").reset_index(drop=True)

    prices = market.prices[market.prices.product_id == product_id].copy()
    prices["date"] = pd.to_datetime(prices["date"], utc=True)
    prices = prices[prices.date <= as_of].sort_values("date")

    events = market.seller_events[market.seller_events.seller_id == product["seller_id"]].copy()
    events["date"] = pd.to_datetime(events["date"], utc=True)
    events = events[events.date <= as_of]

    certs = market.certifications[market.certifications.product_id == product_id]

    seller_age = (as_of - pd.Timestamp(seller["account_created"], tz="UTC")).days
    summary = {
        "product_id": product_id,
        "title": product["title"],
        "category": product["category"],
        "seller_id": seller["seller_id"],
        "seller_name": seller["name"],
        "seller_region": seller["region"],
        "seller_account_age_days": int(seller_age),
        "reviews": int(len(rv)),
        "avg_rating": round(float(rv.rating.mean()), 2) if len(rv) else None,
        "verified_purchase_rate": round(float(rv.verified_purchase.mean()), 2) if len(rv) else None,
        "reviewer_account_age_avg_days": round(float(rv.account_age_at_review_days.mean()), 1) if len(rv) else None,
        "reviewer_account_age_median_days": round(float(rv.account_age_at_review_days.median()), 1) if len(rv) else None,
        "reviewer_categories_avg": round(float(rv.categories_purchased.mean()), 2) if len(rv) else None,
        "first_review_utc": rv.timestamp_utc.min().isoformat() if len(rv) else None,
        "last_review_utc": rv.timestamp_utc.max().isoformat() if len(rv) else None,
        "current_price_inr": int(prices.price_inr.iloc[-1]) if len(prices) else int(product["price_inr"]),
    }
    return CaseData(product=product, seller=seller, reviews=rv, price_history=prices, seller_events=events,
                    certifications=certs, market=market, as_of=as_of, summary=summary, data_quality=quality)
