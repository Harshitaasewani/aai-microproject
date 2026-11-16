"""TrustGuard dashboard — run with:  streamlit run app.py"""
from __future__ import annotations

import json

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from trustguard import report
from trustguard.orchestrator import AGENT_TITLES, Orchestrator
from trustguard.timeline import score_timeline

st.set_page_config(page_title="TrustGuard — Marketplace Trust & Compliance", page_icon="🛡️", layout="wide")

TIER_COLOR = {"Low": "#2e7d32", "Medium": "#f9a825", "High": "#ef6c00", "Critical": "#c62828"}
SEV_ICON = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
AGENT_KEYS = ["statistical", "linguistic", "network", "claims", "visual", "seller"]

st.markdown("""
<style>
.block-container {padding-top: 1.6rem;}
.kpi {border: 1px solid rgba(128,128,128,.25); border-radius: 12px; padding: 14px 16px;}
.kpi .label {font-size: .78rem; opacity: .7; text-transform: uppercase; letter-spacing: .04em;}
.kpi .value {font-size: 1.3rem; font-weight: 700; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
.summary-table td {vertical-align: top; padding: 8px 10px; border-bottom: 1px solid rgba(128,128,128,.2);}
.summary-table td:first-child {font-weight: 600; white-space: nowrap; width: 190px;}
.pill {display:inline-block; padding: 2px 10px; border-radius: 999px; color: white; font-weight: 600; font-size: .85rem;}
</style>""", unsafe_allow_html=True)


@st.cache_resource
def get_orch() -> Orchestrator:
    return Orchestrator()


@st.cache_data(show_spinner=False)
def run_case(pid: str, region: str | None) -> dict:
    return get_orch().run(pid, region=region)


@st.cache_data(show_spinner=False)
def run_all(region: str | None) -> list[dict]:
    return [get_orch().run(p, region=region, use_llm=False) for p in get_orch().market.products.product_id]


@st.cache_data(show_spinner=False)
def timeline(pid: str, region: str | None) -> pd.DataFrame:
    return score_timeline(get_orch(), pid, points=14, region=region)


def kpi(col, label, value, color=None):
    style = f"color:{color}" if color else ""
    col.markdown(f"<div class='kpi'><div class='label'>{label}</div><div class='value' style='{style}'>{value}</div></div>",
                 unsafe_allow_html=True)


orch = get_orch()
market = orch.market
products = market.products.set_index("product_id")

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("🛡️ TrustGuard")
    st.caption("PS-13 · Review Authenticity & Counterfeit Detection — multi-agent detection & evidence layer")
    pid = st.selectbox("Product", products.index, format_func=lambda p: f"{p} · {products.loc[p, 'title']}")
    region_opt = st.selectbox("Marketplace region", ["Auto (seller region)", "IN", "EU", "US"])
    region = None if region_opt.startswith("Auto") else region_opt
    st.divider()
    st.markdown("**Agent pipeline**")
    st.markdown("\n".join(f"- {t}" for t in AGENT_TITLES.values()))
    st.caption("Agents 2–6 run in parallel. The system never enforces — every action is routed to a human queue.")

with st.spinner("Running 10-agent pipeline…"):
    r = run_case(pid, region)

p = r["product"]
st.markdown(f"## {p['title']}")
st.caption(f"{p['product_id']} · {p['category']} · Seller **{p['seller_name']}** ({p['seller_id']}, "
           f"{p['seller_account_age_days']} days old, region {p['seller_region']}) · Case {r['case_id']}")

c = st.columns(6)
kpi(c[0], "Risk score", f"{r['risk_score']:.0f}/100", TIER_COLOR[r["tier"]])
kpi(c[1], "Tier", r["tier"], TIER_COLOR[r["tier"]])
kpi(c[2], "Reviews · avg", f"{p['reviews']} · {p['avg_rating']}★")
kpi(c[3], "Verified purchase", f"{p['verified_purchase_rate']:.0%}")
kpi(c[4], "Decision", r["decision"]["status"].replace("_", " "))
kpi(c[5], "Routed to", r["decision"]["queue"].split("—")[-1].strip().split(" (")[0])
if r["decision"]["conflict"]:
    st.warning(f"**Conflicting signals:** {r['decision']['conflict']}. Flagged for manual review instead of auto-deciding.")

