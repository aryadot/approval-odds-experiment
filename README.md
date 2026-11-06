# Approval Odds Display Test in a Lending Marketplace

Does showing approval odds on each offer card increase funded loans in a lending marketplace, without shifting too much volume toward a few partners?

This project runs one experiment end to end, the way a marketplace testing team would: hypothesis, metric design, power analysis, randomization checks, analysis, a ship decision, and a backlog of follow-up tests.

> **Result:** Ship, with a 5% holdback. Funded loans per user rose 2.3% (95% CI +0.1% to +4.6%) while CTR fell 7.5%, and all guardrails passed. The lift was concentrated in security app traffic (+11%). Full readout: [`docs/test_readout.md`](docs/test_readout.md).

## The marketplace

Users arrive from three traffic sources and see five ranked offers from ten lending partners. They may click an offer, complete an application, and be funded or declined.

- **Traffic sources:** the main marketplace, partner channels, and a security app channel, a new source of users who skew toward better credit.
- **Partners:** each has approval odds by credit tier, a payout per funded loan, and a brand appeal. Stricter partners pay more, so ranking for payout and ranking for approval pull against each other.
- **Ranking:** offers are ranked by expected revenue (approval odds × payout × brand appeal), so strict, high-payout partners appear mainly for strong-credit users.
- **The change being tested:** treatment shows each offer's approval odds. The ranking is identical in both arms, so any difference comes from the display alone.

The data is simulated. That's deliberate: because the true effect is known, the analysis can be checked against ground truth, which shows the methods recover the right answer. The simulation was calibrated (`notebooks/00_calibrate_simulation.ipynb`) so the true effects are realistic in size: a display change that lowers CTR by about 8% and raises funded loans per user by about 3%.

## Experiment design

The full design, including guardrail thresholds and the decision rule, is in [`docs/experiment_design.md`](docs/experiment_design.md). Thresholds follow standard marketplace testing practice and were fixed before the effect analysis.

| Role | Metric | Why |
|---|---|---|
| Primary | Funded loans per user | The outcome the marketplace exists for; cannot be inflated by a drop in clicks |
| Secondary | Revenue per lead | Payout earned per user who submits an inquiry |
| Diagnostic | CTR, click-to-funded rate | Explain *how* the effect happens |
| Guardrail | Approval rate | Partners should not see worse application quality |
| Guardrail | Partner lead share | Volume should not concentrate on a few partners |

**Two metric traps this test is built to expose:**
- **CTR alone is a trap.** Showing odds steers users away from low-odds offers, so clicks fall even when funded loans rise.
- **Click-to-funded rate alone is a trap too.** It's a ratio, and the treatment changes its denominator. Fewer clicks can push it up even if total funded loans stay flat. This is why funded loans per user is the primary metric.

## Methods

- Power analysis to size the test for the primary metric
- Sample ratio mismatch check on assignment
- Treatment effects with confidence intervals; delta method for ratio metrics
- CUPED variance reduction using pre-period visits
- A demonstration of how checking results daily (peeking) inflates false positives
- Effects by traffic source, including the new channel

## SQL

All metrics are computed in SQL from event tables (`users`, `impressions`, `partners`). Queries are written in PostgreSQL syntax and run locally on DuckDB, so they would carry over to a Postgres warehouse unchanged. Python is used only for the statistics.

## Project structure

```
src/simulate.py        marketplace simulation and DuckDB loading
docs/                  design document, test readout, figures
app/                   Streamlit readout dashboard
src/analysis.py        delta method, CUPED, peeking simulation
sql/                   metric queries (PostgreSQL syntax)
notebooks/             analysis, one notebook per step
data/                  local DuckDB file (not committed)
```

## How to run

```
pip install -r requirements.txt
jupyter notebook
```

Run the notebooks in order: `01_simulate_and_check_metrics`, `02_power_analysis`, `03_analysis`.

To open the dashboard:

```
python -m streamlit run app/streamlit_app.py
```

Run `00_calibrate_simulation.ipynb` first only if you want to see how the simulation settings were chosen.

## Steps

1. Simulation and SQL metric layer (done)
2. Experiment design and power analysis (done)
3. Analysis: effects, delta method, CUPED, peeking, segments (done)
4. Test readout with ship decision and follow-up backlog (`docs/test_readout.md`), plus a Streamlit dashboard (done)
