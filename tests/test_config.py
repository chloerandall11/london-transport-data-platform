import pytest

from london_transport_data_platform.config import (
    DatabaseConfig,
    database_config_from_environment,
)


def test_database_config_from_environment(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "test-host")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "test-database")
    monkeypatch.setenv("POSTGRES_USER", "test-user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")

    result = database_config_from_environment()

    expected = DatabaseConfig(
        host="test-host",
        port=5432,
        dbname="test-database",
        user="test-user",
        password="test-password",
    )

    assert result == expected


def test_database_config_requires_credentials(monkeypatch):
    monkeypatch.delenv("POSTGRES_DB", raising=False)
    monkeypatch.delenv("POSTGRES_USER", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

    with pytest.raises(ValueError):
        database_config_from_environment()
