import argparse
from pathlib import Path
from london_transport_data_platform.clean_journeys import run_pipeline
from london_transport_data_platform.config import PipelineConfig
import logging

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Clean TfL cycle journey data."
    )

    parser.add_argument(
        "--input",
        dest="input_path",
        type=Path,
        required=True,
        help="The raw CSV file to read.",
    )

    parser.add_argument(
        "--output",
        dest="output_path",
        type=Path,
        required=True,
        help="Where to save the cleaned CSV.",
    )

    return parser


def main() -> None:
    args = build_parser().parse_args()

    config = PipelineConfig(
        input_path=args.input_path,
        output_path=args.output_path,
    )

    result = run_pipeline(config)
    logger.info(
    "Validation complete: input_rows=%d output_rows=%d "
    "duration_mismatch_rows=%d duplicate_rows=%d "
    "duplicate_rental_id_rows=%d nonpositive_duration_rows=%d",
    result.input_rows,
    result.output_rows,
    result.duration_mismatch_rows,
    result.duplicate_rows,
    result.duplicate_rental_id_rows,
    result.nonpositive_duration_rows,)

if __name__ == "__main__":
    main()