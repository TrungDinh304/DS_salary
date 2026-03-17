"""Model evaluation utilities."""
from sklearn.metrics import mean_squared_error, r2_score, accuracy_score


def evaluate_model(model, X_test, y_test, task_type: str = "regression"):
    """
    Evaluate model performance.

    Args:
        task_type: "regression" or "classification"
    """
    y_pred = model.predict(X_test)

    if task_type == "regression":
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        print(f"MSE: {mse:.4f}")
        print(f"R2: {r2:.4f}")
        return {"mse": mse, "r2": r2}
    else:
        acc = accuracy_score(y_test, y_pred)
        print(f"Accuracy: {acc:.4f}")
        return {"accuracy": acc}
