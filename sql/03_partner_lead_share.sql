-- Guardrail: each partner's share of applications (leads) within each arm.
-- A large shift toward a few partners would mean the change concentrates volume,
-- which can strain partner caps and relationships even if total funding rises.
SELECT i.partner_id,
       COUNT(*) FILTER (WHERE u.variant = 0) * 1.0
         / SUM(COUNT(*) FILTER (WHERE u.variant = 0)) OVER ()   AS control_share,
       COUNT(*) FILTER (WHERE u.variant = 1) * 1.0
         / SUM(COUNT(*) FILTER (WHERE u.variant = 1)) OVER ()   AS treatment_share
FROM impressions i
JOIN users u ON u.user_id = i.user_id
WHERE i.applied
GROUP BY i.partner_id
ORDER BY i.partner_id;
