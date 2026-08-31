import pandas as pd
from london_transport_data_platform.clean_journeys import remove_nonpositive_durations

def test_remove_nonpositive_durations():
    test_data = {"duration_seconds": [0, -10, 60]}
    test_df = pd.DataFrame(data=test_data)
    output_df = remove_nonpositive_durations(test_df)
    assert output_df["duration_seconds"].tolist() == [60]
    assert len(test_df) == 3
