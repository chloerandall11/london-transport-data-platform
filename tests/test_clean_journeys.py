import pandas as pd
import pytest
from london_transport_data_platform.clean_journeys import (
    date_to_datetime,
    normalise_station_names,
    remove_nonpositive_durations,
    standardise_columns,
    load_journeys,
    validate_required_columns,
    invalid_rental_id_mask,
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
    assert test_df.columns.tolist() == ["Rental Id", "Duration", "Start Date",]

def test_load_journeys(tmp_path):
    test_data = {"Rental Id": [1, 2],"Duration": [60, 120],}
    test_df = pd.DataFrame(data=test_data)

    csv_path = tmp_path / "test_load_journeys.csv"
    test_df.to_csv(csv_path, index=False)
    output_df = load_journeys(csv_path)

    pd.testing.assert_frame_equal(output_df, test_df)

def test_validate_required_columns():
    test_df = pd.DataFrame(columns=["Rental Id", "Bike Id", "End Date", "EndStation Id", "EndStation Name", "Start Date", "StartStation Id", "StartStation Name",])

    with pytest.raises(ValueError, match="Missing required columns: Duration",):
        validate_required_columns(test_df)

def test_invalid_rental_id_mask_null():
    test_data = {"rental_id": [1, 2, None]}
    test_df = pd.DataFrame(data=test_data)

    boolean_mask = invalid_rental_id_mask(test_df)

    assert boolean_mask.tolist() == [False, False, True]

def test_invalid_rental_id_mask_duplicate():
    test_data = {"rental_id": [1, 2, 2, 3]}
    test_df = pd.DataFrame(data=test_data)

    boolean_mask = invalid_rental_id_mask(test_df)

    assert boolean_mask.tolist() == [False, True, True, False]
