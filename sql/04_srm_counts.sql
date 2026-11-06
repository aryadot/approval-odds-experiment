-- Sample ratio mismatch check input: users per arm. With a 50/50 split, a large
-- imbalance signals broken assignment or logging, and the test results can't be trusted.
SELECT variant, COUNT(*) AS users
FROM users
GROUP BY variant
ORDER BY variant;
