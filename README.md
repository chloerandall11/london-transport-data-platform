# London Transport Data Platform

## Overview
On the side data-engineering project. Reusable pipeline to analyse TfL demand (currently Santander Cycles), with the idea in the future to link this with weather at the time.

## Current scope
Currently reads the first 1000 rows of sample data, standardises columns and names, converts timestamps into datetimes, checks for duplicates and validates journey durations by removing non-positive duration records. Writes the clean sample data to a new file. Installable and usable by CLI and unit tests are currently being added.

PostgreSQL, Parquet, weather ingestion, Docker, and CI are planned but not yet implemented.

## Data provenance
- Source: [TfL Cycling Open Data](https://cycling.data.tfl.gov.uk/)
- Original file: `02aJourneyDataExtract07Fe16-20Feb2016.csv`
- Coverage: 7–20 February 2016
- The source was manually downloaded.
- `create_sample.py` deterministically selects the first 1,000 rows.
- Raw and generated data are excluded from Git.
- Raw input is treated as immutable.

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
tfl-pipeline --help
pytest -q
```

## Running the pipeline

The CLI requires explicit input and output paths:

```bash
tfl-pipeline \
  --input data/raw/santander_journeys_sample.csv \
  --output data/processed/santander_journeys_clean.csv
```

A successful sample run reports:

```text
Validation complete: input_rows=<number> output_rows=<number> duration_mismatch_rows=<number> duplicate_rows=<number> duplicate_rental_id_rows=<number> nonpositive_duration_rows=<number>
```
Depending on the sample data, these counts will vary.

Raw and processed datasets are intentionally ignored by Git.

## Architecture

```text
Historical TfL CSV
        |
        v
Command-line interface
        |
        v
PipelineConfig
        |
        v
Load -> standardise -> validate -> filter -> normalise
        |
        +--> cleaned CSV
        |
        +--> ValidationResult and structured logs
```

## Current components:

- `cli.py` parses explicit input and output paths.
- `config.py` carries run configuration.
- `clean_journeys.py` performs loading, validation, transformation, and export.
- `validation.py` defines the structured validation result.
- `create_sample.py` creates a deterministic development sample.
- `tests/` contains automated unit tests.

Parquet and PostgreSQL will be added as later output layers without replacing the existing validation and cleaning stages.