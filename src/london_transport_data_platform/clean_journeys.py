from pathlib import Path
import pandas as pd
from london_transport_data_platform.config import PipelineConfig
import logging
from london_transport_data_platform.validation import ValidationResult
import datetime as dt

logger = logging.getLogger(__name__)


def load_journeys(input_path: Path) -> pd.DataFrame:
    df = pd.read_csv(input_path)
    return df


def standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    standard_df = df.rename(
        columns={
            "Rental Id": "rental_id",
            "Duration": "duration_seconds",
            "Bike Id": "bike_id",
            "End Date": "ended_at",
            "EndStation Id": "end_station_id",
            "EndStation Name": "end_station_name",
            "Start Date": "started_at",
            "StartStation Id": "start_station_id",
            "StartStation Name": "start_station_name",
        }
    )
    return standard_df


def date_to_datetime(df_col: pd.Series) -> pd.Series:
    df_new_col = pd.to_datetime(df_col, format="%d/%m/%Y %H:%M")
    return df_new_col

def validate_required_columns(df: pd.DataFrame) -> None:
    required_cols = (
    "Rental Id",
    "Duration",
    "Bike Id",
    "End Date",
    "EndStation Id",
    "EndStation Name",
    "Start Date",
    "StartStation Id",
    "StartStation Name",
    )

    existing_cols = df.columns.to_list()

    missing_cols = []
    for col in required_cols:
        if col not in existing_cols:
            missing_cols.append(col)

    if missing_cols:
        raise ValueError(
    f"Missing required columns: {', '.join(missing_cols)}")


def remove_nonpositive_durations(df: pd.DataFrame) -> pd.DataFrame:
    df_positive_durations = df[df["duration_seconds"] > 0].copy()
    return df_positive_durations


def normalise_station_names(df_col: pd.Series) -> pd.Series:
    normalised_df_col = df_col.str.strip().str.replace(r"\s+,", ",", regex=True)
    return normalised_df_col

def invalid_rental_id_mask(df: pd.DataFrame) -> pd.Series:
    df_rental_id = df["rental_id"]
    boolean_mask_null = df_rental_id.isnull()
    boolean_mask_duplicate = df_rental_id.duplicated(keep=False)

    return boolean_mask_duplicate | boolean_mask_null

def invalid_duration_mask(df: pd.DataFrame) -> pd.Series:
    df_duration = df["duration_seconds"]
    boolean_mask_0_or_less = df_duration <= 0
    boolean_mask_null =  df_duration.isnull()

    return boolean_mask_0_or_less | boolean_mask_null

def invalid_timestamp_mask(df: pd.DataFrame) -> pd.Series:
    boolean_mask_null_started = df['started_at'].isnull()
    boolean_mask_null_ended = df['ended_at'].isnull()

    df_diff = (df['ended_at']-df['started_at']).dt.total_seconds()
    boolean_mask_end_before_start = df_diff <= 0

    return boolean_mask_end_before_start | boolean_mask_null_ended | boolean_mask_null_started

def invalid_station_id_mask(df: pd.DataFrame) -> pd.Series:
    boolean_mask_null_end = df['end_station_id'].isnull()
    boolean_mask_null_start = df['start_station_id'].isnull()

    boolean_mask_negative_end = df['end_station_id'] <= 0
    boolean_mask_negative_start = df['start_station_id'] <= 0


    return boolean_mask_negative_end | boolean_mask_negative_start | boolean_mask_null_end | boolean_mask_null_start

def add_rejection_reason(df: pd.DataFrame, boolean_mask: pd.Series, rejection_reason: str) -> pd.DataFrame:
    df_copy = df.copy()
    if 'rejection_reason' not in df_copy.columns:
        df_copy['rejection_reason'] = None

    already_has_reason_mask = (boolean_mask & df_copy["rejection_reason"].notna())
    has_no_reason_mask = (boolean_mask & df_copy["rejection_reason"].isna())

    df_copy.loc[has_no_reason_mask, "rejection_reason"] = rejection_reason
    df_copy.loc[already_has_reason_mask, "rejection_reason"] += f", {rejection_reason}"
    return df_copy

def add_journey_rejection_reasons(df: pd.DataFrame) -> pd.DataFrame:
    boolean_mask_station_id = invalid_station_id_mask(df)
    boolean_mask_timestamp = invalid_timestamp_mask(df)
    boolean_mask_duration = invalid_duration_mask(df)
    boolean_mask_rental_id = invalid_rental_id_mask(df)

    output_df = add_rejection_reason(df, boolean_mask_station_id, 'invalid station_id')
    output_df = add_rejection_reason(output_df, boolean_mask_timestamp, 'invalid started_at or ended_at timestamp')
    output_df = add_rejection_reason(output_df, boolean_mask_duration, 'invalid duration_seconds')
    output_df = add_rejection_reason(output_df, boolean_mask_rental_id, 'invalid rental_id')

    return output_df

def run_pipeline(config: PipelineConfig) -> ValidationResult:
    # read csv as dataframe
    df = load_journeys(config.input_path)
    validate_required_columns(df)
    logger.info(
    "Loaded %d rows and %d columns from %s",
    len(df),
    len(df.columns),
    config.input_path,
    )

    # standardise column names
    df = standardise_columns(df)
    logger.debug("Standardised columns: %s", df.columns.tolist())

    # change date formats to datetime type
    df["started_at"] = date_to_datetime(df["started_at"])
    df["ended_at"] = date_to_datetime(df["ended_at"])
    logger.debug("Datatype check for dates: %s", df[["started_at", "ended_at"]].dtypes)

    # validate csv duration_seconds using datetime
    validate_duration_seconds = (df["ended_at"] - df["started_at"]).dt.total_seconds()
    unequal_rows = (validate_duration_seconds != df["duration_seconds"]).sum()

    # check for duplicates
    duplicated_rows = df.duplicated().sum()
    duplicated_rental_id_rows = df["rental_id"].duplicated().sum()

    # validate and clean durations
    low_duration_rows = (df["duration_seconds"] <= 0).sum()
    pre_filter_row_count = df.shape[0]

    df = remove_nonpositive_durations(df)
    post_filter_row_count = df.shape[0]

    # normalising station names
    df["start_station_name"] = normalise_station_names(df["start_station_name"])
    df["end_station_name"] = normalise_station_names(df["end_station_name"])
    logger.debug("Station name samples: start=%s end=%s", df["start_station_name"].head(3), df["end_station_name"].head(3))

    # reorder columns
    column_order = [
        "rental_id",
        "bike_id",
        "started_at",
        "start_station_id",
        "start_station_name",
        "ended_at",
        "end_station_id",
        "end_station_name",
        "duration_seconds",
    ]

    df = df[column_order]
    logger.debug("Output columns: %s", df.columns.tolist())

    # save cleaned df as a csv
    df.to_csv(config.output_path, index=False)
    logger.info("Wrote cleaned journeys to %s", config.output_path)

    return ValidationResult(
        input_rows=pre_filter_row_count,
        output_rows=post_filter_row_count,
        duration_mismatch_rows=int(unequal_rows),
        duplicate_rows=int(duplicated_rows),
        duplicate_rental_id_rows=int(duplicated_rental_id_rows),
        nonpositive_duration_rows=int(low_duration_rows),
    )
