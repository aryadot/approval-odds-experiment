"""
Statistical methods for the experiment analysis.

Metrics are computed in SQL (see sql/); these functions take the per-user results and
handle inference: confidence intervals, the delta method for ratio metrics, CUPED, and
the A/A peeking simulation.
"""
import numpy as np
from scipy import stats

Z = stats.norm.ppf(0.975)


def _summary(m_t, m_c, var_t, var_c):
    """Absolute difference with a 95% CI, relative lift with a log-scale delta-method CI, p-value."""
    diff = m_t - m_c
    se = np.sqrt(var_t + var_c)
    se_log = np.sqrt(var_t / m_t**2 + var_c / m_c**2)
    rel_lo, rel_hi = np.exp(np.log(m_t / m_c) + np.array([-Z, Z]) * se_log) - 1
    return {
        "control": m_c, "treatment": m_t, "diff": diff, "se": se,
        "ci_low": diff - Z * se, "ci_high": diff + Z * se,
        "rel_lift": m_t / m_c - 1, "rel_ci_low": rel_lo, "rel_ci_high": rel_hi,
        "p_value": 2 * stats.norm.sf(abs(diff) / se),
    }


def mean_diff(y_t, y_c):
    """Compare a per-user mean metric (e.g. funded loans per user) between arms."""
    y_t, y_c = np.asarray(y_t, float), np.asarray(y_c, float)
    return _summary(y_t.mean(), y_c.mean(), y_t.var(ddof=1) / len(y_t), y_c.var(ddof=1) / len(y_c))


def _ratio_and_var(a, b):
    """Ratio of sums sum(a)/sum(b) and its delta-method variance, with the user as the unit.

    Treating each impression or click as independent can understate the variance when a user's
    impressions are correlated. The delta method keeps the user as the unit of analysis.
    """
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = len(a)
    ma, mb = a.mean(), b.mean()
    cov = np.cov(a, b, ddof=1)
    var = (cov[0, 0] / mb**2 - 2 * ma * cov[0, 1] / mb**3 + ma**2 * cov[1, 1] / mb**4) / n
    return ma / mb, var


def ratio_diff(a_t, b_t, a_c, b_c):
    """Compare a ratio metric (e.g. click-to-funded = funded / clicks) between arms."""
    r_t, v_t = _ratio_and_var(a_t, b_t)
    r_c, v_c = _ratio_and_var(a_c, b_c)
    return _summary(r_t, r_c, v_t, v_c)


def naive_ratio_se(a_t, b_t, a_c, b_c):
    """Standard error of the difference if every denominator unit were treated as independent.

    Shown only for comparison with the delta method; this is the common mistake.
    """
    out = 0.0
    for a, b in [(a_t, b_t), (a_c, b_c)]:
        r = np.sum(a) / np.sum(b)
        out += r * (1 - r) / np.sum(b)
    return np.sqrt(out)


def cuped_adjust(y, x):
    """CUPED: remove the part of the outcome explained by a pre-period covariate.

    theta is estimated on both arms pooled. Because x is measured before assignment, the
    adjustment leaves the treatment effect unbiased while reducing its variance.
    """
    y, x = np.asarray(y, float), np.asarray(x, float)
    theta = np.cov(y, x, ddof=1)[0, 1] / x.var(ddof=1)
    return y - theta * (x - x.mean()), theta


def aa_peeking(y, day, n_days=28, reps=500, seed=0, batch=50):
    """False positive rate of A/A tests: one look at the end versus checking every day.

    Users with no true effect (one arm of the real test) are randomly split into two fake
    arms many times. For each split, a z-test runs on cumulative data after every day.
    Returns (rate significant at the final look, rate significant at any daily look).
    """
    rng = np.random.default_rng(seed)
    y = np.asarray(y, float)
    day = np.asarray(day, int)
    n = len(y)
    D = np.zeros((n, n_days))
    D[np.arange(n), day] = 1.0
    yD, y2D = y[:, None] * D, (y**2)[:, None] * D

    end_sig = np.zeros(reps, bool)
    any_sig = np.zeros(reps, bool)
    for start in range(0, reps, batch):
        b = min(batch, reps - start)
        in_a = rng.random((b, n)) < 0.5
        arm_stats = []
        for mask in (in_a, ~in_a):
            m = mask.astype(float)
            cnt = np.cumsum(m @ D, axis=1)
            s1 = np.cumsum(m @ yD, axis=1)
            s2 = np.cumsum(m @ y2D, axis=1)
            mean = s1 / cnt
            var = (s2 - cnt * mean**2) / (cnt - 1)
            arm_stats.append((mean, var / cnt))
        z = (arm_stats[0][0] - arm_stats[1][0]) / np.sqrt(arm_stats[0][1] + arm_stats[1][1])
        sig = np.abs(z) > Z
        end_sig[start:start + b] = sig[:, -1]
        any_sig[start:start + b] = sig.any(axis=1)
    return end_sig.mean(), any_sig.mean()
