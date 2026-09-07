from dataclasses import dataclass


@dataclass(frozen=True)
class IngestionMetadata:
    source_url: str
    retrieval_timestamp: str
    filename: str
    checksum_sha256: str
    source_row_count: int
    file_size_bytes: int
