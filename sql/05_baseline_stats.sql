-- Baseline statistics for the power analysis, computed from pre-experiment (historical)
-- traffic. Power must be planned from data available before the test starts, so this
-- query reads the hist_ tables, not the experiment tables.
WITH per_user AS (
    SELECT u.user_id,
           u.prior_visits,
           SUM(i.funded::int)::double precision                                  AS funded,
           COALESCE(SUM(i.payout) FILTER (WHERE i.funded), 0)::double precision  AS revenue
    FROM hist_users u
    JOIN hist_impressions i ON i.user_id = u.user_id
    GROUP BY u.user_id, u.prior_visits
)
SELECT COUNT(*)                                   AS users,
       COUNT(*) * 1.0 / 28                        AS users_per_day,
       AVG(funded)                                AS funded_mean,
       VAR_SAMP(funded)                           AS funded_var,
       AVG(revenue)                               AS revenue_mean,
       VAR_SAMP(revenue)                          AS revenue_var,
       CORR(funded, prior_visits)                 AS funded_prior_corr,
       CORR(revenue, prior_visits)                AS revenue_prior_corr
FROM per_user;
