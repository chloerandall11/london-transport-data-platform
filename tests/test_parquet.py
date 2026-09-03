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



