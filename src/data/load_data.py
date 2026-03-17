"""Data loading utilities."""
import pandas as pd
from pathlib import Path
import kagglehub


def download_kaggle_data(dataset: str = "hummaamqaasim/jobs-in-data") -> str:
    """Download dataset from Kaggle."""
    path = kagglehub.dataset_download(dataset)
    print(f"Dataset downloaded to: {path}")
    return path


def load_raw_data(file_path: str | Path) -> pd.DataFrame:
    """Load raw data from CSV file."""
    df = pd.read_csv(file_path)
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    return df


def load_processed_data(processed_dir: str | Path = "data/processed") -> pd.DataFrame:
    """Load processed data."""
    path = Path(processed_dir) / "cleaned_data.csv"
    return pd.read_csv(path)
