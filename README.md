# TrustGuard: Marketplace Trust & Compliance System (PS-13)

TrustGuard is a multi-agent system that detects fake reviews, review rings and counterfeit or misrepresented listings. For each product it produces a compliance-ready trust report for human reviewers.

> **Detection and evidence layer, not enforcement.** Every output is a *recommendation* routed to a human queue. When the agents disagree, the case is marked `needs_manual_review` instead of auto-deciding.

---

## Quick start

```bash
pip install -r requirements.txt
python scripts/generate_data.py          # build the synthetic marketplace (already included in data/)
python scripts/run_pipeline.py P001      # analyse one product, print the report summary
python scripts/run_pipeline.py --all --evidence   # all products -> reports/ (+ evidence zips)
python scripts/evaluate.py               # precision / recall against planted ground truth
streamlit run app.py                     # dashboard at http://localhost:8501
```

Optional: set `ANTHROPIC_API_KEY` (and `pip install anthropic`) to have an LLM write the reviewer-facing explanation from the structured findings. The LLM never decides scores, tiers or policy mappings. Without a key, a deterministic template is used.

---

## Architecture

```
                     Product ID (+ region)
                             │
                 ┌───────────▼───────────┐
                 │ 10 · Orchestrator     │  routes data, resolves conflicts, packages report
                 └───────────┬───────────┘
                             │
                 ┌───────────▼───────────┐
                 │ 1 · Ingestion         │  reviews + reviewer metadata + listing + prices +
                 │                       │  seller history; timestamps normalized to UTC
                 └───────────┬───────────┘
        ┌──────────┬─────────┼─────────┬──────────┐        (run in parallel)
        ▼          ▼         ▼         ▼          ▼
   2 · Stats  3 · Text  4 · Network 5 · Claims 6 · Visual
        └──────────┴─────────┼─────────┴──────────┘
                             ▼
                 7 · Seller Risk Correlation   (uses 2-6 outputs: "young seller" + "ring" = systemic)
                             ▼
                 8 · Compliance Mapping        (flag → policy clause → regional regulation, SHA-256 audit trail)
                             ▼
                 9 · Trust Risk Scoring        (0-100, region-aware tiers, incremental re-scoring)
                             ▼
     Orchestrator: conflict check → case memory → explanation → routing queue → report + evidence pack
```

Every agent returns the same contract (`trustguard/models.py`):

```json
{"agent": "...", "score": 0.0-1.0, "confidence": 0.0-1.0, "flags": [{"flag_type", "title", "detail", "severity", "evidence": [...]}], "metrics": {...}}
```

Because every agent returns the same contract, agents are plug-ins: the orchestrator, compliance mapper and scorer never need to know how an agent works inside.

### The 10 agents

| # | Agent | How it works (MVP) | File |
|---|---|---|---|
| 1 | Review & Metadata Ingestion | Joins reviews with reviewer metadata. Normalizes mixed-offset timestamps to UTC. Computes `reviews`, `verified_purchase_rate` and `reviewer_account_age` at review time. Records data-quality notes. | `agents/ingestion.py` |
| 2 | Statistical Anomaly | Finds the busiest 72h sliding window and compares it to the category baseline (median of peer products). Measures 5★ share and Jensen-Shannon divergence against the category rating distribution, plus hour-of-day divergence. Detects price cuts that coincide with the burst. | `agents/statistical.py` |
| 3 | Linguistic Pattern | Char n-gram TF-IDF with cosine ≥ 0.80 builds a near-duplicate graph across *different* accounts; templated clusters are its connected components. Also detects generic superlatives with no product-specific detail and incentive disclosures. Outputs an authenticity score from 0 to 1. | `agents/linguistic.py` |
| 4 | Reviewer Network | Builds a graph linking accounts that share a device, or share an IP range *and* were created within 5 days of each other. Its components are candidate rings. Also checks seller-exclusive reviewers, reciprocal seller networks, creation-window concentration and order-history diversity. | `agents/network.py` |
| 5 | Product Claim Verification | Extracts material, origin, certification and safety claims from the listing and checks them against documents on file. Checks brand authorization and price against brand MSRP. | `agents/claims.py` |
| 6 | Visual Counterfeit Signal | 256-bit perceptual hash (dHash) of the listing photo. Finds the same photo on unrelated sellers' listings (last 60 days) and matches against brand reference imagery. | `agents/visual.py` |
| 7 | Seller Risk Correlation | Compares account age with review velocity, counts flags and warnings in the last 30 days, and detects relisting within 7 days of a takedown. Correlates all of this with product-level anomalies and outputs a seller tier. | `agents/seller.py` |
| 8 | Compliance Mapping | Deterministic lookup from flag to policy clause to region-specific regulatory reference. Prioritizes IP and safety exposure. Hashes each finding's evidence with SHA-256 for a tamper-evident audit trail. | `agents/compliance.py`, `config/policies.json` |
| 9 | Trust Risk Scoring | `100 × (0.65 × confidence-weighted mean + 0.35 × top-2 mean)`. A critical, high-confidence finding sets a floor so it cannot be averaged away. Tier cut-offs are region-aware. | `agents/scoring.py`, `config/weights.json`, `config/regions.json` |
| 10 | Orchestrator | Runs agents 2 to 6 in parallel and caches claims and visual results for incremental re-scoring. If review signals disagree, it sets `needs_manual_review`. It then adds historical precedent, writes the explanation, recommends actions and routes the case to a queue. | `orchestrator.py` |