tabs = st.tabs(["🔎 Case report", "📈 Review activity", "🕸️ Reviewer network", "⏱️ Trust score timeline",
                "🗂️ Compliance dashboard", "📦 Evidence package"])

# ---------------------------------------------------------------- 1. case report
with tabs[0]:
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown("#### Agentic output")
        rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in r["summary_table"].items())
        st.markdown(f"<table class='summary-table'>{rows}</table>", unsafe_allow_html=True)
        st.markdown("#### Findings & audit trail")
        for f in r["findings"]:
            exp = " · ⚖️ regulatory exposure" if f["regulatory_exposure"] else ""
            with st.expander(f"{SEV_ICON[f['severity']]} {f['finding_id']} · {f['title']} — {f['policy_clause']}{exp}"):
                st.write(f["detail"])
                st.caption(f"Agent: {f['agent']} · severity {f['severity']} · confidence {f['confidence']} · "
                           f"evidence items {f['evidence_count']} · sha256 {f['evidence_sha256'][:16]}…")
                if f["regulatory_reference"]:
                    st.caption(f"Indicative regulatory reference ({r['region']}): {f['regulatory_reference']}")
                if f["evidence"]:
                    ev = f["evidence"]
                    st.dataframe(pd.DataFrame(ev) if isinstance(ev[0], dict) else pd.DataFrame({"evidence": ev}),
                                 width="stretch", height=min(260, 38 + 35 * len(ev)))
    with right:
        st.markdown("#### Agent signals")
        sc = r["scoring"]
        df = pd.DataFrame({"agent": [r["agents"][k]["agent"] for k in AGENT_KEYS],
                           "risk signal": [sc["agent_scores"][k] for k in AGENT_KEYS],
                           "confidence": [sc["agent_confidence"][k] for k in AGENT_KEYS]})
        fig = px.bar(df, x="risk signal", y="agent", orientation="h", range_x=[0, 1], text="risk signal",
                     color="risk signal", color_continuous_scale=["#2e7d32", "#f9a825", "#c62828"], range_color=[0, 1],
                     hover_data=["confidence"])
        fig.update_traces(texttemplate="%{x:.2f}")
        fig.update_layout(height=300, margin=dict(l=0, r=10, t=10, b=0), coloraxis_showscale=False, yaxis_title=None,
                          yaxis=dict(categoryorder="array", categoryarray=df.agent.tolist()[::-1]))
        st.plotly_chart(fig, width="stretch")
        st.caption(f"Score = 100 × (0.65 × confidence-weighted mean + 0.35 × top-2 mean) = {sc['risk_score']:.0f}"
                   + (" · critical-finding floor applied" if sc["critical_floor_applied"] else ""))

        st.markdown("#### Recommended actions")
        for x in r["decision"]["recommendations"]:
            st.markdown(f"- {x}")
        st.info(r["decision"]["enforcement"])

        st.markdown("#### Historical precedent")
        cm = r["case_memory"]
        st.write(f"**{cm['headline']}.**")
        st.dataframe(pd.DataFrame(cm["nearest"]), width="stretch", hide_index=True)

        st.markdown("#### Pipeline trace")
        st.dataframe(pd.DataFrame(r["trace"]), width="stretch", hide_index=True)
        if r["data_quality"]:
            st.caption("Data quality: " + "; ".join(r["data_quality"]))

    st.markdown("#### Agent details")
    for k in AGENT_KEYS:
        a = r["agents"][k]
        with st.expander(f"{a['agent']} — {a['summary']}"):
            st.json({m: v for m, v in a["metrics"].items() if m not in ("ring_assignment", "flagged_review_ids")})

