"""Data preprocessing utilities."""
import pandas as pd
from pathlib import Path


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean raw data.

    Steps:
    - Handle missing values
    - Remove duplicates
    - Fix data types
    """
    df_clean = df.copy()

    # Remove duplicates
    initial_rows = len(df_clean)
    df_clean = df_clean.drop_duplicates()
    print(f"Removed {initial_rows - len(df_clean)} duplicate rows")

    # Handle missing values
    missing_cols = df_clean.columns[df_clean.isnull().any()].tolist()
    if missing_cols:
        print(f"Columns with missing values: {missing_cols}")

    return df_clean


def save_processed_data(
    df: pd.DataFrame,
    output_dir: str | Path = "data/processed",
    filename: str = "cleaned_data.csv"
) -> None:
    """Save processed data to CSV."""
    output_path = Path(output_dir) / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Saved processed data to: {output_path}")
