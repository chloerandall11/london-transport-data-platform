import pandas as pd
import pytest
from london_transport_data_platform.clean_journeys import (
    date_to_datetime,
    normalise_station_names,
    standardise_columns,
    load_journeys,
    validate_required_columns,
    invalid_rental_id_mask,
    invalid_duration_mask,
    invalid_timestamp_mask,
    invalid_station_id_mask,
    add_rejection_reason,
    add_journey_rejection_reasons,
    separate_accepted_rejected_rows,
    add_journey_date,
)

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

def test_invalid_duration_mask():
    test_data = {"duration_seconds": [37, 0, None, -10, 107, 'not-a-duration']}
    test_df = pd.DataFrame(data=test_data)
    boolean_mask = invalid_duration_mask(test_df)

    assert boolean_mask.tolist() == [False, True, True, True, False, True]


def test_invalid_timestamp_mask():
    test_data = {"started_at": ["07/02/2016 10:00",
                                "07/02/2016 14:12",
                                "08/02/2016 00:01",
                                "08/02/2016 00:07",
                                None,
                                "18/02/2016 18:02"],
                "ended_at": ["07/02/2016 10:10",
                             "07/02/2016 10:30",
                             "07/02/2016 23:01",
                             "08/02/2016 00:07",
                             "07/02/2016 13:06",
                             None]}
    test_df = pd.DataFrame(data=test_data)

    test_df['started_at'] = pd.to_datetime(test_df['started_at'], format="%d/%m/%Y %H:%M")
    test_df['ended_at'] = pd.to_datetime(test_df['ended_at'], format="%d/%m/%Y %H:%M")
    boolean_mask = invalid_timestamp_mask(test_df)

    assert boolean_mask.tolist() == [False, True, True, True, True, True]

def test_invalid_station_id_mask():
    test_data = {"end_station_id": [None, 2, -2, 6, 10, 0, 13, 3, 6, 11, 2.5, 'station-id', '12'],
                "start_station_id": [1, 2, 3, 6, 8, 7, 7, None, 0, -3, 5, 7, 22]}
    test_df = pd.DataFrame(data=test_data)

    boolean_mask = invalid_station_id_mask(test_df)

    assert boolean_mask.tolist() == [True, False, True, False, False, True, False, True, True, True, True, True, False]


def test_add_rejection_reason():
    test_data = {"end_station_id": [None, 2, 5],
                "start_station_id": [1, 7, 3]}
    test_df = pd.DataFrame(data=test_data)
    boolean_mask = pd.Series([True, False, False], index=test_df.index)
    rejection_reason = 'invalid station_id'

    output_df = add_rejection_reason(test_df, boolean_mask, rejection_reason)

    assert output_df['rejection_reason'].tolist() == ['invalid station_id', None, None]
    pd.testing.assert_frame_equal(
    test_df,
    pd.DataFrame(data=test_data),
    )
    assert "rejection_reason" not in test_df.columns

def test_add_rejection_reason_double():
    test_data = {"end_station_id": [None, 2, 5],
                    "start_station_id": [1, 7, 3],
                    "rental_id": [None, 4, None]}
    test_df = pd.DataFrame(data=test_data)
    boolean_mask_station_id = pd.Series([True, False, False], index=test_df.index)
    rejection_reason_station_id = 'invalid station_id'

    output_df_station_id = add_rejection_reason(test_df, boolean_mask_station_id, rejection_reason_station_id)

    boolean_mask_rental_id = pd.Series([True, False, True], index=test_df.index)
    rejection_reason_rental_id = 'invalid rental_id'

    output_df = add_rejection_reason(output_df_station_id, boolean_mask_rental_id, rejection_reason_rental_id)

    assert output_df_station_id['rejection_reason'].tolist() == ['invalid station_id', None, None]
    assert output_df['rejection_reason'].tolist() == ['invalid station_id, invalid rental_id', None, 'invalid rental_id']
    pd.testing.assert_frame_equal(
        test_df,
        pd.DataFrame(data=test_data),
        )
    assert "rejection_reason" not in test_df.columns

def test_add_journey_rejection_reasons():
    test_data = {"end_station_id": [1, 2, 5, 6],
                "start_station_id": [4, None, 3, 4],
                "rental_id": [709, None, 608, 889],
                "duration_seconds": [357, 4, 0, 244],
                "started_at": ["07/02/2016 10:00", "07/02/2016 15:00", "07/02/2016 17:00", "07/02/2016 21:00"],
                "ended_at": ["07/02/2016 10:10", "07/02/2016 15:10", "07/02/2016 17:10", "07/02/2016 21:00"],
                }
    test_df = pd.DataFrame(data=test_data)
    test_df['started_at'] = pd.to_datetime(test_df['started_at'], format="%d/%m/%Y %H:%M")
    test_df['ended_at'] = pd.to_datetime(test_df['ended_at'], format="%d/%m/%Y %H:%M")

    output_df = add_journey_rejection_reasons(test_df)

    assert "rejection_reason" not in test_df.columns
    assert output_df['rejection_reason'].tolist() == [None, 'invalid station_id, invalid rental_id', 'invalid duration_seconds', 'invalid started_at or ended_at timestamp']

def test_separate_accepted_rejected_rows():
    test_data = {"rejection_reason": [None, 'invalid station_id, invalid rental_id', 'invalid duration_seconds', None]}
    test_df = pd.DataFrame(data=test_data)

    df_accepted, df_rejected = separate_accepted_rejected_rows(test_df)

    assert df_rejected['rejection_reason'].tolist() == ['invalid station_id, invalid rental_id', 'invalid duration_seconds']
    assert df_accepted['rejection_reason'].isna().all()
    assert len(test_df) == len(df_accepted) + len(df_rejected)
    pd.testing.assert_frame_equal(
            test_df,
            pd.DataFrame(data=test_data),
            )

def test_date_to_datetime_bad_vals():
    test_data = {"start_date": ["07/02/2016 00:00", None, "not-a-date"]}
    test_df = pd.DataFrame(data=test_data, dtype=str)

    output_series = date_to_datetime(test_df['start_date'])

    assert pd.isna(output_series.iloc[1])
    assert pd.isna(output_series.iloc[2])
    assert output_series.iloc[0] == pd.Timestamp("2016-02-07 00:00")

def test_add_journey_date():
    test_data = {"started_at": [pd.Timestamp("2016-02-07 00:00"),
    pd.Timestamp("2016-02-13 15:45"),]}
    test_df = pd.DataFrame(data=test_data)

    output_df = add_journey_date(test_df)

    assert output_df["journey_date"].tolist() == ["2016-02-07", "2016-02-13",]
    assert "journey_date" not in test_df.columns
