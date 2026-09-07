import json
from datetime import date

import pandas as pd

from london_transport_data_platform.config import PostgresLoadConfig
from london_transport_data_platform.load_postgres import (
    prepare_dates,
    prepare_journey_facts,
    prepare_stations,
    read_load_inputs,
)


def test_prepare_stations():
    test_data = {
        "start_station_id": [1, 2],
        "end_station_id": [2, 3],
        "start_station_name": ["Station A", "Station B"],
        "end_station_name": ["Station B", "Station C"],
    }
    test_df = pd.DataFrame(data=test_data)
    output_df = prepare_stations(test_df)

    assert output_df.to_dict(orient="records") == [
        {"station_id": 1, "station_name": "Station A"},
        {"station_id": 2, "station_name": "Station B"},
        {"station_id": 3, "station_name": "Station C"},
    ]


def test_prepare_dates():
    test_data = {"journey_date": ["2016-02-08", "2016-02-07", "2016-02-07"]}
    test_df = pd.DataFrame(data=test_data)
    output_df = prepare_dates(test_df)

    assert output_df.to_dict(orient="records") == [
        {
            "date_key": date(2016, 2, 7),
            "day_of_week": 7,
            "day_name": "Sunday",
            "month_number": 2,
            "year_number": 2016,
            "is_weekend": True,
        },
        {
            "date_key": date(2016, 2, 8),
            "day_of_week": 1,
            "day_name": "Monday",
            "month_number": 2,
            "year_number": 2016,
            "is_weekend": False,
        },
    ]


def test_prepare_journey_facts():
    test_data = {
        "rental_id": [1],
        "bike_id": [205],
        "started_at": [pd.Timestamp("2016-02-08 13:00")],
        "journey_date": ["2016-02-08"],
        "start_station_id": [15],
        "start_station_name": ["Station A"],
        "ended_at": [pd.Timestamp("2016-02-08 13:05")],
        "end_station_id": [22],
        "end_station_name": ["Station B"],
        "duration_seconds": [300],
    }
    test_df = pd.DataFrame(data=test_data)

    output_df = prepare_journey_facts(test_df, pipeline_run_id=42)

    assert output_df.to_dict(orient="records") == [
        {
            "rental_id": 1,
            "pipeline_run_id": 42,
            "bike_id": 205,
            "started_at": pd.Timestamp("2016-02-08 13:00"),
            "ended_at": pd.Timestamp("2016-02-08 13:05"),
            "start_station_id": 15,
            "end_station_id": 22,
            "date_key": date(2016, 2, 8),
            "duration_seconds": 300,
        }
    ]


def test_read_load_inputs(tmp_path):
    test_data_acc = {"rental_id": [1, 2]}
    test_df_acc = pd.DataFrame(data=test_data_acc)
    output_path_acc = tmp_path / "accepted.parquet"
    test_df_acc.to_parquet(output_path_acc, index=False)

    test_data_rej = {"rejection_reason": ["invalid duration", "invalid station name"]}
    test_df_rej = pd.DataFrame(data=test_data_rej)
    output_path_rej = tmp_path / "rejected.csv"
    test_df_rej.to_csv(output_path_rej, index=False)

    test_data_meta = {"filename": "source.csv", "checksum_sha256": "d" * 64}
    output_path_meta = tmp_path / "source.metadata.json"
    json_meta = json.dumps(test_data_meta)
    output_path_meta.write_text(json_meta, encoding="utf-8")

    config = PostgresLoadConfig(
        parquet_input_path=output_path_acc,
        rejected_input_path=output_path_rej,
        metadata_path=output_path_meta,
    )

    accepted_df, filename, checksum, rejected_rows = read_load_inputs(config)

    pd.testing.assert_frame_equal(accepted_df, test_df_acc)
    assert filename == "source.csv"
    assert checksum == "d" * 64
    assert rejected_rows == 2
