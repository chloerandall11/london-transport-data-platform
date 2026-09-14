import os
from datetime import date

import pandas as pd
import psycopg
import pytest

from london_transport_data_platform.config import DatabaseConfig
from london_transport_data_platform.load_postgres import (
    complete_pipeline_run,
    connect_database,
    create_pipeline_run,
    insert_dates,
    insert_journey_facts,
    insert_stations,
    load_journeys,
)


@pytest.fixture
def database_connection():
    password = os.getenv("POSTGRES_PASSWORD")
    database_name = os.getenv("POSTGRES_DB")
    database_user = os.getenv("POSTGRES_USER")

    if not password or not database_name or not database_user:
        pytest.skip("PostgreSQL environment is not configured")

    config = DatabaseConfig(
        host="localhost",
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=database_name,
        user=database_user,
        password=password,
    )

    try:
        with connect_database(config) as connection:
            yield connection
            connection.rollback()
    except psycopg.OperationalError:
        pytest.fail("Database connection failed", pytrace=False)


def test_database_connection(database_connection):
    with database_connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        result = cursor.fetchone()

    assert result == (1,)


def test_expected_tables_exist(database_connection):
    expected_tables = {"dim_station", "dim_date", "pipeline_run", "fact_journey"}
    with database_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public';
            """
        )
        result = cursor.fetchall()
        actual_tables = {row[0] for row in result}
    assert expected_tables.issubset(actual_tables)


def test_insert_stations(database_connection):
    test_data = {"station_id": [9001, 9002], "station_name": ["Station X", "Station Y"]}
    test_df = pd.DataFrame(data=test_data)
    insert_stations(database_connection, test_df)

    with database_connection.cursor() as cursor:
        cursor.execute(
            """
        SELECT station_id, station_name
        FROM dim_station
        WHERE station_id IN (9001, 9002)
        ORDER BY station_id;
        """
        )
        result = cursor.fetchall()

    assert result == [
        (9001, "Station X"),
        (9002, "Station Y"),
    ]

    insert_stations(database_connection, test_df)

    with database_connection.cursor() as cursor:
        cursor.execute(
            """
        SELECT station_id, station_name
        FROM dim_station
        WHERE station_id IN (9001, 9002)
        ORDER BY station_id;
        """
        )
        result = cursor.fetchall()

    assert result == [
        (9001, "Station X"),
        (9002, "Station Y"),
    ]


def test_insert_dates(database_connection):
    test_data = {
        "date_key": [date(2016, 2, 7)],
        "day_of_week": [7],
        "day_name": ["Sunday"],
        "month_number": [2],
        "year_number": [2016],
        "is_weekend": [True],
    }
    test_df = pd.DataFrame(data=test_data)

    insert_dates(database_connection, test_df)
    insert_dates(database_connection, test_df)

    with database_connection.cursor() as cursor:
        cursor.execute(
            """
        SELECT *
        FROM dim_date
        WHERE date_key = %s;
        """,
            (date(2016, 2, 7),),
        )
        result = cursor.fetchone()

    assert result == (
        date(2016, 2, 7),
        7,
        "Sunday",
        2,
        2016,
        True,
    )


def test_create_pipeline_run(database_connection):
    source_filename = "test_journeys.parquet"
    source_checksum = "a" * 64
    input_rows = 995
    run_id = create_pipeline_run(
        database_connection, source_filename, source_checksum, input_rows
    )

    assert isinstance(run_id, int)

    with database_connection.cursor() as cursor:
        cursor.execute(
            """
        SELECT source_filename, source_checksum, status, input_rows
        FROM pipeline_run
        WHERE pipeline_run_id = %s;
        """,
            (run_id,),
        )
        result = cursor.fetchone()

    assert result == (
        "test_journeys.parquet",
        "a" * 64,
        "running",
        995,
    )


def test_insert_journey_facts(database_connection):
    station_data = {
        "station_id": [9001, 9002],
        "station_name": ["Start Station", "End Station"],
    }
    station_df = pd.DataFrame(data=station_data)
    insert_stations(database_connection, station_df)
    insert_stations(database_connection, station_df)

    date_data = {
        "date_key": [date(2016, 2, 7)],
        "day_of_week": [7],
        "day_name": ["Sunday"],
        "month_number": [2],
        "year_number": [2016],
        "is_weekend": [True],
    }
    date_df = pd.DataFrame(data=date_data)
    insert_dates(database_connection, date_df)

    run_id = create_pipeline_run(
        database_connection,
        "journey-test.parquet",
        "b" * 64,
        1,
    )

    journey_data = {
        "rental_id": [1],
        "bike_id": [205],
        "pipeline_run_id": [run_id],
        "started_at": [pd.Timestamp("2016-02-07 13:00")],
        "date_key": [date(2016, 2, 7)],
        "start_station_id": [9001],
        "ended_at": [pd.Timestamp("2016-02-07 13:05")],
        "end_station_id": [9002],
        "duration_seconds": [300],
    }
    journey_df = pd.DataFrame(data=journey_data)

    insert_journey_facts(database_connection, journey_df)
    with database_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT rental_id, pipeline_run_id, bike_id, started_at, ended_at, start_station_id, end_station_id, date_key, duration_seconds
            FROM fact_journey
            WHERE rental_id = %s;
            """,
            (1,),
        )
        result = cursor.fetchone()

    assert result == (
        1,
        run_id,
        205,
        pd.Timestamp("2016-02-07 13:00:00"),
        pd.Timestamp("2016-02-07 13:05:00"),
        9001,
        9002,
        date(2016, 2, 7),
        300,
    )


