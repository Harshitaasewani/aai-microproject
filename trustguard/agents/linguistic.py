"""Agent 3 — Linguistic Pattern Agent.

Signals of fake / incentivized authorship:
  * near-duplicate phrasing across different reviewer accounts (char n-gram TF-IDF cosine similarity,
    robust to small edits like "!!" or "Wow.")
  * generic superlatives with no product-specific detail
  * explicit incentive disclosures ("in exchange for my honest review")
Upgrade path: swap TF-IDF for sentence-transformer embeddings and add an LLM judge for borderline text.
"""
from __future__ import annotations

import re
from collections import Counter

import networkx as nx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..models import AgentResult, CaseData, Flag

NAME = "Linguistic Pattern"
DUP_THRESHOLD = 0.80
MIN_CLUSTER = 5

GENERIC = {"amazing", "excellent", "superb", "best", "awesome", "great", "perfect", "highly", "recommend",
           "exceeded", "expectations", "wow", "love", "fantastic", "outstanding", "five", "stars", "value"}
CATEGORY_VOCAB = {
    "bags": "strap zipper pocket pockets stitching lining handle buckle leather colour color room fits shoulder smell material logo edges",
    "electronics": "battery bass pairing calls charge charging case pocket connection volume app port hours disconnecting sound",
    "home": "glaze handle tea rim dishwasher chip finish",
    "apparel": "cotton fit shrink shrank neckline wash washing hem size colour",
    "beauty": "skin absorbs dropper breakout serum irritation sticky drops",
    "footwear": "cushioning sole grip mesh runs size break-in toe",
}
STOP = {"with", "and", "the", "for", "this", "that", "from", "your", "into", "made", "perfect", "daily", "most"}
INCENTIVE = re.compile(r"(?:in exchange for|received (?:this|it|the product)?\s*(?:product)?\s*(?:free|at a discount)|"
                       r"discount for my|free for review|for review purposes|unbiased review)", re.I)


def _tokens(s: str) -> list[str]:
    return re.findall(r"[a-z][a-z\-]+", s.lower())


def _top_phrase(texts: list[str], n: int = 4) -> tuple[str, int]:
    c = Counter()
    for t in texts:
        tok = _tokens(t)
        c.update({" ".join(tok[i:i + n]) for i in range(len(tok) - n + 1)})
    return c.most_common(1)[0] if c else ("", 0)


def run(case: CaseData) -> AgentResult:
    rv = case.reviews
    n = len(rv)
    if n < 5:
        return AgentResult(NAME, 0.0, 0.1, [], {"reviews": n}, "Too few reviews for linguistic analysis.")
    texts = rv.text.fillna("").tolist()
    flags: list[Flag] = []

    # --- near-duplicate clusters across *different* accounts
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=True, min_df=1)
    X = vec.fit_transform(texts)
    S = cosine_similarity(X, dense_output=True)
    np.fill_diagonal(S, 0)
    g = nx.Graph()
    ii, jj = np.where(np.triu(S >= DUP_THRESHOLD))
    reviewers = rv.reviewer_id.to_numpy()
    g.add_edges_from((int(i), int(j)) for i, j in zip(ii, jj) if reviewers[i] != reviewers[j])
    clusters = [sorted(c) for c in nx.connected_components(g) if len(c) >= MIN_CLUSTER]
    clusters.sort(key=len, reverse=True)
    in_cluster = sorted({i for c in clusters for i in c})
    dup_share = len(in_cluster) / n

    # --- specificity: does the review mention anything concrete about this product?
    vocab = set(CATEGORY_VOCAB.get(case.product["category"], "").split())
    vocab |= {t for t in _tokens(case.product["title"] + " " + case.product["description"]) if len(t) > 3} - STOP
    toks = [set(_tokens(t)) for t in texts]
    specific = np.array([len(t & vocab) > 0 for t in toks])
    generic_ratio = np.array([len(t & GENERIC) / max(1, len(t)) for t in toks])
    generic_nonspecific = (~specific) & (generic_ratio >= 0.15)
    gn_share = float(generic_nonspecific.mean())

    # --- incentive disclosures
    incentive = rv.text.fillna("").str.contains(INCENTIVE)
    inc_share = float(incentive.mean())

    if clusters:
        members = [texts[i] for i in in_cluster]
        # prefer the longest shared phrase that still covers most of what the best short phrase covers
        cands = [_top_phrase(members, n=k) for k in (6, 5, 4, 3)]
        best3 = cands[-1][1]
        phrase = next((p for p, c in cands if p and c >= 0.6 * best3), cands[-1][0])
        phrase_hits = int(sum(phrase in " ".join(_tokens(t)) for t in texts)) if phrase else 0
        flags.append(Flag(
            "near_duplicate_text", "Near-duplicate review text across accounts",
            f"{len(in_cluster)} reviews ({dup_share:.0%}) from different accounts fall into {len(clusters)} templated "
            f"cluster{'s' if len(clusters) != 1 else ''}; largest has "
            f"{len(clusters[0])} reviews. {phrase_hits} reviews share the phrase pattern \"{phrase}\"",
            "critical" if dup_share >= 0.5 else "high" if dup_share >= 0.2 else "medium",
            [{"cluster": k + 1, "size": len(c), "example": texts[c[0]],
              "review_ids": rv.review_id.iloc[c].tolist()} for k, c in enumerate(clusters[:5])]))
    if gn_share >= 0.15:
        flags.append(Flag(
            "generic_no_detail", "Generic superlatives without product detail",
            f"{gn_share:.0%} of reviews use generic praise and mention no product-specific detail "
            f"(e.g. strap, zipper, stitching for this category)",
            "high" if gn_share >= 0.4 else "medium", rv.review_id[generic_nonspecific].tolist()))
    if inc_share >= 0.05:
        flags.append(Flag(
            "incentivized_disclosure", "Incentivized reviews",
            f"{int(incentive.sum())} reviews ({inc_share:.0%}) disclose a free product or discount in exchange for the review",
            "high" if inc_share >= 0.15 else "medium", rv.review_id[incentive].tolist()))

    dup_s = min(1.0, dup_share / 0.5)
    gn_s = min(1.0, gn_share / 0.5)
    inc_s = min(1.0, inc_share / 0.25)
    risk = float(min(1.0, 0.55 * max(dup_s, gn_s, inc_s) + 0.45 * (0.5 * dup_s + 0.25 * gn_s + 0.25 * inc_s)))
    authenticity = round(1 - risk, 2)
    metrics = {
        "reviews": n, "authenticity_score": authenticity, "near_duplicate_share": round(dup_share, 3),
        "templated_clusters": len(clusters), "largest_cluster": len(clusters[0]) if clusters else 0,
        "generic_nonspecific_share": round(gn_share, 3), "specific_detail_share": round(float(specific.mean()), 3),
        "incentive_disclosure_share": round(inc_share, 3),
        "flagged_review_ids": sorted(set(rv.review_id.iloc[in_cluster]) | set(rv.review_id[incentive])
                                     | set(rv.review_id[generic_nonspecific])),
    }
    conf = min(1.0, 0.3 + n / 80)
    return AgentResult(NAME, risk, conf, flags, metrics, f"Linguistic authenticity score {authenticity:.2f}/1.0")
