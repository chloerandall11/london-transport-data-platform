import pandas as pd
import json
import psycopg
from london_transport_data_platform.config import PostgresLoadConfig, DatabaseConfig

def prepare_stations(df: pd.DataFrame) -> pd.DataFrame:
    df_copy_start = df[['start_station_id', 'start_station_name']].copy()
    df_copy_start = df_copy_start.rename(columns={'start_station_id': 'station_id', 'start_station_name': 'station_name'})

    df_copy_end = df[['end_station_id', 'end_station_name']].copy()
    df_copy_end = df_copy_end.rename(columns={'end_station_id': 'station_id', 'end_station_name': 'station_name'})

    output_df = pd.concat([df_copy_end, df_copy_start], ignore_index=True)
    output_df = output_df.drop_duplicates(subset=["station_id"])
    output_df = output_df.sort_values(by=["station_id"]).reset_index(drop=True)

    return output_df

def prepare_dates(df: pd.DataFrame) -> pd.DataFrame:
    df_copy = df[['journey_date']].copy()
    output_df = df_copy.drop_duplicates()
    output_df['journey_date'] = pd.to_datetime(output_df['journey_date'])
    output_df = output_df.sort_values(by=["journey_date"]).reset_index(drop=True)

    output_df['date_key'] = output_df['journey_date'].dt.date
    output_df["day_name"] = output_df["journey_date"].dt.day_name()
    output_df['day_of_week'] = output_df['journey_date'].dt.isocalendar().day.astype(int)
    output_df['month_number'] = output_df['journey_date'].dt.month.astype(int)
    output_df['year_number'] = output_df['journey_date'].dt.year.astype(int)
    output_df["is_weekend"] = output_df["day_of_week"] > 5
    output_df = output_df.drop(columns=['journey_date'])

    return output_df

def prepare_journey_facts(df: pd.DataFrame, pipeline_run_id: int) -> pd.DataFrame:
    df_copy = df.copy()

    df_copy['pipeline_run_id'] = pipeline_run_id
    df_copy['date_key'] = pd.to_datetime(df_copy['journey_date']).dt.date

    fact_cols = ["rental_id",
                 "pipeline_run_id",
                 "bike_id",
                 "started_at",
                 "ended_at",
                 "start_station_id",
                 "end_station_id",
                 "date_key",
                 "duration_seconds",]
    output_df = df_copy[fact_cols]
    return output_df


def insert_stations(connection: psycopg.Connection, station_df: pd.DataFrame) -> None:
    station_rows = list(
        station_df[["station_id", "station_name"]].itertuples(
            index=False,
            name=None,
        )
    )
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO dim_station (station_id, station_name)
            VALUES (%s, %s)
            ON CONFLICT (station_id) DO UPDATE
            SET station_name = EXCLUDED.station_name
            """,
            station_rows,
        )


def insert_dates(connection: psycopg.Connection, date_df: pd.DataFrame) -> None:
    date_rows = list(
        date_df[["date_key", "day_of_week", "day_name", "month_number", "year_number", "is_weekend"]].itertuples(
            index=False,
            name=None,
        )
    )
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO dim_date (
            date_key,
            day_of_week,
            day_name,
            month_number,
            year_number,
            is_weekend
                )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (date_key) DO UPDATE
            SET day_of_week = EXCLUDED.day_of_week,
            day_name = EXCLUDED.day_name,
            month_number = EXCLUDED.month_number,
            year_number = EXCLUDED.year_number,
            is_weekend = EXCLUDED.is_weekend
            """,
            date_rows,
        )


def create_pipeline_run(connection: psycopg.Connection, source_filename: str, source_checksum: str, input_rows: int) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO pipeline_run (
                source_filename,
                source_checksum,
                status,
                input_rows
            )
            VALUES (%s, %s, 'running', %s)
            RETURNING pipeline_run_id;
            """, (source_filename, source_checksum, input_rows),)
        result = cursor.fetchone()

    if result is None:
        raise RuntimeError("Failed to create pipeline run")

    return result[0]


def insert_journey_facts(connection: psycopg.Connection, journey_df: pd.DataFrame) -> None:
    journey_rows = list(
        journey_df[
            [
                "rental_id",
                "pipeline_run_id",
                "bike_id",
                "started_at",
                "ended_at",
                "start_station_id",
                "end_station_id",
                "date_key",
                "duration_seconds",
            ]
        ].itertuples(index=False, name=None)
    )

    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO fact_journey (
                rental_id,
                pipeline_run_id,
                bike_id,
                started_at,
                ended_at,
                start_station_id,
                end_station_id,
                date_key,
                duration_seconds
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (rental_id) DO UPDATE
            SET pipeline_run_id = EXCLUDED.pipeline_run_id,
                bike_id = EXCLUDED.bike_id,
                started_at = EXCLUDED.started_at,
                ended_at = EXCLUDED.ended_at,
                start_station_id = EXCLUDED.start_station_id,
                end_station_id = EXCLUDED.end_station_id,
                date_key = EXCLUDED.date_key,
                duration_seconds = EXCLUDED.duration_seconds
            """,
            journey_rows,
        )

def complete_pipeline_run(connection: psycopg.Connection, pipeline_run_id: int, accepted_rows: int, rejected_rows: int,) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE pipeline_run
            SET status = 'completed',
                completed_at = CURRENT_TIMESTAMP,
                accepted_rows = %s,
                rejected_rows = %s
            WHERE pipeline_run_id = %s
            """,
            (accepted_rows, rejected_rows, pipeline_run_id),
        )
    
def load_journeys(connection: psycopg.Connection, journey_df: pd.DataFrame, source_filename: str, source_checksum: str | None, rejected_rows: int) -> int:
    accepted_rows = len(journey_df)
    input_rows = accepted_rows + rejected_rows

    run_id = create_pipeline_run(
        connection,
        source_filename,
        source_checksum,
        input_rows,
    )

    station_df = prepare_stations(journey_df)
    date_df = prepare_dates(journey_df)
    fact_df = prepare_journey_facts(journey_df, run_id)

    insert_stations(connection, station_df)
    insert_dates(connection, date_df)
    insert_journey_facts(connection, fact_df)

    complete_pipeline_run(
    connection,
    run_id,
    accepted_rows,
    rejected_rows,
    )

    return run_id


def read_load_inputs(config: PostgresLoadConfig) -> tuple[pd.DataFrame, str, str, int]:
    accepted_df = pd.read_parquet(config.parquet_input_path)
    rejected_df = pd.read_csv(config.rejected_input_path)

    metadata_text = config.metadata_path.read_text(encoding="utf-8")
    metadata = json.loads(metadata_text)

    return (accepted_df, metadata["filename"], metadata["checksum_sha256"], len(rejected_df))


def connect_database(config: DatabaseConfig) -> psycopg.Connection:
    return psycopg.connect(
        host=config.host,
        port=config.port,
        dbname=config.dbname,
        user=config.user,
        password=config.password)


def load_processed_journeys(connection: psycopg.Connection, config: PostgresLoadConfig) -> int:
    results = read_load_inputs(config)
    journey_df, source_filename, source_checksum, rejected_rows = results
    run_id = load_journeys(connection, journey_df, source_filename, source_checksum, rejected_rows)

    return run_id