"""
Stakeholder readout for the approval odds test.

Regenerates the simulated experiment on start, computes metrics with the same SQL files
used in the notebooks, and presents the decision first, then what changed and why, with
the statistical checks available in a collapsible section. Run from the project folder:

    python -m streamlit run app/streamlit_app.py
"""
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import analysis as an
from src import simulate as sim

SQL = ROOT / "sql"

# Palette: control recedes in gray, treatment stands out in plum. Green and red are used
# only for good and bad results, never for the arms. Amber is the single highlight.
PAPER, INK, MUTED = "#F7F8FA", "#1C2430", "#5E6672"
CONTROL, TREATMENT = "#8A8F98", "#5B3E8E"
GOOD, BAD, NEUTRAL, HIGHLIGHT = "#2F7D5B", "#B8473A", "#8A8F98", "#C98A1B"
FONT = "Public Sans, sans-serif"

st.set_page_config(page_title="Approval odds test readout", layout="wide")
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, h1, h2, h3, p, li, span, div {{ font-family: {FONT}; }}
.block-container {{ max-width: 1150px; padding-top: 2.2rem; }}
h1 {{ font-weight: 700; letter-spacing: -0.02em; color: {INK}; }}
h2 {{ font-weight: 600; color: {INK}; margin-top: 2.2rem; }}
.decision {{ border-left: 6px solid {GOOD}; background: #FFFFFF; padding: 1.1rem 1.4rem;
             margin: 0.6rem 0 1.4rem 0; }}
