SELECT
    CASE
        WHEN duration_seconds < 300 THEN 'Under 5 minutes'
        WHEN duration_seconds < 900 THEN '5 to under 15 minutes'
        WHEN duration_seconds < 1800 THEN '15 to under 30 minutes'
        WHEN duration_seconds < 3600 THEN '30 to under 60 minutes'
        ELSE '60 minutes or longer'
    END AS duration_band,
    COUNT(*) AS journey_count
FROM fact_journey
GROUP BY duration_band
ORDER BY journey_count DESC;