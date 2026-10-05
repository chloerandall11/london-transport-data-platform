SELECT dd.date_key, dd.day_name, COUNT(fj.date_key) AS journey_count
FROM fact_journey AS fj
LEFT JOIN dim_date AS dd
ON dd.date_key = fj.date_key
GROUP BY dd.date_key, dd.day_name
ORDER BY dd.date_key ASC;