# import
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def create_sample(
    input_path: Path,
    output_path: Path,
    row_count: int = 1000,
) -> int:

    # calling first 1000 rows of data
    df = pd.read_csv(input_path, nrows=row_count)
    logger.debug("Dataframe shape: %s", df.shape)
    logger.debug("Existing columns: %s", list(df.columns))

    df.to_csv(output_path, index=False)
    logger.info("%d data saved to: %s", len(df), output_path)

    return len(df)
