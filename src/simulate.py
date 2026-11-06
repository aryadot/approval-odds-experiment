"""
Simulated lending marketplace for the approval-odds display experiment.

Users arrive from three traffic sources and see five ranked offers from ten lending
partners. Control sees the offers as usual; treatment sees each offer's approval odds.
The behavior model builds in a known effect, and the true expected outcome under both
arms is computed for every user, so the analysis can be checked against ground truth.
"""
import numpy as np
import pandas as pd

SOURCES = ["marketplace", "partner_channel", "security_app"]
SOURCE_P = [0.55, 0.30, 0.15]

# Credit-tier mix per source: excellent, good, fair, poor.
# The security_app channel (standing in for Norton Money traffic) skews toward better credit.
TIER_MIX = {
    "marketplace": [0.15, 0.35, 0.30, 0.20],
    "partner_channel": [0.20, 0.35, 0.28, 0.17],
    "security_app": [0.30, 0.40, 0.20, 0.10],
}
TIER_NAMES = ["excellent", "good", "fair", "poor"]

# Approval probability by tier before each partner's strictness multiplier is applied.
BASE_APPROVAL = np.array([0.65, 0.42, 0.20, 0.07])

# How strongly partner strictness bites at each tier. Strict partners (multiplier < 1) lose
# more approval for weaker credit, and lenient partners gain relatively, so the best offers
# differ by credit tier, as in a real marketplace.
TIER_GAMMA = np.array([0.5, 1.0, 1.5, 2.0])

K = 5                # offers shown per user
APPLY_RATE = 0.55    # share of clicks that become completed applications

# Click model parameters. In treatment, users react asymmetrically to seeing odds: offers
# below ODDS_PIVOT approval lose clicks at rate ODDS_DOWN, offers above it gain clicks at the
# smaller rate ODDS_UP (low odds deter more than high odds encourage). Values were chosen with
# notebooks/00_calibrate_simulation.ipynb to give a realistic pattern: CTR down about 8%,
# funded loans per user up about 3%.
CLICK_INTERCEPT = -1.6
POSITION_DECAY = 0.35
ODDS_PIVOT = 0.40
ODDS_UP = 1.0
ODDS_DOWN = 2.0
RANK_NOISE = 0.1


def _make_users(rng, n_users, n_days):
    """Generate users with traffic source, credit tier, day, assignment, intent and pre-period visits."""
    users = pd.DataFrame({"user_id": np.arange(n_users)})
    users["source"] = rng.choice(SOURCES, n_users, p=SOURCE_P)
    tiers = np.zeros(n_users, dtype=int)
    for s in SOURCES:
        m = (users["source"] == s).to_numpy()
        tiers[m] = rng.choice(4, m.sum(), p=TIER_MIX[s])
    users["tier"] = tiers
    users["tier_name"] = np.array(TIER_NAMES)[tiers]
    users["day"] = rng.integers(0, n_days, n_users)
    users["variant"] = rng.integers(0, 2, n_users)       # 0 = control, 1 = treatment
    users["intent"] = rng.normal(0, 0.5, n_users)        # unobserved; never stored in the warehouse
    # Pre-period visits are correlated with intent, which is what makes CUPED useful later.
    users["prior_visits"] = rng.poisson(np.exp(0.3 + users["intent"].to_numpy()))
    return users


def build_marketplace(n_users=200_000, n_days=28, n_partners=10, seed=42):
    """Create users (with random 50/50 assignment) and lending partners."""
    rng = np.random.default_rng(seed)
    users = _make_users(rng, n_users, n_days)

    # Stricter partners (lower multiplier) pay more per funded loan, so ranking for payout
    # and ranking for approval pull in opposite directions, as in a real marketplace.
    mult = rng.uniform(0.6, 1.3, n_partners)
    partners = pd.DataFrame({
        "partner_id": [f"P{i:02d}" for i in range(n_partners)],
        "approval_mult": mult,
        "payout": np.round(120 + 280 * (1.3 - mult) / 0.7 + rng.normal(0, 20, n_partners)),
        "appeal": rng.normal(0, 0.3, n_partners),
    })
    return users, partners, rng


