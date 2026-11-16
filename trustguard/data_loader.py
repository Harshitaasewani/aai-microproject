"""Loads the marketplace tables once. In production these would be API/DB connectors
(review service, listing service, seller-risk DB); the agents only see this interface."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CONFIG_DIR = ROOT / "config"


@dataclass
class MarketData:
    sellers: pd.DataFrame
    products: pd.DataFrame
    reviewers: pd.DataFrame
    reviews: pd.DataFrame
    prices: pd.DataFrame
    listings: pd.DataFrame
    seller_events: pd.DataFrame
    certifications: pd.DataFrame
    brands: pd.DataFrame
    cases: pd.DataFrame
    as_of: pd.Timestamp
    image_dir: Path


def load_market(data_dir: Path = DATA_DIR) -> MarketData:
    r = lambda name: pd.read_csv(data_dir / name)  # noqa: E731
    reviews = r("reviews.csv")
    # Normalize mixed-offset timestamps to UTC (Ingestion Agent requirement)
    reviews["timestamp_utc"] = pd.to_datetime(reviews["timestamp"], utc=True, format="ISO8601")
    meta = json.loads((data_dir / "meta.json").read_text())
    return MarketData(
        sellers=r("sellers.csv"), products=r("products.csv"), reviewers=r("reviewers.csv"), reviews=reviews,
        prices=r("price_history.csv"), listings=r("marketplace_listings.csv"), seller_events=r("seller_events.csv"),
        certifications=r("certifications.csv"), brands=r("brand_reference.csv"), cases=r("case_history.csv"),
        as_of=pd.Timestamp(meta["as_of"]), image_dir=data_dir / "images",
    )


def load_config(name: str) -> dict:
    return json.loads((CONFIG_DIR / name).read_text())
