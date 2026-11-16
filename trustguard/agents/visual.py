"""Agent 6 — Visual Counterfeit Signal Agent.

Uses perceptual hashing to find (a) listing photos reused by unrelated sellers (non-original imagery)
and (b) listing photos that match protected brand reference imagery. Logo / stitching inconsistency
checks need close-up reference shots; the MVP reports them as "not assessed" rather than guessing.
Upgrade path: CLIP embeddings for brand-logo similarity and a fine-tuned detector for stitching defects.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from ..imaging import dhash, hamming
from ..models import AgentResult, CaseData, Flag

NAME = "Visual Counterfeit Signal"
REUSE_MAX_DIST = 24
BRAND_MAX_DIST = 28


@lru_cache(maxsize=4096)
def _hash(path: str) -> int:
    return dhash(path)


def run(case: CaseData) -> AgentResult:
    m = case.market
    img_dir: Path = m.image_dir
    own = img_dir / case.product["image_file"]
    if not own.exists():
        return AgentResult(NAME, 0.0, 0.1, [], {}, "No listing image available.")
    h = _hash(str(own))
    flags: list[Flag] = []

    # (a) reuse across unrelated listings (marketplace image index + other products' photos)
    matches = []
    window_start = (case.as_of - pd.Timedelta(days=60)).date().isoformat()
    for _, l in m.listings.iterrows():
        if l.seller_id == case.seller["seller_id"] or l.listed_date < window_start:
            continue
        d = hamming(h, _hash(str(img_dir / l.image_file)))
        if d <= REUSE_MAX_DIST:
            matches.append({"listing_id": l.listing_id, "seller_id": l.seller_id, "seller_name": l.seller_name,
                            "image": l.image_file, "hamming_distance": d, "listed_date": l.listed_date})
    for _, p in m.products.iterrows():
        if p.seller_id == case.seller["seller_id"]:
            continue
        d = hamming(h, _hash(str(img_dir / p.image_file)))
        if d <= REUSE_MAX_DIST:
            matches.append({"listing_id": p.product_id, "seller_id": p.seller_id, "seller_name": p.seller_id,
                            "image": p.image_file, "hamming_distance": d, "listed_date": p.listed_date})
    sellers = {x["seller_id"] for x in matches}
    if matches:
        flags.append(Flag(
            "reused_image", "Non-original product imagery",
            f"Listing image matches photos used by {len(sellers)} unrelated seller(s) in the past 60 days "
            f"(perceptual-hash distance ≤ {REUSE_MAX_DIST}/256)",
            "high" if len(sellers) >= 3 else "medium", matches))

    # (b) brand reference imagery
    brand_matches = []
    for _, b in m.brands.iterrows():
        d = hamming(h, _hash(str(img_dir / b.reference_image)))
        if d <= BRAND_MAX_DIST:
            authorized = case.seller["seller_id"] in str(b.authorized_sellers).split(";")
            brand_matches.append({"brand": b.brand, "reference_image": b.reference_image,
                                  "hamming_distance": d, "authorized_seller": authorized})
            if not authorized:
                flags.append(Flag(
                    "brand_image_match", "Brand imagery on unauthorized listing",
                    f"Listing image matches {b.brand} reference imagery (distance {d}/256) but seller is not an "
                    f"authorized {b.brand} reseller — possible counterfeit / IP infringement",
                    "critical", [{"listing_image": case.product['image_file'], "reference": b.reference_image,
                                  "hamming_distance": d}]))

    reuse_s = min(1.0, len(sellers) / 4)
    brand_s = 1.0 if any(not b["authorized_seller"] for b in brand_matches) else 0.0
    score = max(reuse_s * 0.85, brand_s)
    metrics = {"image_hash": f"{h:064x}", "reuse_matches": len(matches), "unrelated_sellers_reusing": len(sellers),
               "brand_matches": brand_matches,
               "logo_stitching_check": "not assessed — no close-up brand reference images on file"}
    summ = (f"Image reused by {len(sellers)} unrelated sellers" if sellers else "Image appears original") + (
        f"; matches {brand_matches[0]['brand']} reference" if brand_matches else "")
    return AgentResult(NAME, float(score), 0.75, flags, metrics, summ)
