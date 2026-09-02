import argparse
from pathlib import Path
from london_transport_data_platform.clean_journeys import run_pipeline
from london_transport_data_platform.config import PipelineConfig, IngestionConfig
from london_transport_data_platform.ingest import ingest_file
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

    subparsers = parser.add_subparsers(
    dest="command",
    required=True,
    )

    clean_parser = subparsers.add_parser(
        "clean",
        help="Clean and standardise a TfL journey CSV.",
    )

    ingest_parser = subparsers.add_parser(
    "ingest",
    help="Download a raw TfL journey CSV with provenance.",
    )

    clean_parser.add_argument(
        "--input",
        dest="input_path",
        type=Path,
        required=True,
        help="The raw CSV file to read.",
    )

    clean_parser.add_argument(
        "--output",
        dest="output_path",
        type=Path,
        required=True,
        help="Where to save the cleaned CSV.",
    )

    clean_parser.add_argument(
        "--rejected-output",
        dest="rejected_output_path",
        type=Path,
        required=True,
        help="Where to save the rejected record CSV.",
        )

    ingest_parser.add_argument(
    "--url",
    dest="source_url",
    required=True,
    help="Source URL for the historical TfL CSV.",
    )

    ingest_parser.add_argument(
    "--destination",
    dest="destination_path",
    type=Path,
    required=True,
    help="Local path for the downloaded raw CSV.",
    )

    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "clean":    
        config = PipelineConfig(
            input_path=args.input_path,
            output_path=args.output_path,
            rejected_output_path=args.rejected_output_path,
        )

        result = run_pipeline(config)
        logger.info(
        "Validation complete: input_rows=%d output_rows=%d "
        "rejected_rows=%d duration_mismatch_rows=%d duplicate_rows=%d "
        "duplicate_rental_id_rows=%d nonpositive_duration_rows=%d",
        result.input_rows,
        result.output_rows,
        result.rejected_rows,
        result.duration_mismatch_rows,
        result.duplicate_rows,
        result.duplicate_rental_id_rows,
        result.nonpositive_duration_rows,)
    elif args.command == "ingest":
        config = IngestionConfig(
            source_url=args.source_url,
            destination_path=args.destination_path,
        )

        metadata = ingest_file(config)

        logger.info(
            "Ingestion complete: filename=%s rows=%d bytes=%d sha256=%s",
            metadata.filename,
            metadata.source_row_count,
            metadata.file_size_bytes,
            metadata.checksum_sha256,
            )

if __name__ == "__main__":
    main()