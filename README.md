# London Transport Data Platform

## Overview

This is a data-engineering portfolio project that builds a reusable pipeline for analysing Transport for London demand data.

The project currently processes historical Santander Cycles journeys. A future stage will add historical weather data from the same period so that weather conditions can be compared with cycling demand.

## Current scope

The pipeline currently:

- downloads a configured historical TfL Santander Cycles CSV
- records provenance information about the downloaded source
- creates a deterministic development sample
- validates and cleans journey records
- retains rejected records with explicit rejection reasons
- writes accepted data to CSV and date-partitioned Parquet
- runs PostgreSQL locally through Docker Compose
- loads a dimensional model into PostgreSQL
- records each database pipeline run
- prevents repeated loads from duplicating journey data
- provides analytical SQL queries
- runs automated tests, linting, and formatting checks through GitHub Actions

Historical weather ingestion is planned but is not yet implemented.

## Data provenance

- Source: [TfL Cycling Open Data](https://cycling.data.tfl.gov.uk/)
- Original file: `02aJourneyDataExtract07Fe16-20Feb2016.csv`
- Coverage: 7–20 February 2016
- The source is downloaded using the ingestion command.
- `create_sample.py` deterministically selects the first 1,000 rows for development.
- Raw and generated data are excluded from Git.
- The cleaning pipeline reads the raw input without modifying it.

Each ingestion run records:

- source URL
- retrieval timestamp
- downloaded filename
- SHA-256 checksum
- source row count
- file size in bytes

## Setup

### Prerequisites

- Python 3.12.11
- Git
- Docker Desktop

Create and activate a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install the package and its locked development dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
```

Verify the installation:

```bash
tfl-pipeline --help
python -m pytest -q
python -m ruff check src tests
python -m ruff format --check src tests
```

## Ingesting raw data

Download the historical TfL journey file and capture its provenance:

```bash
tfl-pipeline ingest \
  --url "https://cycling.data.tfl.gov.uk/usage-stats/02aJourneyDataExtract07Fe16-20Feb2016.csv" \
  --destination data/raw/02aJourneyDataExtract07Fe16-20Feb2016.csv
```

The URL identifies where the source data comes from, and the destination identifies where it should be saved.

The command also creates a `.metadata.json` sidecar file containing the provenance information.

Rerunning the command replaces the files at the same configured paths rather than creating duplicate raw or metadata files.

## Cleaning journey data

The cleaning command requires explicit input and output paths:

```bash
tfl-pipeline clean \
  --input data/raw/santander_journeys_sample.csv \
  --output data/processed/santander_journeys_clean.csv \
  --rejected-output data/processed/santander_journeys_rejected.csv \
  --parquet-output data/processed/santander_journeys_clean
```

The command produces:

- an accepted-journeys CSV
- a rejected-journeys CSV with rejection reasons
- a date-partitioned Parquet dataset

The `--parquet-output` value is a dataset directory rather than an individual Parquet file.

A successful cleaning run reports validation totals similar to:

```text
Validation complete: input_rows=<number> output_rows=<number> rejected_rows=<number> duration_mismatch_rows=<number> duplicate_rows=<number> duplicate_rental_id_rows=<number> nonpositive_duration_rows=<number>
```

The exact counts depend on the input data.

Raw and processed datasets are intentionally ignored by Git.

## Local PostgreSQL

Create a local environment file from the example:

```bash
cp .env.example .env
```

Replace the example password in `.env` with your own local development password.

The local `.env` file is ignored by Git and must not be committed.

Make sure Docker Desktop is running, then start PostgreSQL:

```bash
docker compose up -d
```

Check the service status:

```bash
docker compose ps
```

Wait until the PostgreSQL service reports that it is healthy.

When PostgreSQL starts with a fresh database volume, it automatically runs `sql/schema.sql`. This creates:

- `dim_station`
- `dim_date`
- `fact_journey`
- `pipeline_run`

Test the database connection:

```bash
docker compose exec postgres \
  psql -U tfl_pipeline -d london_transport \
  -c "SELECT current_database(), current_user;"
```

Stop PostgreSQL:

```bash
docker compose down
```

The named database volume is retained when `docker compose down` is used.

The following command also deletes the local database volume and should only be used when deliberately resetting the database:

```bash
docker compose down --volumes
```

## Loading PostgreSQL

Export the database settings from `.env` into the current terminal session:

```bash
set -a
source .env
set +a
```

Load the processed journey data into PostgreSQL:

```bash
tfl-pipeline load \
  --parquet-input data/processed/santander_journeys_clean \
  --rejected-input data/processed/santander_journeys_rejected.csv \
  --metadata data/raw/02aJourneyDataExtract07Fe16-20Feb2016.csv.metadata.json
```

The load process:

- reads the processed Parquet dataset
- prepares station and date dimension records
- inserts journey facts
- records a pipeline-run receipt
- uses database transactions
- prevents repeated loads from duplicating stations, dates, or journeys

A repeated load creates a new pipeline-run record while leaving the dimensional and journey row counts unchanged.

## Analytical SQL

Analytical queries are stored in `sql/analysis/`.

The current queries answer the following questions:

- Which stations have the most journeys starting from them?
- Which stations have the most journeys ending at them?
- How does journey demand vary by hour?
- How does journey demand vary by date?
- How are journeys distributed across duration bands?

Run an individual query from the project root with:

```bash
docker compose exec -T postgres \
  psql -U tfl_pipeline -d london_transport \
  < sql/analysis/busiest_start_stations.sql
```

Replace the final filename to run a different analytical query.

The development sample contains journeys from only one date and a limited number of hours. Queries become more representative when the full historical extract is processed and loaded.

## Architecture

```text
Historical TfL CSV URL
        |
        v
tfl-pipeline ingest
        |
        +--> raw CSV
        |
        +--> provenance metadata JSON
                 |
                 v
        tfl-pipeline clean
                 |
                 +--> accepted CSV
                 |
                 +--> rejected CSV with rejection reasons
                 |
                 +--> date-partitioned Parquet
                              |
                              v
                     tfl-pipeline load
                              |
                              +--> dim_station
                              +--> dim_date
                              +--> fact_journey
                              +--> pipeline_run
                                      |
                                      v
                              analytical SQL
```

The repository is checked automatically by GitHub Actions:

```text
push or pull request
        |
        v
install locked dependencies
        |
        v
start PostgreSQL service
        |
        v
create database schema
        |
        +--> Ruff linting
        +--> Ruff formatting check
        +--> pytest test suite
```

## Validation rules

The journey pipeline checks that:

- rental IDs are present and unique
- durations are numeric and greater than zero
- timestamps can be converted to datetimes
- journey end times occur after start times
- station IDs are present, numeric, positive integers
- duplicated rows and rental IDs are identified
- duration values agree with the calculated timestamp difference
- rejected rows retain one or more useful rejection reasons
- input rows equal accepted rows plus rejected rows

Rerunning the cleaning pipeline safely replaces its configured outputs.

## PostgreSQL model

### `dim_station`

Stores each unique station once and is used for both the start-station and end-station roles.

### `dim_date`

Stores calendar attributes for each journey date, including the day name and weekend indicator.

### `fact_journey`

Stores accepted journey records and references:

- the start station
- the end station
- the journey date
- the pipeline run that loaded the record

The rental ID is the primary key and prevents repeated loads from duplicating journey facts.

### `pipeline_run`

Records information about each load, including:

- source filename
- source checksum
- start and completion timestamps
- run status
- input row count
- accepted row count
- rejected row count

## Testing

The automated test suite covers:

- CSV loading
- required-column validation
- column-name standardisation
- timestamp conversion
- malformed timestamp handling
- station-name normalisation
- journey validation rules
- rejection-reason creation
- accepted and rejected row separation
- row-count reconciliation
- Parquet output
- partitioned repeat writes
- ingestion and provenance
- temporary-file cleanup
- database configuration
- database connectivity
- schema constraints
- station, date, and journey loading
- pipeline-run records
- repeated-load behaviour
- transaction rollback
- reconciliation between processed input and loaded facts
- CLI argument parsing

Run the tests locally with:

```bash
python -m pytest -q
```

Run the quality checks with:

```bash
python -m ruff check src tests
python -m ruff format --check src tests
```

The same checks run in GitHub Actions on pushes and pull requests.

## Current components

- `cli.py` provides the `ingest`, `clean`, and `load` commands.
- `config.py` defines ingestion, cleaning, PostgreSQL-loading, and database configuration.
- `ingest.py` downloads the configured source CSV.
- `provenance.py` records information about the downloaded source.
- `create_sample.py` creates a deterministic development sample.
- `clean_journeys.py` validates, transforms, and separates accepted and rejected journeys.
- `validation.py` defines validation result information.
- `parquet_io.py` writes accepted data as date-partitioned Parquet.
- `load_postgres.py` prepares and loads stations, dates, journey facts, and pipeline-run records.
- `sql/schema.sql` defines the dimensional model, constraints, and indexes.
- `sql/analysis/` contains analytical SQL queries.
- `compose.yaml` runs the local PostgreSQL service.
- `.github/workflows/ci.yml` runs automated CI checks.
- `tests/` contains unit, pipeline, idempotency, and database integration tests.

## Latest development-sample result

The latest development-sample run produced:

- 1,000 input rows
- 995 accepted rows
- 5 rejected rows
- 995 journey facts in PostgreSQL
- 582 unique stations
- 1 journey date

Repeating the same database load created another pipeline-run receipt without duplicating the station, date, or journey records.

## Planned work

The next major stage is historical weather ingestion aligned with the journey period.

Later improvements may include:

- weather validation and rejected-record handling
- weather-related PostgreSQL tables
- weather-versus-demand analysis
- processing the full historical TfL extract
- cloud storage
- orchestration
- dbt transformations