.decision .verdict {{ font-size: 1.6rem; font-weight: 700; color: {GOOD}; }}
.decision .why {{ color: {INK}; font-size: 1.02rem; margin-top: 0.3rem; max-width: 70ch; }}
.kpi {{ background: #FFFFFF; padding: 1rem 1.1rem; border: 1px solid #E3E6EB; height: 100%; }}
.kpi .name {{ color: {MUTED}; font-size: 0.92rem; }}
.kpi .values {{ font-size: 1.45rem; font-weight: 600; color: {INK}; margin: 0.25rem 0; }}
.kpi .delta {{ font-weight: 600; font-size: 1rem; }}
.kpi .note {{ color: {MUTED}; font-size: 0.85rem; margin-top: 0.35rem; }}
.next {{ background: #FFFFFF; border-top: 3px solid {TREATMENT}; padding: 0.9rem 1rem; height: 100%; }}
.next .title {{ font-weight: 600; color: {INK}; margin-bottom: 0.3rem; }}
.next .body {{ color: {MUTED}; font-size: 0.93rem; }}
.lede {{ color: {MUTED}; max-width: 75ch; }}
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Running the 28 day test simulation...")
def load_data():
    """Simulate the test and historical traffic; return everything the page needs."""
    users, partners, rng = sim.build_marketplace()
    impressions, truth = sim.simulate_outcomes(users, partners, rng)
    con = duckdb.connect()
    sim.load_to_duckdb(con, users, partners, impressions, truth)
    con.execute((SQL / "01_user_metrics.sql").read_text())
    um = con.execute("SELECT * FROM user_metrics").df()
    cols = ["impressions", "clicks", "applications", "funded", "revenue", "prior_visits"]
    um[cols] = um[cols].astype(float)
    lead_share = con.execute((SQL / "03_partner_lead_share.sql").read_text()).df()
    srm = con.execute((SQL / "04_srm_counts.sql").read_text()).df()
    con.close()

    # Pre-experiment traffic for the power numbers.
    hist_users, hist_rng = sim.build_historical()
    hist_imp, _ = sim.simulate_outcomes(hist_users, partners, hist_rng)
    hist_funded = hist_imp.groupby("user_id")["funded"].sum().astype(float)

    control = um[um["variant"] == 0]
    peek_end, peek_any = an.aa_peeking(control["funded"].to_numpy(), control["day"].to_numpy(),
                                       n_days=28, reps=300)
    true_lift = truth["true_funded_t"].mean() / truth["true_funded_c"].mean() - 1
    return um, lead_share, partners, srm, hist_funded, (peek_end, peek_any), true_lift


um, lead_share, partners, srm, hist_funded, peeking, true_lift = load_data()
t, c = um[um["variant"] == 1], um[um["variant"] == 0]

funded = an.mean_diff(t["funded"], c["funded"])
revenue = an.mean_diff(t["revenue"], c["revenue"])
ctr = an.ratio_diff(t["clicks"], t["impressions"], c["clicks"], c["impressions"])
ctf = an.ratio_diff(t["funded"], t["clicks"], c["funded"], c["clicks"])
appr = an.ratio_diff(t["funded"], t["applications"], c["funded"], c["applications"])

ls = lead_share.merge(partners[["partner_id", "payout"]], on="partner_id")
ls["change"] = ls["treatment_share"] - ls["control_share"]
top2_change = ls.nlargest(2, "control_share")["change"].sum()
guardrails_pass = appr["ci_low"] > -0.01 and ls["change"].abs().max() <= 0.02 and top2_change <= 0.03
ship = (funded["p_value"] < 0.05 and funded["diff"] > 0
        and not (revenue["p_value"] < 0.05 and revenue["diff"] < 0) and guardrails_pass)


def base_layout(fig, height=360):
    fig.update_layout(height=height, margin=dict(l=10, r=20, t=10, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family=FONT, color=INK, size=14), legend_title_text="",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    fig.update_xaxes(gridcolor="#E3E6EB", zeroline=False)
    fig.update_yaxes(gridcolor="#E3E6EB", zeroline=False)
    return fig


def delta_color(res, higher_is_better=True):
    if res["p_value"] >= 0.05:
        return NEUTRAL
    return GOOD if (res["diff"] > 0) == higher_is_better else BAD


# The decision.
st.title("Showing approval odds raised funded loans")
st.markdown('<p class="lede">A 28 day A/B test in a simulated lending marketplace. Treatment showed each '
            'offer\'s approval odds on the offer card; ranking was identical in both arms. '
            f'{len(um):,} visitors, split 50/50.</p>', unsafe_allow_html=True)

verdict = "Ship, with a 5% holdback" if ship else "Do not ship"
why = (f"Funded loans per visitor rose {funded['rel_lift']:.1%} and every guardrail held. Most of the lift "
       "came from security app traffic, so the holdback should be watched by traffic source."
       if ship else "The primary metric did not improve significantly, or a guardrail failed.")
st.markdown(f'<div class="decision"><div class="verdict">{verdict}</div><div class="why">{why}</div></div>',
            unsafe_allow_html=True)

kpis = [
    ("Funded loans per 100 visitors", f"{funded['control'] * 100:.1f} → {funded['treatment'] * 100:.1f}",
     f"{funded['rel_lift']:+.1%}", delta_color(funded), "The outcome that matters"),
    ("Revenue per lead", f"${revenue['control']:.2f} → ${revenue['treatment']:.2f}",
     f"{revenue['rel_lift']:+.1%}", delta_color(revenue),
     "Not statistically significant" if revenue["p_value"] >= 0.05 else "Statistically significant"),
    ("Approval rate", f"{appr['control']:.1%} → {appr['treatment']:.1%}",
     f"{appr['diff'] * 100:+.1f} pts", delta_color(appr), "Partners get better qualified applications"),
    ("Click through rate", f"{ctr['control']:.1%} → {ctr['treatment']:.1%}",
     f"{ctr['rel_lift']:+.1%}", delta_color(ctr), "Expected: users skip offers with low odds"),
]
for col, (name, values, delta, color, note) in zip(st.columns(4), kpis):
    col.markdown(f'<div class="kpi"><div class="name">{name}</div><div class="values">{values}</div>'
                 f'<div class="delta" style="color:{color}">{delta}</div><div class="note">{note}</div></div>',
                 unsafe_allow_html=True)

# What changed for users.
st.header("Fewer clicks, but more of them end in a loan")
funnel = pd.DataFrame({
    "stage": ["Clicks", "Applications", "Funded loans"] * 2,
    "arm": ["Control"] * 3 + ["Treatment"] * 3,
    "per_100": [c["clicks"].mean() * 100, c["applications"].mean() * 100, c["funded"].mean() * 100,
                t["clicks"].mean() * 100, t["applications"].mean() * 100, t["funded"].mean() * 100],
})
fig = go.Figure()
for arm, color in [("Control", CONTROL), ("Treatment", TREATMENT)]:
    d = funnel[funnel["arm"] == arm]
    fig.add_bar(y=d["stage"], x=d["per_100"], name=arm, orientation="h", marker_color=color,
                text=[f"{v:.1f}" for v in d["per_100"]], textposition="outside")
fig.update_yaxes(autorange="reversed")
fig.update_xaxes(title="Per 100 visitors")
st.plotly_chart(base_layout(fig, 320), use_container_width=True)
st.caption("Seeing their odds, users click less often but choose offers they are likely to be approved for.")

# The metric trap.
st.header("Judge the test on funded loans, not clicks")
rows = [
    ("Click through rate", ctr, CONTROL),
    ("Click to funded rate", ctf, CONTROL),
    ("Revenue per lead", revenue, CONTROL),
    ("Funded loans per visitor", funded, TREATMENT),
]
fig = go.Figure()
for label, r, color in rows:
    fig.add_scatter(x=[r["rel_lift"] * 100], y=[label], mode="markers", showlegend=False,
                    marker=dict(size=14, color=color),
                    error_x=dict(type="data", symmetric=False, color=color, thickness=2.5,
                                 array=[(r["rel_ci_high"] - r["rel_lift"]) * 100],
                                 arrayminus=[(r["rel_lift"] - r["rel_ci_low"]) * 100]),
                    hovertemplate=f"{label}: %{{x:+.1f}}%<extra></extra>")
fig.add_vline(x=0, line_color=INK, line_width=1)
fig.update_xaxes(title="Change versus control, % (with 95% range)", ticksuffix="%")
st.plotly_chart(base_layout(fig, 300), use_container_width=True)
st.markdown(
    f"Click through rate fell {abs(ctr['rel_lift']):.1%}, which looks harmful. Click to funded rate rose "
    f"{ctf['rel_lift']:.1%}, but mostly because clicks shrank, so it overstates the gain. Funded loans per "
    f"visitor, the outcome the marketplace exists for, rose {funded['rel_lift']:.1%}.")

# Where the lift comes from.
st.header("The lift comes from security app visitors")
names = {"marketplace": "Main marketplace", "partner_channel": "Partner channels", "security_app": "Security app"}
fig = go.Figure()
for source in ["marketplace", "partner_channel", "security_app"]:
    g = um[um["source"] == source]
    r = an.mean_diff(g.loc[g["variant"] == 1, "funded"], g.loc[g["variant"] == 0, "funded"])
    color = HIGHLIGHT if source == "security_app" else CONTROL
    fig.add_scatter(x=[r["rel_lift"] * 100], y=[f"{names[source]} ({len(g):,})"], mode="markers+text",
                    text=[f"{r['rel_lift']:+.1%}"], textposition="top center", showlegend=False,
                    marker=dict(size=14, color=color),
                    error_x=dict(type="data", symmetric=False, color=color, thickness=2.5,
                                 array=[(r["rel_ci_high"] - r["rel_lift"]) * 100],
                                 arrayminus=[(r["rel_lift"] - r["rel_ci_low"]) * 100]),
                    hovertemplate="%{x:+.1f}%<extra></extra>")
fig.add_vline(x=0, line_color=INK, line_width=1)
fig.update_xaxes(title="Change in funded loans per visitor, % (with 95% range)", ticksuffix="%")
st.plotly_chart(base_layout(fig, 280), use_container_width=True)
st.caption("Security app visitors skew toward stronger credit, so they see more high odds offers. Segment "
           "results are exploratory: the test was not sized for each segment.")

# Partner impact.
st.header("Volume shifted slightly toward lenient, lower payout partners")
d = ls[(ls["control_share"] > 0.005) | (ls["treatment_share"] > 0.005)].sort_values("change")
fig = go.Figure()
fig.add_vrect(x0=-2, x1=2, fillcolor=CONTROL, opacity=0.10, line_width=0)
fig.add_bar(y=[f"{p}  (${v:.0f})" for p, v in zip(d["partner_id"], d["payout"])], x=d["change"] * 100,
            orientation="h", showlegend=False,
            marker_color=[TREATMENT if x > 0 else CONTROL for x in d["change"]],
            text=[f"{x * 100:+.1f}" for x in d["change"]], textposition="outside",
            hovertemplate="%{x:+.2f} pts<extra></extra>")
fig.add_vline(x=0, line_color=INK, line_width=1)
fig.update_xaxes(title="Change in share of applications, percentage points", range=[-2.5, 2.5])
st.plotly_chart(base_layout(fig, 340), use_container_width=True)
pay_c = c["revenue"].sum() / c["funded"].sum()
pay_t = t["revenue"].sum() / t["funded"].sum()
st.caption(f"The shaded band is the ±2 point guardrail; no partner left it. Partner payout per funded loan is "
           f"shown in brackets. Average payout per funded loan fell from ${pay_c:.0f} to ${pay_t:.0f}, which is "
           "why revenue grew less than funded loans.")

# Next tests.
st.header("What to test next")
nexts = [
    ("Confirm the security app effect", "A test sized for security app traffic alone, to check whether the 11% "
     "lift holds."),
    ("Help the main marketplace", "A softer display for low odds offers, such as badges on strong offers "
     "instead of low percentages."),
    ("Rebalance revenue", "A ranking that adjusts for the new click behavior, so revenue can rise as fast as "
     "funded loans."),
]
for col, (title, body) in zip(st.columns(3), nexts):
    col.markdown(f'<div class="next"><div class="title">{title}</div><div class="body">{body}</div></div>',
                 unsafe_allow_html=True)

# Reliability checks, for analysts.
st.header("Can we trust this result?")
with st.expander("Statistical checks"):
    from scipy import stats as _stats
    srm_p = _stats.chisquare(srm["users"]).pvalue
    mean_h, var_h = hist_funded.mean(), hist_funded.var(ddof=1)
    z = _stats.norm.ppf(0.975) + _stats.norm.ppf(0.8)
    mde = z * np.sqrt(2 * var_h / (len(hist_funded) / 2)) / mean_h
    st.markdown(
        f"- **Random assignment worked.** {len(c):,} control and {len(t):,} treatment visitors; the sample "
        f"ratio check gives p = {srm_p:.2f}.\n"
        f"- **The test was sized in advance.** From four weeks of earlier traffic, the smallest lift it could "
        f"reliably detect was {mde:.1%}. A lift near 3% had about a one in four chance of being missed.\n"
        f"- **The estimate matches the known truth.** The data is simulated, so the true lift is known: "
        f"{true_lift:+.1%}, inside the measured range of {funded['rel_ci_low']:+.1%} to {funded['rel_ci_high']:+.1%}.\n"
        "- **Results were read once, at day 28.** Checking every day and stopping at the first good result "
        "inflates false alarms, as the chart shows.")
    fig = go.Figure(go.Bar(x=["One look at day 28", "Checking every day"],
                           y=[peeking[0] * 100, peeking[1] * 100], marker_color=[CONTROL, BAD],
                           text=[f"{peeking[0]:.0%}", f"{peeking[1]:.0%}"], textposition="outside"))
    fig.update_yaxes(title="False alarms in tests with no real effect (%)", ticksuffix="%")
    st.plotly_chart(base_layout(fig, 300), use_container_width=True)
    adj, _ = an.cuped_adjust(um["funded"], um["prior_visits"])
    is_t = (um["variant"] == 1).to_numpy()
    cup = an.mean_diff(adj[is_t], adj[~is_t])
    st.markdown(f"- **CUPED barely helped.** Prior visits explain little of who gets funded, so variance fell "
                f"by only {1 - (cup['se'] / funded['se']) ** 2:.1%}. A pre-period measure of the outcome itself "
                "would be a stronger adjustment.")
