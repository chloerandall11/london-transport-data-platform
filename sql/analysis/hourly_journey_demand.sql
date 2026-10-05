SELECT  COUNT(*) AS journey_count, EXTRACT(hour from started_at) as journey_hour
FROM fact_journey
GROUP BY journey_hour
ORDER BY journey_hour ASC;