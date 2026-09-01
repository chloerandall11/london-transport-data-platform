from london_transport_data_platform.ingest import calculate_sha256, download_file
from london_transport_data_platform.config import IngestionConfig
import pytest
from urllib.error import URLError

def test_calculate_sha256(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(b"hello")

    result = calculate_sha256(file_path)
    assert result == ("2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")

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

    temporary_path = destination_path.with_suffix(
        destination_path.suffix + ".part"
    )

    assert not destination_path.exists()
    assert not temporary_path.exists()