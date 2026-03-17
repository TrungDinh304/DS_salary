"""Feature engineering utilities."""
import pandas as pd


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build features for analysis/modeling.

    Add business-meaningful features here.
    """
    df_features = df.copy()

    # Example: Extract year from date columns if exists
    # Example: Create salary bins
    # Example: Aggregate statistics

    return df_features