def build_historical(n_users=200_000, n_days=28, seed=7):
    """Pre-experiment traffic: same marketplace, everyone sees the current experience.

    Used for the power analysis, which must be based on data available before the test.
    Pass the experiment's partners table to simulate_outcomes so the marketplace matches.
    """
    rng = np.random.default_rng(seed)
    users = _make_users(rng, n_users, n_days)
    users["variant"] = 0
    return users, rng


def approval_matrix(tiers, mult):
    """Approval probability for every user-partner pair, given each user's credit tier."""
    gamma = TIER_GAMMA[tiers][:, None]
    return np.clip(BASE_APPROVAL[tiers][:, None] * mult[None, :] ** gamma, 0, 0.95)


def simulate_outcomes(users, partners, rng):
    """Rank offers, then simulate clicks, applications and funding for each user.

    Returns one row per offer impression, plus each user's true expected outcomes
    under both arms (ground truth for checking the analysis).
    """
    tiers = users["tier"].to_numpy()
    mult = partners["approval_mult"].to_numpy()
    appeal = partners["appeal"].to_numpy()
    payout = partners["payout"].to_numpy()

    # Ranking is by expected revenue (approval x payout x appeal, with noise), the way a
    # yield-focused marketplace ranks. It is the same in both arms, so any difference
    # between arms comes only from showing the odds.
    approval = approval_matrix(tiers, mult)
    score = (approval * payout[None, :] * np.exp(appeal)[None, :]
             * rng.lognormal(0, RANK_NOISE, approval.shape))
    shown = np.argsort(-score, axis=1)[:, :K]
    s_appr = np.take_along_axis(approval, shown, axis=1)
    s_appeal = appeal[shown]
    s_payout = payout[shown]

    pos = np.arange(K)[None, :]
    intent = users["intent"].to_numpy()[:, None]

    def click_prob(treated):
        odds_shift = (ODDS_UP * np.clip(s_appr - ODDS_PIVOT, 0, None)
                      - ODDS_DOWN * np.clip(ODDS_PIVOT - s_appr, 0, None))
        logit = CLICK_INTERCEPT - POSITION_DECAY * pos + s_appeal + intent + treated * odds_shift
        return 1 / (1 + np.exp(-logit))

    p0, p1 = click_prob(0), click_prob(1)
    truth = pd.DataFrame({
        "user_id": users["user_id"].to_numpy(),
        "true_funded_c": (p0 * APPLY_RATE * s_appr).sum(1),
        "true_funded_t": (p1 * APPLY_RATE * s_appr).sum(1),
        "true_revenue_c": (p0 * APPLY_RATE * s_appr * s_payout).sum(1),
        "true_revenue_t": (p1 * APPLY_RATE * s_appr * s_payout).sum(1),
        "true_clicks_c": p0.sum(1),
        "true_clicks_t": p1.sum(1),
    })

    treated = users["variant"].to_numpy()[:, None] == 1
    p = np.where(treated, p1, p0)
    clicks = rng.random(p.shape) < p
    applied = clicks & (rng.random(p.shape) < APPLY_RATE)
    funded = applied & (rng.random(p.shape) < s_appr)

    n = len(users)
    impressions = pd.DataFrame({
        "user_id": np.repeat(users["user_id"].to_numpy(), K),
        "position": np.tile(np.arange(1, K + 1), n),
        "partner_id": partners["partner_id"].to_numpy()[shown.ravel()],
        "approval_prob": s_appr.ravel().round(4),
        "payout": s_payout.ravel(),
        "clicked": clicks.ravel(),
        "applied": applied.ravel(),
        "funded": funded.ravel(),
    })
    return impressions, truth


def load_to_duckdb(con, users, partners, impressions, truth, prefix=""):
    """Store the simulation as warehouse-style tables.

    Only observable columns go into the users table (intent stays out). Ground truth
    is kept in its own table so it is never mixed into the analysis by accident.
    Use prefix="hist_" to store pre-experiment traffic alongside the experiment tables.
    """
    tables = {
        f"{prefix}users": users[["user_id", "source", "tier_name", "day", "variant", "prior_visits"]],
        f"{prefix}partners": partners,
        f"{prefix}impressions": impressions,
        f"{prefix}ground_truth": truth,
    }
    if prefix == "":
        con.execute("DROP VIEW IF EXISTS user_metrics")
    for name, df in tables.items():
        con.register(f"{name}_df", df)
        con.execute(f"DROP TABLE IF EXISTS {name}")
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM {name}_df")
        con.unregister(f"{name}_df")
