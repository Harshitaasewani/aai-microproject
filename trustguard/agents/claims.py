"""Agent 5 — Product Claim Verification Agent.

Extracts material / certification / origin / authenticity claims from the listing and checks each
against documents on file and brand reference data. Rule-based extraction keeps it deterministic and
auditable; an LLM extractor can be plugged in for free-form listings (see trustguard/llm.py).
"""
from __future__ import annotations

import re

from ..models import AgentResult, CaseData, Flag

NAME = "Product Claim Verification"

# claim_key -> (regex, claim type, severity if unverified)
CLAIMS = {
    "genuine leather": (r"genuine leather|real leather|pure leather", "material", "high"),
    "100% cotton": (r"100% cotton|pure cotton", "material", "medium"),
    "made in italy": (r"(made|handcrafted|crafted) in italy", "origin", "high"),
    "made in india": (r"made in india", "origin", "low"),
    "bis certified": (r"bis certified", "safety certification", "critical"),
    "dermatologically tested": (r"dermatologically tested", "safety/health claim", "high"),
}


def run(case: CaseData) -> AgentResult:
    p = case.product
    text = f"{p['title']}. {p['description']}".lower()
    on_file = set(case.certifications.claim_key.str.lower()) if len(case.certifications) else set()
    flags: list[Flag] = []
    found = []
    for key, (rx, ctype, sev) in CLAIMS.items():
        m = re.search(rx, text)
        if not m:
            continue
        verified = key in on_file
        doc = case.certifications[case.certifications.claim_key == key].doc_ref.tolist()
        found.append({"claim": m.group(0), "claim_key": key, "type": ctype, "verified": verified, "documents": doc})
        if not verified:
            flags.append(Flag(
                "unverified_claim", f"Unverified {ctype} claim",
                f"Listing claims \"{m.group(0)}\" but no supplier/certification document is on file",
                sev, [{"listing_text": m.group(0), "documents_on_file": []}]))

    # Brand authenticity: brand named in listing, seller not an authorized reseller, implausible price
    brand_hits = []
    for _, b in case.market.brands.iterrows():
        if b.brand.lower() in text:
            authorized = case.seller["seller_id"] in str(b.authorized_sellers).split(";")
            price = case.summary.get("current_price_inr") or p["price_inr"]
            ratio = price / b.msrp_inr
            brand_hits.append({"brand": b.brand, "authorized_seller": authorized, "price_inr": price,
                               "brand_msrp_inr": int(b.msrp_inr), "price_to_msrp": round(ratio, 3)})
            claims_authentic = bool(re.search(r"authentic|original|genuine " + b.brand.lower(), text))
            if not authorized:
                flags.append(Flag(
                    "unauthorized_brand", "Branded listing from unauthorized seller",
                    f"Listing uses brand \"{b.brand}\"{' and claims authenticity' if claims_authentic else ''}; "
                    f"seller {case.seller['seller_id']} is not an authorized {b.brand} reseller",
                    "critical", [{"brand": b.brand, "authorized_sellers": b.authorized_sellers}]))
            if ratio < 0.3:
                flags.append(Flag(
                    "implausible_price", "Price implausible for claimed brand",
                    f"Listed at ₹{price:,} — {ratio:.0%} of {b.brand} MSRP ₹{int(b.msrp_inr):,}", "high"))

    sev_w = {"low": 0.15, "medium": 0.35, "high": 0.6, "critical": 0.9}
    score = 0.0
    for f in flags:  # probabilistic OR: several unverified claims compound
        score = 1 - (1 - score) * (1 - sev_w[f.severity])
    conf = 0.8 if found or brand_hits else 0.5
    metrics = {"claims_found": found, "brand_checks": brand_hits,
               "unverified": sum(1 for c in found if not c["verified"])}
    summ = f"{len(found)} claims extracted, {metrics['unverified']} unverified" + (
        f"; brand check: {brand_hits[0]['brand']}" if brand_hits else "")
    return AgentResult(NAME, float(score), conf, flags, metrics, summ)
