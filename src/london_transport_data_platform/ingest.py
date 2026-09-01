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
from shutil import copyfileobj
from urllib.request import urlopen
from london_transport_data_platform.config import IngestionConfig

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

    try:
        with (
            urlopen(config.source_url, timeout=30) as response,
            temporary_path.open("wb") as output_file,
        ):
            copyfileobj(response, output_file)

        temporary_path.replace(config.destination_path)

    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return config.destination_path