def test_complete_pipeline_run(database_connection):
    source_filename = "test_journeys.parquet"
    source_checksum = "a" * 64
    input_rows = 995
    run_id = create_pipeline_run(
        database_connection,
        source_filename,
        source_checksum,
        input_rows,
    )

    complete_pipeline_run(database_connection, run_id, 990, 5)

    with database_connection.cursor() as cursor:
        cursor.execute(
            """
        SELECT status, completed_at, accepted_rows, rejected_rows
        FROM pipeline_run
        WHERE pipeline_run_id = %s;
        """,
            (run_id,),
        )
        completed_result = cursor.fetchone()

        assert completed_result[0] == "completed"
        assert completed_result[1] is not None
        assert completed_result[2:] == (990, 5)


def test_load_journeys(database_connection):
    journey_data = {
        "rental_id": [880001],
        "bike_id": [305],
        "started_at": [pd.Timestamp("2016-02-07 14:00:00")],
        "ended_at": [pd.Timestamp("2016-02-07 14:10:00")],
        "start_station_id": [9201],
        "start_station_name": ["Load Start"],
        "end_station_id": [9202],
        "end_station_name": ["Load End"],
        "journey_date": ["2016-02-07"],
        "duration_seconds": [600],
    }
    journey_df = pd.DataFrame(journey_data)

    run_id = load_journeys(
        database_connection,
        journey_df,
        "test-load.parquet",
        "c" * 64,
        2,
    )
    with database_connection.cursor() as cursor:
        cursor.execute(
            """
        SELECT status, input_rows, accepted_rows, rejected_rows
        FROM pipeline_run
        WHERE pipeline_run_id = %s;
        """,
            (run_id,),
        )
        completed_result = cursor.fetchone()

    assert completed_result[0] == "completed"
    assert completed_result[1:] == (3, 1, 2)
    assert isinstance(run_id, int)

    with database_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT pipeline_run_id, start_station_id, end_station_id, date_key
            FROM fact_journey
            WHERE rental_id = %s;
            """,
            (880001,),
        )
        journey_result = cursor.fetchone()

    assert journey_result == (
        run_id,
        9201,
        9202,
        date(2016, 2, 7),
    )

    second_run_id = load_journeys(
        database_connection,
        journey_df,
        "test-load.parquet",
        "c" * 64,
        2,
    )

    assert second_run_id != run_id

    with database_connection.cursor() as cursor:
        cursor.execute(
            """
        SELECT COUNT(*)
        FROM fact_journey
        WHERE rental_id = %s;
        """,
            (880001,),
        )
        journey_count = cursor.fetchone()[0]

    assert journey_count == 1


def test_failed_load_roll_back(database_connection):
    journey_data = {
        "rental_id": [880002],
        "bike_id": [305],
        "started_at": [pd.Timestamp("2016-02-07 14:00:00")],
        "ended_at": [pd.Timestamp("2016-02-07 14:10:00")],
        "start_station_id": [9301],
        "start_station_name": ["Rollback Start"],
        "end_station_id": [9302],
        "end_station_name": ["Rollback End"],
        "journey_date": ["2016-02-07"],
        "duration_seconds": [0],  # so it fails
    }
    journey_df = pd.DataFrame(journey_data)

    with (
        pytest.raises(psycopg.errors.CheckViolation),
        database_connection.transaction(),
    ):
        load_journeys(
            database_connection,
            journey_df,
            "failed-load.parquet",
            "e" * 64,
            0,
        )

    with database_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM pipeline_run
                WHERE source_filename = %s),
                (SELECT COUNT(*) FROM dim_station
                WHERE station_id IN (9301, 9302)),
                (SELECT COUNT(*) FROM fact_journey
                WHERE rental_id = 880002)
            """,
            ("failed-load.parquet",),
        )
        rollback_count = cursor.fetchone()

    assert rollback_count == (0, 0, 0)
