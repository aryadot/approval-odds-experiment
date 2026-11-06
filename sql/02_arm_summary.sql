-- Headline metrics by arm.
-- Primary: funded loans per user (cannot be inflated by a drop in clicks).
-- Secondary: revenue per lead (every user is a lead, so this is revenue per user).
-- Diagnostics: CTR and click-to-funded rate, which explain how the effect happens.
-- Guardrail: approval rate (funded / applications).
SELECT CASE variant WHEN 0 THEN 'control' ELSE 'treatment' END  AS arm,
       COUNT(*)                                                 AS users,
       AVG(funded)                                              AS funded_per_user,
       AVG(revenue)                                             AS revenue_per_lead,
       SUM(clicks) * 1.0 / SUM(impressions)                     AS ctr,
       SUM(funded) * 1.0 / NULLIF(SUM(clicks), 0)               AS click_to_funded,
       SUM(funded) * 1.0 / NULLIF(SUM(applications), 0)         AS approval_rate
FROM user_metrics
GROUP BY variant
ORDER BY variant;
