"""Model training utilities."""
import pandas as pd
from sklearn.model_selection import train_test_split


def train_model(
    df: pd.DataFrame,
    target_col: str,
    feature_cols: list[str],
    test_size: float = 0.2,
    random_state: int = 42
):
    """
    Train a model.

    Returns:
        model, X_test, y_test for evaluation
    """
    X = df[feature_cols]
    y = df[target_col]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    # Add model training logic here
    model = None  # Placeholder

    return model, X_test, y_test
