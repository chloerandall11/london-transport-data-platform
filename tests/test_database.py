import os
import psycopg
import pytest


@pytest.fixture
def database_connection():
    password = os.getenv("POSTGRES_PASSWORD")

    if password is None:
        pytest.skip("PostgreSQL environment is not configured")

    try:
        with psycopg.connect(
            host="localhost",
            port=os.getenv("POSTGRES_PORT"),
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=password,
        ) as connection:
            yield connection
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
