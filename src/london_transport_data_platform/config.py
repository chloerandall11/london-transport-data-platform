from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PipelineConfig:
    input_path: Path
    output_path: Path
    rejected_output_path: Path
    parquet_output_path: Path

@dataclass(frozen=True)
class IngestionConfig:
    source_url: str
    destination_path: Path