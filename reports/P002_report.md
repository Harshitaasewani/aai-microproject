# Trust & Compliance Report — Aria Mini Tote

**Case:** CASE-P002-20261020 · **Region:** IN · **As of:** 2026-10-20T12:00 UTC  
**Seller:** Aria Leather House (S001, account 21 days old)  
**Reviews:** 133 · **Avg rating:** 4.83★ · **Verified-purchase rate:** 0.38 · **Median reviewer account age at review:** 21.0 days

## Risk score: 84/100 — Critical
**Decision status:** `escalate` · **Routed to:** Trust & Safety — Seller Audit  
**Enforcement:** None taken automatically — all actions require human approval

## Summary

| Field | Value |
|---|---|
| Anomaly Detected | 84 reviews (82 five-star) in a 72-hour window (12 Oct 13:30–15 Oct 09:38 UTC) vs category baseline of 19/week — 4x the weekly baseline, 10x the expected 72h volume |
| Issue | 100 reviews (75%) from different accounts fall into 8 templated clusters; largest has 20 reviews. 24 reviews share the phrase pattern "exceeded my expectations will buy again" |
| Risk / Priority Level | Critical (84/100) |
| Explanation | Evidence is consistent with near-duplicate review text across accounts, coordinated reviewer network, review volume spike, generic superlatives without product detail. The review burst is driven by a coordinated cluster of new, single-category accounts, matching a known incentivized review-ring signature. Seller account age (21 days) is inconsistent with its review volume and the seller has recent flags on file. Material/origin/certification claims in the listing have no supporting documents on file. |
| Recommendation | Escalate to compliance for seller audit (coordinated review activity); Suppress rating badge pending investigation; Hold suspected reviews (~75% of total) out of the star rating pending human review |

## Agent scores

| Agent | Risk signal (0-1) | Confidence | Summary |
|---|---|---|---|
| Statistical Anomaly | 0.73 | 1.00 | Peak 84 reviews/72h vs baseline 19/week; 92% five-star. |
| Linguistic Pattern | 0.89 | 1.00 | Linguistic authenticity score 0.11/1.0 |
| Reviewer Network | 1.00 | 1.00 | 100 of 133 reviewers in coordinated clusters; linked sellers: none |
| Product Claim Verification | 0.60 | 0.80 | 1 claims extracted, 1 unverified |
| Visual Counterfeit Signal | 0.00 | 0.75 | Image appears original |
| Seller Risk Correlation | 1.00 | 0.85 | Seller Aria Leather House (21d old) — risk tier High |

## Findings (audit trail)

