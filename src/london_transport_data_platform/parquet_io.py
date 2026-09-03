from pathlib import Path
import pandas as pd

def write_parquet(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, engine='pyarrow', index=False)