from dataclasses import dataclass

@dataclass(frozen=True)
class ValidationResult:
    input_rows: int
    output_rows: int
    duration_mismatch_rows: int
    duplicate_rows: int
    duplicate_rental_id_rows: int
    nonpositive_duration_rows: int