-- Per-user metrics. The user is the unit of randomization, so it is also the unit of
-- analysis: every metric is aggregated to one row per user before comparing arms.
-- Written in PostgreSQL syntax; runs unchanged on DuckDB.
CREATE OR REPLACE VIEW user_metrics AS
SELECT u.user_id,
       u.variant,
       u.source,
       u.tier_name,
       u.prior_visits,
       u.day,
       COUNT(*)                                            AS impressions,
       SUM(i.clicked::int)                                 AS clicks,
       SUM(i.applied::int)                                 AS applications,
       SUM(i.funded::int)                                  AS funded,
       COALESCE(SUM(i.payout) FILTER (WHERE i.funded), 0)  AS revenue
FROM users u
JOIN impressions i ON i.user_id = u.user_id
GROUP BY u.user_id, u.variant, u.source, u.tier_name, u.prior_visits, u.day;
