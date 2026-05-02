"""Data loading utilities."""
import shutil
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
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


def _find_csv_in_directory(directory: Path) -> Path | None:
    csv_files = sorted(directory.glob("*.csv"))
    return csv_files[0] if csv_files else None


def _find_csv_in_tree(directory: Path) -> Path | None:
    candidates = sorted(directory.rglob("*.csv"))
    return candidates[0] if candidates else None


def _copy_csv_to_raw(source: Path, raw_dir: Path) -> Path:
    destination = raw_dir / source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    return destination


def _extract_csv_from_zip(zip_path: Path, raw_dir: Path) -> Path:
    with ZipFile(zip_path, "r") as archive:
        csv_members = sorted([name for name in archive.namelist() if name.lower().endswith(".csv")])
        if not csv_members:
            raise FileNotFoundError("Downloaded archive does not contain a CSV file")
        extracted_path = Path(archive.extract(csv_members[0], path=raw_dir))
        return extracted_path


def _download_dataset_csv(dataset: str, raw_dir: Path) -> Path:
    downloaded = Path(download_kaggle_data(dataset))
    if downloaded.is_dir():
        csv_file = _find_csv_in_tree(downloaded)
        if not csv_file:
            raise FileNotFoundError("Dataset directory does not contain a CSV file")
        return _copy_csv_to_raw(csv_file, raw_dir)
    if downloaded.suffix.lower() == ".zip":
        return _extract_csv_from_zip(downloaded, raw_dir)
    raise RuntimeError("Downloaded dataset must be a directory or a zip archive")


def load_raw_data_with_fallback(
    raw_dir: str | Path = "data/raw",
    dataset: str | None = None,
    filename: str | None = None,
) -> pd.DataFrame:
    """Read local CSV or download from Kaggle when it is missing."""
    raw_path = Path(raw_dir)
    raw_path.mkdir(parents=True, exist_ok=True)
    candidate = raw_path / filename if filename else _find_csv_in_directory(raw_path)
    if candidate and candidate.exists():
        return load_raw_data(candidate)
    if not dataset:
        raise ValueError("Dataset identifier is required when no local CSV is available")
    csv_path = _download_dataset_csv(dataset, raw_path)
    return load_raw_data(csv_path)

# def main():
#     # load data for test this package
#     df = load_raw_data_with_fallback(
#         raw_dir="data/raw",
#         dataset="hummaamqaasim/jobs-in-data",
#         filename=None,
#     )
#     print(df.head())
# if __name__ == "__main__":
#     main()
