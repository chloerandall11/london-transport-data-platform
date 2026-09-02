from london_transport_data_platform.clean_journeys import run_pipeline
from london_transport_data_platform.config import PipelineConfig
import pandas as pd

def test_run_pipeline(tmp_path):
    test_data = {
    "Rental Id": [1, 2, 5],
    "Duration": [60, 0, 'not-a-duration'],
    "Bike Id": [101, 102, 103],
    "End Date": ["07/02/2016 00:01", "07/02/2016 00:02", "07/02/2016 00:16"],
    "EndStation Id": [20, 30, 45],
    "EndStation Name": [" End Station , Test ", "Same Station", "Station"],
    "Start Date": ["07/02/2016 00:00", "07/02/2016 00:02", "07/02/2016 00:06"],
    "StartStation Id": [10, 30, 43],
    "StartStation Name": [" Start Station , Test ", "Same Station", "Station"],
    }
    
    input_path = tmp_path / "input_journeys.csv"
    output_path = tmp_path / "clean_journeys.csv"
    rejected_output_path = tmp_path / "rejected_journeys.csv"

    config = PipelineConfig(
    input_path=input_path,
    output_path=output_path,
    rejected_output_path=rejected_output_path,)

    input_df = pd.DataFrame(data=test_data)
    input_df.to_csv(input_path, index=False)
    result = run_pipeline(config)
    output_df = pd.read_csv(output_path)
    rejected_df = pd.read_csv(rejected_output_path)


    assert result.input_rows == 3
    assert result.output_rows == 1
    assert result.nonpositive_duration_rows == 1
    assert result.rejected_rows == 2
    assert result.input_rows == result.output_rows + result.rejected_rows
    assert len(rejected_df) == 2
    assert output_df.shape == (1, 9)
    assert output_df.loc[0, "start_station_name"] == "Start Station, Test"
    assert output_df.loc[0, "end_station_name"] == "End Station, Test"
    assert rejected_df['rental_id'].tolist() == [2, 5]
    assert rejected_df['rejection_reason'].tolist() == ['invalid started_at or ended_at timestamp, invalid duration_seconds', 'invalid duration_seconds']

    second_result = run_pipeline(config)
    second_output_df = pd.read_csv(output_path)
    second_rejected_df = pd.read_csv(rejected_output_path)

    assert second_result == result
    pd.testing.assert_frame_equal(output_df, second_output_df)
    pd.testing.assert_frame_equal(rejected_df, second_rejected_df)