### Advanced features included

| Feature | Where |
|---|---|
| Compliance dashboard across categories | Dashboard → *Compliance dashboard* tab (risk distribution by category, policy-clause heatmap) |
| Reviewer network graph view | Dashboard → *Reviewer network* tab |
| Historical case memory | `trustguard/case_memory.py`, nearest past cases by agent-score vector (e.g. "100% of similar cases were confirmed review fraud") |
| Region-aware compliance rules | `config/regions.json` (IN / EU / US tier thresholds and regulatory references), sidebar selector |
| Auto-generated audit evidence package | `report.evidence_package()`: zip with report, audit trail, flagged reviews, cluster membership, seller history, matched images and SHA-256 manifest |
| Before/after trust score timeline | `trustguard/timeline.py`, Dashboard → *Trust score timeline* tab |

---

## Data: why synthetic, and what's in it

Real marketplaces do not publish reviewer IP addresses, device fingerprints or seller takedown history. So `scripts/generate_data.py` simulates a marketplace with 10 sellers, 14 products, about 3,000 reviewers, about 6,200 reviews, 56 images, pricing history, certifications and 400 historical cases. It then **plants** known scenarios, which gives us ground truth:

| Product | Planted scenario | Expected |
|---|---|---|
| P001 Aria Leather Crossbody Bag | 512 reviews; 289 five-star posted in 72h by a ring of new single-category accounts sharing devices and IPs; templated text; stock photo reused by 4 unrelated sellers; "genuine leather" and "handcrafted in Italy" with no documents; 21-day-old seller with 2 flags and a relist after takedown; price cut during the burst | Critical |
| P002 Aria Mini Tote | Same seller, same ring, smaller burst | Critical / High |
| P013 Velora Canvas Belt | Partner seller sharing the same reviewer pool (reciprocal ring) | High |
| P003 Pulse Wireless Earbuds | Incentivized reviews from **real** customers: the text looks fake but the network is clean | Conflict → manual review |
| P004 LuxeCo Monogram Wallet | Counterfeit: brand imagery, unauthorized seller, price ~5% of MSRP | High → Legal/IP queue |
| P006 Terra Ceramic Mug | Brand-new seller, but honest | Must stay **Low** (fairness check) |
| Others | Established sellers, organic reviews | Low |

Swapping in real data only means replacing `data_loader.py`. For example, public review datasets (Amazon Reviews, YelpChi labeled spam, the Ott et al. deceptive opinion corpus) can be used for the text and timing agents.

## Current results (`python scripts/evaluate.py`)

```
Product level: 5 TP, 0 FP, 0 FN, 9 TN  ->  precision 1.00, recall 1.00
Review level:  precision 0.974, recall 1.000
```

These numbers are on planted synthetic data, so they show that the pipeline works end to end. They are **not** a claim of real-world accuracy. The next milestone is to evaluate on labeled public datasets.

---

## Project structure

```
ps13-trust-agent/
├── app.py                      Streamlit dashboard
├── config/                     policies.json · regions.json · weights.json
├── data/                       generated marketplace (CSV + images + ground truth)
├── reports/                    generated reports / evidence packages
├── scripts/
│   ├── generate_data.py        synthetic marketplace + planted fraud
│   ├── run_pipeline.py         CLI
│   └── evaluate.py             precision / recall vs ground truth
└── trustguard/
    ├── agents/                 the 9 worker agents (ingestion … scoring)
    ├── orchestrator.py         Agent 10
    ├── models.py               shared AgentResult / Flag contract
    ├── data_loader.py          data access layer (swap for real APIs/DB)
    ├── imaging.py              perceptual hashing
    ├── case_memory.py          historical precedent
    ├── timeline.py             trust-score timeline
    ├── report.py               Markdown/JSON report + evidence package
    └── llm.py                  optional LLM explanation layer
```

## Design decisions

- **Why multi-agent?** Each fraud signal needs a different technique: statistics, NLP, graphs, image hashing and rules. Separate agents keep each one testable, explainable and replaceable, and they run in parallel.
- **Why deterministic scoring and mapping?** Compliance teams need to reproduce and audit every decision. LLMs are confined to wording, never verdicts.
- **False positives:** every flag carries a confidence and its evidence. Conflicting signals go to manual review. A new seller alone does not trigger a flag (P006 scores Low). Nothing is enforced automatically.
- **Incremental re-scoring:** claims and visual results depend only on the listing, so they are cached. When new reviews arrive, only the review-dependent agents re-run. The timeline view uses this.

## Roadmap (next reviews)

1. Evaluate on public labeled datasets (YelpChi, Ott deceptive opinion spam, Amazon Reviews).
2. Linguistic agent: sentence-transformer embeddings, plus an LLM judge for borderline reviews.
3. Visual agent: CLIP embeddings for logo similarity, and stitching/packaging defect checks using close-up references.
4. Claims agent: LLM-based claim extraction for free-form listings.
5. Serve through FastAPI with a database backend. Port orchestration to LangGraph for persistent state and human-in-the-loop checkpoints. Stream new reviews into incremental re-scoring.
6. Reviewer feedback loop: case outcomes feed back into case memory and weight calibration.
