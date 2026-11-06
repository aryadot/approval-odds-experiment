# Experiment Design: Approval Odds on Offer Cards

Written before the effect analysis. Guardrail thresholds and the decision rule follow standard marketplace testing practice and are fixed here, so the readout is judged against criteria set in advance.

## Hypothesis

Showing each offer's approval odds helps users choose offers they are likely to be approved for. This will lower clicks but raise funded loans per user, because fewer applications end in a decline.

## Setup

| | |
|---|---|
| Unit of randomization | User |
| Split | 50/50, control vs. treatment |
| Control | Offer cards as today |
| Treatment | Offer cards show approval odds |
| Ranking | Identical in both arms |
| Planned duration | 28 days (four full weeks, to cover weekly cycles) |
| Analysis | One analysis at the end of the test; no early stopping |

## Metrics

| Role | Metric | Definition |
|---|---|---|
| Primary | Funded loans per user | Funded loans / users |
| Secondary | Revenue per lead | Partner payouts / users |
| Diagnostic | CTR | Clicks / offer impressions |
| Diagnostic | Click-to-funded rate | Funded loans / clicks |
| Guardrail | Approval rate | Funded loans / applications |
| Guardrail | Partner lead share | Each partner's share of applications |

## Guardrail thresholds

- **Approval rate:** must not fall by more than 1 percentage point.
- **Partner lead share:** no partner's share may change by more than 2 percentage points, and the combined share of the two largest partners may not rise by more than 3 points.
- **Sample ratio mismatch:** if the chi-square test of the 50/50 split gives p < 0.001, the results are not trusted and the test is investigated.

## Decision rule

Ship if all of the following hold:
1. Funded loans per user increases, significant at α = 0.05 (two-sided).
2. Revenue per lead does not decrease significantly.
3. All guardrails pass.

If the primary metric is not significant, do not ship; consider a follow-up test with a stronger treatment or more traffic.

## Power

From four weeks of pre-experiment traffic (`notebooks/02_power_analysis.ipynb`):

- Baseline funded loans per user: 0.1549 (variance 0.1556), about 7,140 users per day.
- Minimum detectable effect at the planned 100,000 users per arm (80% power, α = 0.05): 3.19% relative.
- Sample size for a 3% relative lift: 113,064 users per arm, about 32 days (5 full weeks).
- Power to detect a 3% lift at 28 days: 75%.
- CUPED with pre-period visits: correlation 0.08 with the outcome, so variance falls by only 0.7%. Pre-period visits are a weak covariate for a rare outcome like funding.

The test runs for the planned 28 days, which is slightly underpowered for a 3% lift. A lift near 3% has roughly a one-in-four chance of being missed, and that risk is stated in the readout.
