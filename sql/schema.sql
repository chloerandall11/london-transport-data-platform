CREATE TABLE IF NOT EXISTS dim_station (
    station_id BIGINT PRIMARY KEY,
    station_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key DATE PRIMARY KEY,
    day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    day_name TEXT NOT NULL,
    month_number SMALLINT NOT NULL CHECK (month_number BETWEEN 1 AND 12),
    year_number SMALLINT NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS pipeline_run (
    pipeline_run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_filename TEXT NOT NULL,
    source_checksum CHAR(64),
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    input_rows BIGINT CHECK (input_rows >= 0),
    accepted_rows BIGINT CHECK (accepted_rows >= 0),
    rejected_rows BIGINT CHECK (rejected_rows >= 0)
);

CREATE TABLE IF NOT EXISTS fact_journey (
    rental_id BIGINT PRIMARY KEY,
    pipeline_run_id BIGINT NOT NULL REFERENCES pipeline_run(pipeline_run_id),
    bike_id BIGINT NOT NULL,
    started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    ended_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    start_station_id BIGINT NOT NULL REFERENCES dim_station(station_id),
    end_station_id BIGINT NOT NULL REFERENCES dim_station(station_id),
    date_key DATE NOT NULL REFERENCES dim_date(date_key),
    duration_seconds INTEGER NOT NULL CHECK (duration_seconds > 0),
    CHECK (ended_at > started_at)
);

CREATE INDEX IF NOT EXISTS idx_fact_journey_date_key
    ON fact_journey (date_key);

CREATE INDEX IF NOT EXISTS idx_fact_journey_start_station
    ON fact_journey (start_station_id);

CREATE INDEX IF NOT EXISTS idx_fact_journey_end_station
    ON fact_journey (end_station_id);

CREATE INDEX IF NOT EXISTS idx_fact_journey_started_at
    ON fact_journey (started_at);