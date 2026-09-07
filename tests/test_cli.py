from london_transport_data_platform.cli import build_parser
from pathlib import Path

def test_clean_build_parser_accepts_path():
    parser = build_parser()

    args = parser.parse_args(
    [
        "clean",
        "--input",
        "input.csv",
        "--output",
        "clean.csv",
        "--rejected-output",
        "rejected.csv",
        "--parquet-output",
        "clean_journeys",
    ]
    )

    assert args.command == "clean"
    assert args.rejected_output_path == Path("rejected.csv")
    assert args.output_path == Path("clean.csv")
    assert args.input_path == Path("input.csv")
    assert args.parquet_output_path == Path("clean_journeys")

def test_load_build_parser_accepts_paths():
    parser = build_parser()

    args = parser.parse_args(
    [
        "load",
        "--parquet-input",
        "accepted",
        "--rejected-input",
        "rejected.csv",
        "--metadata",
        "source.metadata.json"
    ]
    )

    assert args.command == "load"
    assert args.parquet_input_path == Path("accepted")
    assert args.rejected_input_path == Path("rejected.csv")
    assert args.metadata_path == Path("source.metadata.json")