# ---------------------------------------------------------------- 2. review activity
with tabs[1]:
    rv = market.reviews[market.reviews.product_id == pid].copy()
    rv["day"] = rv.timestamp_utc.dt.floor("D")
    daily = rv.groupby(["day", "rating"]).size().reset_index(name="reviews")
    daily["rating"] = daily.rating.astype(str) + "★"
    fig = px.bar(daily, x="day", y="reviews", color="rating", barmode="stack",
                 color_discrete_map={"1★": "#c62828", "2★": "#ef6c00", "3★": "#f9a825", "4★": "#7cb342", "5★": "#2e7d32"},
                 category_orders={"rating": ["5★", "4★", "3★", "2★", "1★"]})
    sm = r["agents"]["statistical"]["metrics"]
    if sm.get("window_start_utc") and sm.get("spike_vs_expected_72h_x", 0) >= 3:
        fig.add_vrect(x0=sm["window_start_utc"], x1=sm["window_end_utc"], fillcolor="red", opacity=0.12, line_width=0,
                      annotation_text=f"peak 72h: {sm['max_72h_count']} reviews", annotation_position="top left")
    ph = market.prices[market.prices.product_id == pid]
    fig.add_trace(go.Scatter(x=pd.to_datetime(ph.date), y=ph.price_inr, name="price (₹)", yaxis="y2",
                             mode="lines+markers", line=dict(color="#5c6bc0", width=2)))
    fig.update_layout(height=430, yaxis2=dict(overlaying="y", side="right", title="price ₹", showgrid=False),
                      margin=dict(l=0, r=0, t=30, b=0), legend=dict(orientation="h"))
    st.plotly_chart(fig, width="stretch")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Category baseline", f"{sm.get('category_weekly_baseline', 0):.0f}/week")
    c2.metric("Peak 72h vs weekly baseline", f"{sm.get('spike_vs_weekly_baseline_x', 0):.0f}×")
    c3.metric("5★ share", f"{sm.get('five_star_share', 0):.0%}", f"category {sm.get('category_five_star_share', 0):.0%}",
              delta_color="off")
    c4.metric("Linguistic authenticity", f"{r['agents']['linguistic']['metrics'].get('authenticity_score', 1):.2f}/1.0")
    st.markdown("##### Sample reviews")
    flagged = set(r["agents"]["linguistic"]["metrics"].get("flagged_review_ids", []))
    rv["flagged"] = rv.review_id.isin(flagged)
    show = pd.concat([rv[rv.flagged].head(6), rv[~rv.flagged].head(6)])
    st.dataframe(show[["review_id", "rating", "timestamp_utc", "verified_purchase", "flagged", "text"]],
                 width="stretch", hide_index=True)

