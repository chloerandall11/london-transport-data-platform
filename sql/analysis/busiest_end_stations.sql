SELECT COUNT(fj.end_station_id) AS journey_count, fj.end_station_id, ds.station_name 
FROM fact_journey AS fj
LEFT JOIN dim_station AS ds
ON fj.end_station_id = ds.station_id
GROUP BY fj.end_station_id, ds.station_name
ORDER BY journey_count DESC
LIMIT 10;