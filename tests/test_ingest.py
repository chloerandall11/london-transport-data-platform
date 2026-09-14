import json
from datetime import datetime, timedelta
from urllib.error import URLError

import pytest

from london_transport_data_platform.config import IngestionConfig
from london_transport_data_platform.ingest import (
    calculate_sha256,
    count_csv_rows,
    create_ingestion_metadata,
    download_file,
    ingest_file,
    write_ingestion_metadata,
)
from london_transport_data_platform.provenance import IngestionMetadata


def test_calculate_sha256(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(b"hello")

    result = calculate_sha256(file_path)
    assert result == (
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


def test_download_file(tmp_path):
    source_path = tmp_path / "source.csv"
    source_bytes = b"rental_id,duration\n1,60\n"
    source_path.write_bytes(source_bytes)

    destination_path = tmp_path / "raw" / "journeys.csv"

    config = IngestionConfig(
        source_url=source_path.as_uri(),
        destination_path=destination_path,
    )

    result = download_file(config)

    assert result == destination_path
    assert destination_path.read_bytes() == source_bytes


def test_download_file_with_missing_source(tmp_path):
    missing_source = tmp_path / "does_not_exist.csv"
    destination_path = tmp_path / "raw" / "journeys.csv"

    config = IngestionConfig(
        source_url=missing_source.as_uri(),
        destination_path=destination_path,
    )

    with pytest.raises(URLError):
        download_file(config)

    temporary_path = destination_path.with_suffix(destination_path.suffix + ".part")

    assert not destination_path.exists()
    assert not temporary_path.exists()


def test_count_csv_rows(tmp_path):
    file_path = tmp_path / "journeys.csv"
    file_path.write_text(
        'id,name\n1,"Station\nName"\n2,Other\n',
        encoding="utf-8",
    )

    result = count_csv_rows(file_path)
    assert result == 2


def test_create_ingestion_metadata(tmp_path):
    file_path = tmp_path / "journeys.csv"
    file_bytes = b"id,duration\n1,60\n2,120\n"
    file_path.write_bytes(file_bytes)

    config = IngestionConfig(
        source_url="https://example.com/journeys.csv",
        destination_path=file_path,
    )
    metadata = create_ingestion_metadata(config, file_path)
    retrieved_at = datetime.fromisoformat(metadata.retrieval_timestamp)

    assert retrieved_at.utcoffset() == timedelta(0)
    assert metadata.source_url == config.source_url
    assert metadata.filename == "journeys.csv"
    assert metadata.checksum_sha256 == calculate_sha256(file_path)
    assert metadata.source_row_count == 2
    assert metadata.file_size_bytes == len(file_bytes)


def test_write_ingestion_metadata(tmp_path):
    metadata = IngestionMetadata(
        source_url="https://example.com/journeys.csv",
        retrieval_timestamp="2026-09-01T12:00:00+00:00",
        filename="journeys.csv",
        checksum_sha256="abc123",
        source_row_count=2,
        file_size_bytes=24,
    )

    metadata_path = tmp_path / "metadata" / "journeys.metadata.json"
    result = write_ingestion_metadata(metadata, metadata_path)
    saved_data = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert result == metadata_path
    assert saved_data["source_url"] == metadata.source_url
    assert saved_data["retrieval_timestamp"] == metadata.retrieval_timestamp
    assert saved_data["filename"] == metadata.filename
    assert saved_data["checksum_sha256"] == metadata.checksum_sha256
    assert saved_data["source_row_count"] == 2
    assert saved_data["file_size_bytes"] == 24


def test_ingest_file_is_repeatable(tmp_path):
    source_path = tmp_path / "source.csv"
    source_bytes = b"id,duration\n1,60\n2,120\n"
    source_path.write_bytes(source_bytes)

    raw_directory = tmp_path / "raw"
    destination_path = raw_directory / "journeys.csv"

    config = IngestionConfig(
        source_url=source_path.as_uri(),
        destination_path=destination_path,
    )

    first_metadata = ingest_file(config)
    second_metadata = ingest_file(config)

    metadata_path = raw_directory / "journeys.csv.metadata.json"
    saved_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert destination_path.read_bytes() == source_bytes
    assert first_metadata.checksum_sha256 == second_metadata.checksum_sha256
    assert saved_metadata["checksum_sha256"] == second_metadata.checksum_sha256
    assert saved_metadata["source_row_count"] == 2

    created_files = {path.name for path in raw_directory.iterdir()}

    assert created_files == {
        "journeys.csv",
        "journeys.csv.metadata.json",
    }
