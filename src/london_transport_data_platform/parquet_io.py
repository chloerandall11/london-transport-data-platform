from pathlib import Path
import pandas as pd

def write_parquet(df: pd.DataFrame, output_path: Path, partition_cols: list[str] | None = None) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if partition_cols:
        df.to_parquet(output_path, engine='pyarrow', index=False, partition_cols=partition_cols, existing_data_behavior="delete_matching")
    else:
        df.to_parquet(output_path, engine='pyarrow', index=False, partition_cols=partition_cols)
