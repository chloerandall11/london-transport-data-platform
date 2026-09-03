# London Transport Data Platform

## Overview
On the side data-engineering project. Reusable pipeline to analyse TfL demand (currently Santander Cycles), with the idea in the future to link this with weather at the time.

## Current scope
Currently downloads historical TfL Santander Cycles data and records where it came from. The cleaning pipeline uses the input and output paths given in the CLI, standardises the columns and values, converts timestamps into datetimes, checks for duplicates, validates journey durations, removes non-positive duration records, and writes the cleaned data to two new files: CSV and Parquet. The 1,000-row sample is kept for development and testing. Any rejected rows are saved to a separate file with their reasoning for failing. The package, CLI, and automated tests are working.

PostgreSQL, weather ingestion, Docker, and CI are planned but not yet implemented.

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
pytest -q
```

## Running the pipeline

The CLI requires explicit input and output paths:

```bash
tfl-pipeline clean \
  --input data/raw/santander_journeys_sample.csv \
  --output data/processed/santander_journeys_clean.csv \
  --rejected-output data/processed/santander_journeys_rejected.csv \
  --parquet-output data/processed/santander_journeys_clean.parquet
```

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
        v
IngestionConfig -> download raw file
        |
        +--> raw CSV
        |
        +--> provenance metadata JSON
                 |
                 v
        tfl-pipeline clean
                 |
                 v
        PipelineConfig
                 |
                 v
Load -> standardise -> validate -> filter -> normalise
                 |
                 +--> accepted rows -> normalise -> cleaned CSV
                 |
                 +--> rejected CSV with rejection reasons
                 |
                 +--> ValidationResult and structured logs
```

## Validation rules

- Rental IDs cannot be null and must be unique.
- Durations must be numbers and greater than 0.
- Timestamps must be convertible to datetimes, and the end time must occur after the start time.
- Station IDs must be numbers, positive, and integers.
- Invalid rows are saved in a rejected rows file with reasons.
- Input rows must equal accepted rows plus rejected rows.
- Rerunning cleaning safely replaces both output files.

## Current components:

- `cli.py` provides the `clean` and `ingest` commands and accepts paths
- `config.py` carries run configuration
- `clean_journeys.py` performs loading, validation, transformation, and export
- `validation.py` defines the structured validation result
- `create_sample.py` creates a deterministic development sample
- `tests/` contains automated unit tests, and cli, pipeline, ingestion tests
- `ingest.py` downloads the configured raw CSV and creates its provenance metadata
- `provenance.py` defines the information recorded about each downloaded source file

PostgreSQL will be added as later output layers without replacing the existing validation and cleaning stages.