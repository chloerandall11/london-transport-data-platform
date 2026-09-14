import argparse
import logging
from pathlib import Path

from london_transport_data_platform.clean_journeys import run_pipeline
from london_transport_data_platform.config import (
    IngestionConfig,
    PipelineConfig,
    PostgresLoadConfig,
    database_config_from_environment,
)
from london_transport_data_platform.ingest import ingest_file
from london_transport_data_platform.load_postgres import (
    connect_database,
    load_processed_journeys,
)

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clean TfL cycle journey data.")

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

    load_parser = subparsers.add_parser(
        "load",
        help="Load processed journey data into PostgreSQL.",
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

    clean_parser.add_argument(
        "--parquet-output",
        dest="parquet_output_path",
        type=Path,
        required=True,
        help="Directory to save the partitioned parquet.",
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

    load_parser.add_argument(
        "--parquet-input",
        dest="parquet_input_path",
        type=Path,
        required=True,
        help="Partitioned Parquet dataset containing accepted journeys.",
    )

    load_parser.add_argument(
        "--rejected-input",
        dest="rejected_input_path",
        type=Path,
        required=True,
        help="CSV file containing rejected journey rows.",
    )

    load_parser.add_argument(
        "--metadata",
        dest="metadata_path",
        type=Path,
        required=True,
        help="JSON file containing source provenance metadata.",
    )

    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "clean":
        config = PipelineConfig(
            input_path=args.input_path,
            output_path=args.output_path,
            rejected_output_path=args.rejected_output_path,
            parquet_output_path=args.parquet_output_path,
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
            result.nonpositive_duration_rows,
        )
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

    elif args.command == "load":
        load_config = PostgresLoadConfig(
            parquet_input_path=args.parquet_input_path,
            rejected_input_path=args.rejected_input_path,
            metadata_path=args.metadata_path,
        )

        database_config = database_config_from_environment()

        with connect_database(database_config) as connection:
            run_id = load_processed_journeys(connection, load_config)

        logger.info("PostgreSQL load complete: pipeline_run_id=%d", run_id)


if __name__ == "__main__":
    main()