# ---------------------------------------------------------------- 3. network
with tabs[2]:
    nm = r["agents"]["network"]["metrics"]
    ring = nm.get("ring_assignment", {})
    rvp = market.reviews[market.reviews.product_id == pid].merge(market.reviewers, on="reviewer_id")
    people = rvp.drop_duplicates("reviewer_id")
    # cap organic reviewers for readability; always keep ring members
    people = pd.concat([people[people.reviewer_id.isin(ring)], people[~people.reviewer_id.isin(ring)].head(150)])
    foot = market.reviews[market.reviews.reviewer_id.isin(people.reviewer_id)].merge(
        market.products[["product_id", "seller_id"]], on="product_id")
    G = nx.Graph()
    for s in foot.seller_id.unique():
        G.add_node(s, kind="seller")
    for _, row in people.iterrows():
        G.add_node(row.reviewer_id, kind="reviewer", cluster=ring.get(row.reviewer_id, 0), device=row.device_id)
    for _, row in foot.drop_duplicates(["reviewer_id", "seller_id"]).iterrows():
        G.add_edge(row.reviewer_id, row.seller_id, kind="reviewed")
    for _, grp in people[people.reviewer_id.isin(ring)].groupby("device_id"):
        ids = grp.reviewer_id.tolist()
        G.add_edges_from((ids[0], x) for x in ids[1:])
    pos = nx.spring_layout(G, seed=7, k=0.08, iterations=60)
    ex, ey = [], []
    for a, b in G.edges():
        ex += [pos[a][0], pos[b][0], None]
        ey += [pos[a][1], pos[b][1], None]
    fig = go.Figure(go.Scatter(x=ex, y=ey, mode="lines", line=dict(width=0.4, color="rgba(140,140,140,.35)"),
                               hoverinfo="skip", showlegend=False))
    rv_nodes = [n for n, d in G.nodes(data=True) if d["kind"] == "reviewer"]
    for label, sel, color in [("organic reviewer", [n for n in rv_nodes if not G.nodes[n]["cluster"]], "#90a4ae"),
                              ("coordinated cluster", [n for n in rv_nodes if G.nodes[n]["cluster"]], "#e53935")]:
        fig.add_trace(go.Scatter(x=[pos[n][0] for n in sel], y=[pos[n][1] for n in sel], mode="markers", name=label,
                                 marker=dict(size=6, color=color), text=[f"{n} · {G.nodes[n]['device']}" for n in sel],
                                 hoverinfo="text"))
    sel = [n for n, d in G.nodes(data=True) if d["kind"] == "seller"]
    fig.add_trace(go.Scatter(x=[pos[n][0] for n in sel], y=[pos[n][1] for n in sel], mode="markers+text", name="seller",
                             text=sel, textposition="top center",
                             marker=dict(size=[26 if n == p["seller_id"] else 16 for n in sel], symbol="diamond",
                                         color=["#1e88e5" if n == p["seller_id"] else "#8e24aa" if n in nm.get("linked_sellers", {}) else "#546e7a" for n in sel])))
    fig.update_layout(height=560, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(visible=False), yaxis=dict(visible=False),
                      legend=dict(orientation="h"))
    c1, c2 = st.columns([3, 1])
    c1.plotly_chart(fig, width="stretch")
    with c2:
        st.metric("Accounts in coordinated clusters", f"{nm.get('ring_accounts', 0)} / {nm.get('reviewers', 0)}")
        st.metric("Created in same 5-day window", f"{nm.get('creation_window_share', 0):.0%}")
        st.metric("Single-category, ≤3 orders", f"{nm.get('low_diversity_share', 0):.0%}")
        st.metric("Linked sellers (reciprocal)", ", ".join(nm.get("linked_sellers", {})) or "none")
        st.caption("Red = accounts linked by shared device / IP range + creation window. Purple diamonds = other "
                   "sellers sharing the same reviewer pool. Organic reviewers capped at 150 for readability.")

