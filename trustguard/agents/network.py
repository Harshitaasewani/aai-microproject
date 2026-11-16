"""Agent 4 — Reviewer Network Agent.

Builds a graph of the product's reviewers, linking accounts that share a device fingerprint, or share
an IP range AND were created within 5 days of each other. Connected components of that graph are
candidate review rings. Also checks reviewer exclusivity (accounts that only ever review this seller)
and reciprocal patterns (a small set of sellers sharing the same reviewer pool).
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd

from ..models import AgentResult, CaseData, Flag

NAME = "Reviewer Network"
CREATION_WINDOW_DAYS = 5
MIN_RING = 5


def _dense_window(dates: pd.Series, days: int) -> tuple[int, pd.Timestamp | None]:
    if dates.empty:
        return 0, None
    t = np.sort(dates.values.astype("datetime64[ns]"))
    end = np.searchsorted(t, t + np.timedelta64(days, "D"), side="right")
    counts = end - np.arange(len(t))
    i = int(counts.argmax())
    return int(counts[i]), pd.Timestamp(t[i], tz="UTC")


def run(case: CaseData) -> AgentResult:
    rv = case.reviews
    m = case.market
    seller_id = case.seller["seller_id"]
    people = rv.drop_duplicates("reviewer_id")[["reviewer_id", "ip_prefix", "device_id", "account_created",
                                                "categories_purchased", "total_orders"]].reset_index(drop=True)
    n = len(people)
    if n < 5:
        return AgentResult(NAME, 0.0, 0.1, [], {"reviewers": n}, "Too few reviewers for network analysis.")
    flags: list[Flag] = []

    # --- shared-signal graph
    g = nx.Graph()
    g.add_nodes_from(people.reviewer_id)
    for _, grp in people.groupby("device_id"):
        ids = grp.reviewer_id.tolist()
        g.add_edges_from((ids[0], x, {"signal": "device"}) for x in ids[1:])
    for _, grp in people.groupby("ip_prefix"):
        grp = grp.sort_values("account_created")
        ids, dates = grp.reviewer_id.tolist(), grp.account_created.tolist()
        for a in range(len(ids) - 1):
            if (dates[a + 1] - dates[a]).days <= CREATION_WINDOW_DAYS:
                g.add_edge(ids[a], ids[a + 1], signal="ip+creation")
    rings = sorted((c for c in nx.connected_components(g) if len(c) >= MIN_RING), key=len, reverse=True)
    ring_members = set().union(*rings) if rings else set()
    ring_share = len(ring_members) / n

    # --- market-wide footprint of each reviewer: which sellers do they review?
    all_rv = m.reviews[m.reviews.reviewer_id.isin(people.reviewer_id) & (m.reviews.timestamp_utc <= case.as_of)]
    all_rv = all_rv.merge(m.products[["product_id", "seller_id"]], on="product_id")
    sellers_by_reviewer = all_rv.groupby("reviewer_id").seller_id.agg(set)
    # "Exclusive" = the reviewer's entire footprint is this seller AND they have almost no purchase history
    # elsewhere (a one-off organic buyer with a long order history is not exclusive).
    thin = set(people[people.total_orders <= 3].reviewer_id)
    exclusive = [r for r, s in sellers_by_reviewer.items() if s == {seller_id} and r in thin]
    excl_share = len(exclusive) / n

    # reciprocal network: other sellers sharing many of THIS product's ring/exclusive-ish reviewers
    shared = all_rv[all_rv.seller_id != seller_id].groupby("seller_id").reviewer_id.nunique()
    linked = {}
    for other, cnt in shared.items():
        if cnt >= 15:
            pool = set(all_rv[all_rv.seller_id == other].reviewer_id) & set(people.reviewer_id)
            narrow = sellers_by_reviewer.loc[list(pool)].apply(lambda s: s <= {seller_id, other}).mean()
            if narrow >= 0.8:
                linked[other] = int(cnt)
    network_excl = float(np.mean([s <= ({seller_id} | set(linked)) and r in thin
                                  for r, s in sellers_by_reviewer.items()]))

    # --- account creation concentration and purchase-history diversity
    created = people.account_created
    win_n, win_start = _dense_window(created, CREATION_WINDOW_DAYS)
    win_share = win_n / n
    low_div = ((people.categories_purchased <= 1) & (people.total_orders <= 3)).mean()

    if rings:
        ring_df = people[people.reviewer_id.isin(ring_members)]
        flags.append(Flag(
            "coordinated_network", "Coordinated reviewer network",
            f"{len(ring_members)} reviewer accounts in {len(rings)} cluster{'s' if len(rings) != 1 else ''} share devices or IP ranges with accounts "
            f"created within {CREATION_WINDOW_DAYS} days of each other (largest cluster {len(rings[0])}; "
            f"{ring_df.device_id.nunique()} devices, {ring_df.ip_prefix.nunique()} IP ranges)",
            "critical" if ring_share >= 0.4 else "high" if ring_share >= 0.15 else "medium",
            [{"cluster": k + 1, "size": len(c), "reviewer_ids": sorted(c)[:60]} for k, c in enumerate(rings[:5])]))
    if win_share >= 0.25 and win_n >= 20:
        flags.append(Flag(
            "creation_window", "Accounts created in the same window",
            f"{win_n} reviewer accounts ({win_share:.0%}) were created within the same {CREATION_WINDOW_DAYS}-day window "
            f"starting {win_start:%d %b %Y}", "high" if win_share >= 0.5 else "medium"))
    if excl_share >= 0.2 or (linked and network_excl >= 0.3):
        detail = f"{len(exclusive)} reviewers ({excl_share:.0%}) have only ever reviewed this seller's catalog"
        if linked:
            detail += (f"; {network_excl:.0%} review only this seller and linked seller(s) "
                       f"{', '.join(linked)} — reciprocal review pattern")
        flags.append(Flag("seller_exclusive_reviewers", "Reviewers exclusive to this seller network", detail,
                          "high" if max(excl_share, network_excl) >= 0.4 else "medium", sorted(exclusive)[:60]))
    if low_div >= 0.25:
        flags.append(Flag(
            "low_order_diversity", "Low reviewer order-history diversity",
            f"{low_div:.0%} of reviewers are single-category purchasers with ≤3 lifetime orders", "medium"))

    ring_s = min(1.0, ring_share / 0.4)
    excl_s = min(1.0, max(excl_share, network_excl if linked else 0) / 0.5)
    win_s = min(1.0, max(0.0, win_share - 0.1) / 0.4)
    div_s = min(1.0, low_div / 0.5)
    parts = [ring_s, excl_s, win_s, div_s]
    score = 0.6 * max(parts) + 0.4 * float(np.mean(parts))
    metrics = {
        "reviewers": n, "ring_clusters": len(rings), "ring_accounts": len(ring_members),
        "ring_share": round(ring_share, 3), "exclusive_share": round(excl_share, 3),
        "linked_sellers": linked, "network_exclusive_share": round(float(network_excl), 3),
        "creation_window_share": round(win_share, 3), "low_diversity_share": round(float(low_div), 3),
        "ring_assignment": {r: k + 1 for k, c in enumerate(rings) for r in c},
    }
    summary = f"{len(ring_members)} of {n} reviewers in coordinated clusters; linked sellers: {list(linked) or 'none'}"
    return AgentResult(NAME, float(min(1.0, score)), float(min(1.0, 0.3 + n / 80)), flags, metrics, summary)
