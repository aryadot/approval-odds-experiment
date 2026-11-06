# Test Readout: Approval Odds on Offer Cards

## Decision

**Ship**, with a 5% holdback to confirm the effect over time. Showing approval odds raised funded loans per user by 2.3%, and every guardrail passed. Most of the lift comes from security app traffic, so the holdback should be monitored by traffic source.

## What we tested

Treatment showed each offer's approval odds on the offer card; control did not. Ranking was identical in both arms. The test ran 28 days with a 50/50 user-level split: 99,926 control and 100,074 treatment users. Assignment was healthy (SRM p = 0.741).

## Results

| Metric | Control | Treatment | Relative lift (95% CI) | p-value |
|---|---|---|---|---|
| Funded loans per user (primary) | 0.1566 | 0.1603 | +2.33% (+0.09%, +4.63%) | 0.041 |
| Revenue per lead (secondary) | $28.74 | $29.25 | +1.78% (−0.65%, +4.26%) | 0.152 |
| CTR (diagnostic) | 15.14% | 14.00% | −7.50% (−8.40%, −6.59%) | < 0.001 |
| Click-to-funded rate (diagnostic) | 20.69% | 22.89% | +10.63% (+8.46%, +12.84%) | < 0.001 |

Because the data is simulated, the true effects are known: +3.45% on funded loans per user and +3.10% on revenue per lead. Both fall inside the 95% intervals. The funded estimate came in below the truth, as expected for a test with 75% power at this effect size.

## Why CTR alone was a trap

CTR fell 7.5%, because users skipped offers with low approval odds. Judged on CTR, the change looks harmful. Click-to-funded rate rose 10.6%, but mostly because its denominator, clicks, shrank, so judged on it alone the change looks four times better than it is. Funded loans per user, the outcome the marketplace exists for, rose 2.3%.

## Guardrails

| Guardrail | Result | Threshold | Pass |
|---|---|---|---|
| Approval rate change | +4.12 pts (37.66% → 41.78%), CI +3.42 to +4.81 | CI low > −1.0 pt | Yes |
| Largest partner share move | 0.85 pts | ≤ 2.0 pts | Yes |
| Top-two partner share change (P05, P04) | +1.63 pts | ≤ 3.0 pts | Yes |

Partners receive better-qualified applications, which is a benefit to them, not only a guardrail passed. Volume shifted slightly toward the two largest partners, within the limit but worth tracking after launch.

## Effects by traffic source (exploratory)

| Source | Users | Relative lift (95% CI) | p-value |
|---|---|---|---|
| Marketplace | 109,983 | −0.76% (−3.77%, +2.34%) | 0.627 |
| Partner channel | 59,973 | +2.80% (−1.26%, +7.03%) | 0.179 |
| Security app | 30,044 | +11.16% (+5.48%, +17.16%) | < 0.001 |

The lift is concentrated in security app traffic, whose users skew toward stronger credit and therefore see more high-odds offers. The security app result stays significant after a Bonferroni correction for three comparisons (threshold 0.017). The test was not powered per segment, so these results are hypotheses for follow-up rather than conclusions.

## Method notes

- **Power:** planned from pre-experiment traffic. The minimum detectable effect at 100,000 users per arm was 3.19%; a 3% lift needed about 5 weeks for 80% power. The test ran the planned 4 weeks, accepting 75% power.
- **CUPED:** pre-period visits correlate only 0.08 with funded loans, so CUPED reduced variance by 0.7% and barely changed the result. A covariate is only as useful as its correlation with the outcome; a pre-period measure of the outcome itself would do better.
- **Peeking:** in 500 A/A tests, checking significance daily raised the false positive rate from 4.4% to 26.8%. This test was analyzed once, at day 28.
- **Ratio metrics:** confidence intervals use the delta method, with the user as the unit. Here the naive standard error was only 2–3% too small, because every user saw exactly five offers; the gap grows when activity per user varies widely.

## Follow-up tests

1. **Confirm the security app effect.** Run a test pre-registered on security app traffic and powered for that segment, to check whether the 11% lift holds.
2. **Recover the marketplace segment.** Test a softer display for low-odds offers (for example, showing only "pre-qualified" badges on strong offers rather than low percentages) to see whether marketplace users can get the benefit without being steered away from offers entirely.
3. **Rebalance revenue.** Users now favor high-odds, lower-payout partners, so revenue rose less than funding. Test a ranking that adjusts for the new click behavior, to see whether revenue per lead can rise as fast as funded loans.