# ---------------------------------------------------------------- 4. timeline
with tabs[3]:
    with st.spinner("Re-scoring the case as of earlier dates (incremental: claims/visual cached)…"):
        tl = timeline(pid, region)
    fig = go.Figure()
    for name, lo, hi in [("Low", 0, 30), ("Medium", 30, 55), ("High", 55, 75), ("Critical", 75, 100)]:
        fig.add_hrect(y0=lo, y1=hi, fillcolor=TIER_COLOR[name], opacity=0.07, line_width=0,
                      annotation_text=name, annotation_position="right")
    fig.add_trace(go.Scatter(x=tl.as_of, y=tl.risk_score, mode="lines+markers", name="risk score",
                             line=dict(width=3, color="#263238")))
    fig.add_trace(go.Bar(x=tl.as_of, y=tl.reviews, name="cumulative reviews", yaxis="y2", opacity=0.25,
                         marker_color="#1e88e5"))
    fig.update_layout(height=420, yaxis=dict(range=[0, 100], title="risk score"),
                      yaxis2=dict(overlaying="y", side="right", showgrid=False, title="reviews"),
                      margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h"))
    st.plotly_chart(fig, width="stretch")
    jump = tl.risk_score.diff().idxmax() if len(tl) > 1 else None
    if jump is not None and tl.risk_score.diff().max() > 10:
        changed = [k for k in AGENT_KEYS if abs(tl[k][jump] - tl[k][jump - 1]) >= 0.2]
        st.write(f"Largest jump: **{tl.risk_score[jump - 1]:.0f} → {tl.risk_score[jump]:.0f}** between "
                 f"{tl.as_of[jump - 1]:%d %b} and {tl.as_of[jump]:%d %b}"
                 + (f", driven by: {', '.join(changed)}" if changed else "") + ".")
    st.caption("Listing-level signals (claims, imagery, seller history) exist from day one; review-driven signals "
               "(statistical, linguistic, network) appear as manipulated reviews accumulate.")
    st.dataframe(tl.assign(as_of=tl.as_of.dt.strftime("%d %b %Y")), width="stretch", hide_index=True)

# ---------------------------------------------------------------- 5. compliance dashboard
with tabs[4]:
    with st.spinner("Scoring all products…"):
        allr = run_all(region)
    df = pd.DataFrame([{"product": x["product"]["product_id"], "title": x["product"]["title"],
                        "category": x["product"]["category"], "seller": x["product"]["seller_name"],
                        "risk_score": x["risk_score"], "tier": x["tier"], "status": x["decision"]["status"],
                        "queue": x["decision"]["queue"]} for x in allr])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Products scanned", len(df))
    c2.metric("Critical / High", int(df.tier.isin(["Critical", "High"]).sum()))
    c3.metric("Needs manual review", int((df.status == "needs_manual_review").sum()))
    c4.metric("With regulatory exposure", sum(x["compliance"]["regulatory_exposure"] for x in allr))
    a, b = st.columns(2)
    fig = px.strip(df, x="category", y="risk_score", color="tier", hover_data=["title", "seller"],
                   color_discrete_map=TIER_COLOR, stripmode="overlay")
    fig.update_traces(marker=dict(size=13))
    fig.update_layout(height=380, title="Risk-score distribution by category", yaxis_range=[-3, 100],
                      margin=dict(l=0, r=0, t=40, b=0))
    a.plotly_chart(fig, width="stretch")
    cl = pd.DataFrame([{"category": x["product"]["category"], "clause": f["policy_clause"]}
                       for x in allr for f in x["findings"]])
    if len(cl):
        heat = cl.groupby(["clause", "category"]).size().unstack(fill_value=0)
        fig = px.imshow(heat, text_auto=True, color_continuous_scale="Reds", aspect="auto",
                        title="Flagged policy-clause frequency by category")
        fig.update_layout(height=380, margin=dict(l=0, r=0, t=40, b=0), coloraxis_showscale=False)
        b.plotly_chart(fig, width="stretch")
    st.dataframe(df.sort_values("risk_score", ascending=False), width="stretch", hide_index=True)

# ---------------------------------------------------------------- 6. evidence package
with tabs[5]:
    st.write("Everything a legal / compliance reviewer needs in one packet: report, audit trail with evidence "
             "hashes, flagged reviews with reasons, reviewer cluster membership, seller history and image matches. "
             "A SHA-256 manifest makes tampering detectable.")
    c1, c2, c3 = st.columns(3)
    c1.download_button("⬇️ Evidence package (.zip)", report.evidence_package(r, market),
                       file_name=f"{r['case_id']}_evidence.zip", mime="application/zip", width="stretch")
    c2.download_button("⬇️ Report (.md)", report.to_markdown(r), file_name=f"{pid}_report.md", width="stretch")
    c3.download_button("⬇️ Report (.json)", json.dumps(r, indent=2, default=str), file_name=f"{pid}_report.json",
                       width="stretch")
    st.markdown("##### Image evidence")
    imgs = [("This listing", products.loc[pid, "image_file"])]
    for f in r["findings"]:
        if f["flag_type"] == "reused_image":
            imgs += [(f"{e['seller_name']} · {e['listing_id']} (Δ{e['hamming_distance']})", e["image"]) for e in f["evidence"]]
        if f["flag_type"] == "brand_image_match":
            imgs += [(f"Brand reference (Δ{e['hamming_distance']})", e["reference"]) for e in f["evidence"]]
    cols = st.columns(min(5, len(imgs)))
    for i, (cap, img) in enumerate(imgs[:5]):
        cols[i].image(str(market.image_dir / img), caption=cap, width="stretch")
    st.markdown("##### Report preview")
    st.markdown(report.to_markdown(r))
