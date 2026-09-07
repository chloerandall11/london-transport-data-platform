from dataclasses import dataclass
from pathlib import Path
import os

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

@dataclass(frozen=True)
class PostgresLoadConfig:
    parquet_input_path: Path
    rejected_input_path: Path
    metadata_path: Path

@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str

def database_config_from_environment() -> DatabaseConfig:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port_text = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")

    if not dbname or not user or not password:
        raise ValueError("POSTGRES_DB, POSTGRES_USER, and POSTGRES_PASSWORD must be set")

    return DatabaseConfig(
    host=host,
    port=int(port_text),
    dbname=dbname,
    user=user,
    password=password,
    )