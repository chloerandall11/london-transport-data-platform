# London Transport Data Platform

## Overview
On the side data-engineering project. Reusable pipeline to analyse TfL demand (currently Santander Cycles), with the idea in the future to link this with weather at the time.

## Current scope
Currently downloads historical TfL Santander Cycles data and records where it came from. The cleaning pipeline uses the input and output paths given in the CLI, standardises the columns and values, converts timestamps into datetimes, checks for duplicates, validates journey durations, removes non-positive duration records, and writes the cleaned data to two new places: CSV and a Parquet dataset partitioned by journey date. The 1,000-row sample is kept for development and testing. Any rejected rows are saved to a separate file with their reasoning for failing. The package, CLI, and automated tests are working.

PostgreSQL and Docker are now implemented. The CLI loads processed Parquet journeys into a small dimensional model and records each pipeline run. Historical weather ingestion and CI are still planned.

## Data provenance
- Source: [TfL Cycling Open Data](https://cycling.data.tfl.gov.uk/)
- Original file: `02aJourneyDataExtract07Fe16-20Feb2016.csv`
- Coverage: 7–20 February 2016
- The source is automatically downloaded using the ingestion command
- `create_sample.py` deterministically selects the first 1,000 rows.
- Raw and generated data are excluded from Git.
- The cleaning pipeline reads the raw input without modification

## Ingesting raw data

Download the historical TfL journey file and capture its provenance. The URL says **where to get it from**, and the destination says **where to save it**.

```bash
tfl-pipeline ingest \
  --url "https://cycling.data.tfl.gov.uk/usage-stats/02aJourneyDataExtract07Fe16-20Feb2016.csv" \
  --destination data/raw/02aJourneyDataExtract07Fe16-20Feb2016.csv
```

The command also creates a `.metadata.json` sidecar file containing:

- source URL
- retrieval timestamp
- downloaded filename
- SHA-256 checksum
- source row count
- file size in bytes

Rerunning the command replaces the files at the same paths and doesn't create duplicate raw or metadata files.

## Setup

Prerequisites:

- Python 3.12.11
- Git

Create and activate a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install the package and locked development dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
```

Verify the installation:

```bash
tfl-pipeline clean --help
python -m pytest -q
python -m ruff check src tests
python -m ruff format --check src tests
```

## Local PostgreSQL

- Docker Desktop is required
- `.env.example` shows the required config names - you must create your own `.env` file and replace the example password
- `.env` is automatically ignored by git here

Create the local environment file and replace its example password:

```bash
cp .env.example .env
```

Start PostgreSQL and check its status:

```bash
docker compose up -d
docker compose ps
```

When PostgreSQL starts with a fresh database volume, it automatically runs `sql/schema.sql` and creates the `dim_station`, `dim_date`, `pipeline_run`, and `fact_journey` tables.

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

The named database volume is retained by `docker compose down`. Using `docker compose down --volumes` also deletes the local database data and should only be used when deliberately resetting it.

## Running the pipeline

The CLI requires explicit input and output paths:

```bash
tfl-pipeline clean \
  --input data/raw/santander_journeys_sample.csv \
  --output data/processed/santander_journeys_clean.csv \
  --rejected-output data/processed/santander_journeys_rejected.csv \
  --parquet-output data/processed/santander_journeys_clean
```

Load the processed journeys into PostgreSQL:

```bash
set -a
source .env
set +a

tfl-pipeline load \
  --parquet-input data/processed/santander_journeys_clean \
  --rejected-input data/processed/santander_journeys_rejected.csv \
  --metadata data/raw/02aJourneyDataExtract07Fe16-20Feb2016.csv.metadata.json
```

The `--parquet-output` is a directory where the data is partitioned by `journey_date`.
A successful sample run reports:

```text
Validation complete: input_rows=<number> output_rows=<number> rejected_rows=<number> duration_mismatch_rows=<number> duplicate_rows=<number> duplicate_rental_id_rows=<number> nonpositive_duration_rows=<number>
```
Depending on the sample data, these counts will vary.

Raw and processed datasets are intentionally ignored by Git.

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
```

## Validation rules

- Rental IDs cannot be null and must be unique.
- Durations must be numbers and greater than 0.
- Timestamps must be convertible to datetimes, and the end time must occur after the start time.
- Station IDs must be numbers, positive, and integers.
- Invalid rows are saved in a rejected rows file with reasons.
- Input rows must equal accepted rows plus rejected rows.
- Rerunning cleaning safely replaces both output files.

## Current components

- `cli.py` provides the `ingest`, `clean`, and `load` commands.
- `config.py` defines configuration for ingestion, cleaning, file-based PostgreSQL loading, and database connections.
- `ingest.py` downloads the configured raw CSV and writes provenance metadata.
- `provenance.py` defines the information recorded about each downloaded source file.
- `clean_journeys.py` validates, transforms, and separates accepted and rejected journeys.
- `parquet_io.py` writes accepted journeys as a date-partitioned Parquet dataset.
- `load_postgres.py` prepares and loads stations, dates, journey facts, and pipeline-run records.
- `sql/schema.sql` defines the PostgreSQL dimensional model, constraints, and indexes.
- `compose.yaml` runs the local PostgreSQL service and initializes the schema.
- `tests/` contains unit, pipeline, idempotency, database integration, and transaction rollback tests.

The latest development-sample load recorded 1,000 input rows, 995 accepted rows, and 5 rejected rows. PostgreSQL contained 995 journey facts, 582 unique stations, and one date. Repeating the same load created a new pipeline-run receipt without duplicating the dimensional or journey data.