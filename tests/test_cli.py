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