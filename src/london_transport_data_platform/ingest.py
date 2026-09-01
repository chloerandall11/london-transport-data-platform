"""
Download raw source files and calculate checksums.
This module contains the first stages of data ingestion. It streams a file
from a configured source URL into the local raw-data directory without loading
the entire file into memory. It can also calculate a SHA-256 checksum by
reading the file in chunks.
The source URL and destination path come from IngestionConfig. The checksum
will later support provenance tracking and repeated-run detection.
"""
import hashlib
from pathlib import Path
import json
from dataclasses import asdict
from shutil import copyfileobj
from urllib.request import urlopen, Request
import csv
from london_transport_data_platform.config import IngestionConfig
from datetime import datetime, timezone
from london_transport_data_platform.provenance import IngestionMetadata

def calculate_sha256(file_path: Path) -> str:
    checksum = hashlib.sha256()
    with file_path.open("rb") as file:
        while chunk := file.read(8192):
            checksum.update(chunk)

    return checksum.hexdigest()

def download_file(config: IngestionConfig) -> Path:
    config.destination_path.parent.mkdir(
    parents=True,
    exist_ok=True,
    )

    temporary_path = config.destination_path.with_suffix(
    config.destination_path.suffix + ".part"
    )

    request = Request(
    config.source_url,
    headers={
        "User-Agent": "london-transport-data-platform/0.1",
    },
    )

    try:
        with (
            urlopen(request, timeout=30) as response,
            temporary_path.open("wb") as output_file,
        ):
            copyfileobj(response, output_file)

        temporary_path.replace(config.destination_path)

    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return config.destination_path

def count_csv_rows(file_path: Path) -> int:
    with file_path.open(
    "r",
    encoding="utf-8-sig",
    newline="",) as file:
        reader = csv.reader(file)
        next(reader, None)
        return sum(1 for _ in reader)

def create_ingestion_metadata(config: IngestionConfig,file_path: Path,) -> IngestionMetadata:
    return IngestionMetadata(
        source_url=config.source_url,
        retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
        filename=file_path.name,
        checksum_sha256=calculate_sha256(file_path),
        source_row_count=count_csv_rows(file_path),
        file_size_bytes=file_path.stat().st_size,)

def write_ingestion_metadata(metadata: IngestionMetadata, metadata_path: Path,) -> Path:
    metadata_path.parent.mkdir(parents=True, exist_ok=True,)

    metadata_json = json.dumps(
        asdict(metadata),
        indent=2,
        sort_keys=True,
    )

    metadata_path.write_text(
        metadata_json + "\n",
        encoding="utf-8",
    )

    return metadata_path

def ingest_file(config: IngestionConfig) -> IngestionMetadata:
    downloaded_path = download_file(config)

    metadata = create_ingestion_metadata(
        config,
        downloaded_path,
    )

    metadata_path = downloaded_path.with_suffix(
        downloaded_path.suffix + ".metadata.json"
    )

    write_ingestion_metadata(
        metadata,
        metadata_path,
    )

    return metadata