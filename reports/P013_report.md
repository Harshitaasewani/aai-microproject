# Trust & Compliance Report — Velora Canvas Belt

**Case:** CASE-P013-20261020 · **Region:** IN · **As of:** 2026-10-20T12:00 UTC  
**Seller:** Velora Accessories (S002, account 35 days old)  
**Reviews:** 162 · **Avg rating:** 4.69★ · **Verified-purchase rate:** 0.51 · **Median reviewer account age at review:** 23.2 days

## Risk score: 70/100 — High
**Decision status:** `escalate` · **Routed to:** Trust & Safety — Seller Audit  
**Enforcement:** None taken automatically — all actions require human approval

## Summary

| Field | Value |
|---|---|
| Anomaly Detected | 68 reviews (64 five-star) in a 72-hour window (12 Oct 18:42–15 Oct 18:28 UTC) vs category baseline of 19/week — 4x the weekly baseline, 8x the expected 72h volume |
| Issue | 100 reviews (62%) from different accounts fall into 8 templated clusters; largest has 15 reviews. 27 reviews share the phrase pattern "fast delivery highly recommend this seller" |
| Risk / Priority Level | High (70/100) |
| Explanation | Evidence is consistent with near-duplicate review text across accounts, coordinated reviewer network, review volume spike, generic superlatives without product detail. Material/origin/certification claims in the listing have no supporting documents on file. |
| Recommendation | Escalate to compliance for seller audit (coordinated review activity); Suppress rating badge pending investigation; Hold suspected reviews (~62% of total) out of the star rating pending human review |

## Agent scores

| Agent | Risk signal (0-1) | Confidence | Summary |
|---|---|---|---|
| Statistical Anomaly | 0.52 | 1.00 | Peak 68 reviews/72h vs baseline 19/week; 85% five-star. |
| Linguistic Pattern | 0.89 | 1.00 | Linguistic authenticity score 0.11/1.0 |
| Reviewer Network | 1.00 | 1.00 | 100 of 162 reviewers in coordinated clusters; linked sellers: ['S001'] |
| Product Claim Verification | 0.35 | 0.80 | 1 claims extracted, 1 unverified |
| Visual Counterfeit Signal | 0.00 | 0.75 | Image appears original |
| Seller Risk Correlation | 0.33 | 0.85 | Seller Velora Accessories (35d old) — risk tier Medium |

## Findings (audit trail)

| ID | Severity | Finding | Policy clause | Regulatory reference | Evidence |
|---|---|---|---|---|---|
| F-001 | critical | **Near-duplicate review text across accounts** — 100 reviews (62%) from different accounts fall into 8 templated clusters; largest has 15 reviews. 27 reviews share the phrase pattern "fast delivery highly recommend this seller" | Policy 3.4: Inauthentic Review Content | Consumer Protection Act, 2019 (unfair trade practices); BIS IS 19000:2022 online consumer reviews standard | 5 item(s), sha256 `ffbb9fdaa63f…` |
| F-002 | critical | **Coordinated reviewer network** — 100 reviewer accounts in 1 cluster share devices or IP ranges with accounts created within 5 days of each other (largest cluster 100; 28 devices, 5 IP ranges) | Policy 3.2: Coordinated / Fake Reviewer Accounts | Consumer Protection Act, 2019 (unfair trade practices); BIS IS 19000:2022 online consumer reviews standard | 1 item(s), sha256 `1033297438d7…` |
| F-003 | high | **Review volume spike** — 68 reviews (64 five-star) in a 72-hour window (12 Oct 18:42–15 Oct 18:28 UTC) vs category baseline of 19/week — 4x the weekly baseline, 8x the expected 72h volume | Policy 3.1: Review Manipulation | Consumer Protection Act, 2019 (unfair trade practices); BIS IS 19000:2022 online consumer reviews standard | 68 item(s), sha256 `931dff77a8e0…` |
| F-004 | high | **Generic superlatives without product detail** — 62% of reviews use generic praise and mention no product-specific detail (e.g. strap, zipper, stitching for this category) | Policy 3.4: Inauthentic Review Content | Consumer Protection Act, 2019 (unfair trade practices); BIS IS 19000:2022 online consumer reviews standard | 100 item(s), sha256 `26b09925486f…` |
| F-005 | high | **Accounts created in the same window** — 100 reviewer accounts (62%) were created within the same 5-day window starting 21 Sep 2026 | Policy 3.2: Coordinated / Fake Reviewer Accounts | Consumer Protection Act, 2019 (unfair trade practices); BIS IS 19000:2022 online consumer reviews standard | 0 item(s), sha256 `4f53cda18c2b…` |
| F-006 | high | **Reviewers exclusive to this seller network** — 10 reviewers (6%) have only ever reviewed this seller's catalog; 62% review only this seller and linked seller(s) S001 — reciprocal review pattern | Policy 3.2: Coordinated / Fake Reviewer Accounts | Consumer Protection Act, 2019 (unfair trade practices); BIS IS 19000:2022 online consumer reviews standard | 10 item(s), sha256 `dc8f64fc8d64…` |
| F-007 | medium | **Unnatural 5-star clustering** — 85% of ratings are 5★ vs 64% in category (JS divergence 0.04) | Policy 3.1: Review Manipulation | Consumer Protection Act, 2019 (unfair trade practices); BIS IS 19000:2022 online consumer reviews standard | 0 item(s), sha256 `4f53cda18c2b…` |
| F-008 | medium | **Timing inconsistent with organic traffic** — 42% of all reviews landed in one 72h window; hour-of-day pattern diverges from category traffic (JS 0.02) | Policy 3.1: Review Manipulation | Consumer Protection Act, 2019 (unfair trade practices); BIS IS 19000:2022 online consumer reviews standard | 0 item(s), sha256 `4f53cda18c2b…` |
| F-009 | medium | **Low reviewer order-history diversity** — 62% of reviewers are single-category purchasers with ≤3 lifetime orders | Policy 3.2: Coordinated / Fake Reviewer Accounts | Consumer Protection Act, 2019 (unfair trade practices); BIS IS 19000:2022 online consumer reviews standard | 0 item(s), sha256 `4f53cda18c2b…` |
| F-010 | medium | **Prior flags / warnings on file** — 1 flag(s) and 0 warning(s) in the last 30 days | Policy 7.2: Seller Integrity / Repeat Offender | — | 1 item(s), sha256 `aaee83ee55e6…` |
| F-011 | medium | **Unverified material claim** — Listing claims "pure cotton" but no supplier/certification document is on file | Policy 4.2: Deceptive Product Description | Consumer Protection Act, 2019 (misleading advertisement); Consumer Protection (E-Commerce) Rules, 2020 | 1 item(s), sha256 `ae0c20c6e9df…` |

## Recommended actions (for human approval)

- Escalate to compliance for seller audit (coordinated review activity)
- Suppress rating badge pending investigation
- Hold suspected reviews (~62% of total) out of the star rating pending human review
- Request supporting documents for: "pure cotton"

## Historical precedent

100% of the 25 most similar past cases were confirmed review fraud.

Outcome mix: confirmed review fraud 100%

---
*Generated by TrustGuard (PS-13 prototype). This report is a detection and evidence layer; it is not an enforcement decision.*