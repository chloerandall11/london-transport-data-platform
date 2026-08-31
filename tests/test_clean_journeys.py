import pandas as pd
from london_transport_data_platform.clean_journeys import (
    date_to_datetime,
    normalise_station_names,
    remove_nonpositive_durations,
    standardise_columns,
)

def test_remove_nonpositive_durations():
    test_data = {"duration_seconds": [0, -10, 60]}
    test_df = pd.DataFrame(data=test_data)
    output_df = remove_nonpositive_durations(test_df)
    assert output_df["duration_seconds"].tolist() == [60]
    assert len(test_df) == 3

def test_normalise_station_names():
    test_data = {"station_name": [" Moorfields , Moorgate", "Queen Mother Sports Centre, Victoria", "Belgrove Street , King's Cross "]}
    test_df = pd.DataFrame(data=test_data)
    output_series = normalise_station_names(test_df['station_name'])

    output_list = output_series.tolist()
    expected_names = [
        "Moorfields, Moorgate",
        "Queen Mother Sports Centre, Victoria",
        "Belgrove Street, King's Cross",
        ]
    assert output_list == expected_names


def test_date_to_datetime():
    test_data = {"start_date": ["07/02/2016 00:00", "13/02/2016 15:45",]}
    test_df = pd.DataFrame(data=test_data, dtype=str)
    output_series = date_to_datetime(test_df['start_date'])

    expected_dates = [
    pd.Timestamp("2016-02-07 00:00"),
    pd.Timestamp("2016-02-13 15:45"),]
    assert output_series.to_list() == expected_dates


def test_standardise_columns():
    test_df = pd.DataFrame(columns=["Rental Id", "Duration", "Start Date"])
    output_df = standardise_columns(test_df)
    assert output_df.columns.to_list() == ['rental_id', 'duration_seconds', 'started_at']