| ID | Severity | Finding | Policy clause | Regulatory reference | Evidence |
|---|---|---|---|---|---|
| F-001 | critical | **Near-duplicate review text across accounts** — 100 reviews (75%) from different accounts fall into 8 templated clusters; largest has 20 reviews. 24 reviews share the phrase pattern "exceeded my expectations will buy again" | Policy 3.4: Inauthentic Review Content | Consumer Protection Act, 2019 (unfair trade practices); BIS IS 19000:2022 online consumer reviews standard | 5 item(s), sha256 `3801a358705c…` |
| F-002 | critical | **Coordinated reviewer network** — 100 reviewer accounts in 1 cluster share devices or IP ranges with accounts created within 5 days of each other (largest cluster 100; 27 devices, 5 IP ranges) | Policy 3.2: Coordinated / Fake Reviewer Accounts | Consumer Protection Act, 2019 (unfair trade practices); BIS IS 19000:2022 online consumer reviews standard | 1 item(s), sha256 `65cf2aa842d6…` |
| F-003 | high | **Review volume spike** — 84 reviews (82 five-star) in a 72-hour window (12 Oct 13:30–15 Oct 09:38 UTC) vs category baseline of 19/week — 4x the weekly baseline, 10x the expected 72h volume | Policy 3.1: Review Manipulation | Consumer Protection Act, 2019 (unfair trade practices); BIS IS 19000:2022 online consumer reviews standard | 84 item(s), sha256 `e72143aaff07…` |
| F-004 | high | **Generic superlatives without product detail** — 75% of reviews use generic praise and mention no product-specific detail (e.g. strap, zipper, stitching for this category) | Policy 3.4: Inauthentic Review Content | Consumer Protection Act, 2019 (unfair trade practices); BIS IS 19000:2022 online consumer reviews standard | 100 item(s), sha256 `e98b91fb04a7…` |
| F-005 | high | **Accounts created in the same window** — 100 reviewer accounts (75%) were created within the same 5-day window starting 21 Sep 2026 | Policy 3.2: Coordinated / Fake Reviewer Accounts | Consumer Protection Act, 2019 (unfair trade practices); BIS IS 19000:2022 online consumer reviews standard | 0 item(s), sha256 `4f53cda18c2b…` |
| F-006 | high | **Reviewers exclusive to this seller network** — 100 reviewers (75%) have only ever reviewed this seller's catalog | Policy 3.2: Coordinated / Fake Reviewer Accounts | Consumer Protection Act, 2019 (unfair trade practices); BIS IS 19000:2022 online consumer reviews standard | 60 item(s), sha256 `3f2d52b32f46…` |
| F-007 | high | **Seller age inconsistent with review volume** — Account is 21 days old but has 645 reviews across 2 listing(s) (30.7/day vs category ~2.8/day per listing) | Policy 7.2: Seller Integrity / Repeat Offender | — | 0 item(s), sha256 `4f53cda18c2b…` |
| F-008 | high | **Prior flags / warnings on file** — 2 flag(s) and 0 warning(s) in the last 30 days | Policy 7.2: Seller Integrity / Repeat Offender | — | 4 item(s), sha256 `fac94536eb71…` |
| F-009 | high | **Rapid relisting after takedown** — 1 listing(s) re-created within 7 days of a takedown | Policy 7.2: Seller Integrity / Repeat Offender | — | 1 item(s), sha256 `c3af5c3996cb…` |
| F-010 | high | **Unverified material claim** — Listing claims "genuine leather" but no supplier/certification document is on file | Policy 4.2: Deceptive Product Description | Consumer Protection Act, 2019 (misleading advertisement); Consumer Protection (E-Commerce) Rules, 2020 | 1 item(s), sha256 `5623078f98b9…` |
| F-011 | medium | **Unnatural 5-star clustering** — 92% of ratings are 5★ vs 63% in category (JS divergence 0.06) | Policy 3.1: Review Manipulation | Consumer Protection Act, 2019 (unfair trade practices); BIS IS 19000:2022 online consumer reviews standard | 0 item(s), sha256 `4f53cda18c2b…` |
| F-012 | medium | **Timing inconsistent with organic traffic** — 63% of all reviews landed in one 72h window; hour-of-day pattern diverges from category traffic (JS 0.03) | Policy 3.1: Review Manipulation | Consumer Protection Act, 2019 (unfair trade practices); BIS IS 19000:2022 online consumer reviews standard | 0 item(s), sha256 `4f53cda18c2b…` |
| F-013 | medium | **Price cut coinciding with review burst** — Price fell 73% (₹2924 → ₹799) during the review spike, then was restored | Policy 6.1: Pricing Manipulation | Consumer Protection Act, 2019 (misleading advertisement); Consumer Protection (E-Commerce) Rules, 2020 | 2 item(s), sha256 `371187789d5c…` |
| F-014 | medium | **Low reviewer order-history diversity** — 75% of reviewers are single-category purchasers with ≤3 lifetime orders | Policy 3.2: Coordinated / Fake Reviewer Accounts | Consumer Protection Act, 2019 (unfair trade practices); BIS IS 19000:2022 online consumer reviews standard | 0 item(s), sha256 `4f53cda18c2b…` |

## Recommended actions (for human approval)

- Escalate to compliance for seller audit (coordinated review activity)
- Suppress rating badge pending investigation
- Hold suspected reviews (~75% of total) out of the star rating pending human review
- Request supporting documents for: "genuine leather"
- Review all active listings of this seller for relisting evasion

## Historical precedent

100% of the 25 most similar past cases were confirmed review fraud.

Outcome mix: confirmed review fraud 100%

---
*Generated by TrustGuard (PS-13 prototype). This report is a detection and evidence layer; it is not an enforcement decision.*