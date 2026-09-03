from london_transport_data_platform.parquet_io import write_parquet
import pandas as pd

def test_write_parquet(tmp_path):
    test_data = {
        "rental_id": [1, 2],
        "duration_seconds": [60, 450],
        "started_at": [pd.Timestamp("2016-02-07 00:00"), pd.Timestamp("2016-02-13 15:45")],
        }
    test_df = pd.DataFrame(data=test_data)

    output_path = tmp_path / "processed" / "journeys.parquet"
    write_parquet(test_df, output_path)

    read_test_df = pd.read_parquet(output_path)

    assert output_path.exists()
    pd.testing.assert_frame_equal(
        test_df,
        read_test_df,
        )

def test_write_partitioned_parquet(tmp_path):
    test_data = {"journey_date": ["2016-02-07", "2016-02-13"], "rental_id": [1, 2]}
    test_df = pd.DataFrame(data=test_data)

    output_path = tmp_path / "processed" / "journeys"

    write_parquet(test_df, output_path, partition_cols=["journey_date"],)

    assert (output_path / "journey_date=2016-02-07").exists()
    assert (output_path / "journey_date=2016-02-13").exists()

    # checking idempotency
    write_parquet(test_df, output_path, partition_cols=["journey_date"],)
    output_df = pd.read_parquet(output_path)

    assert len(output_df) == 2
