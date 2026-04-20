"""Model artifact loader and prediction wrapper."""

from __future__ import annotations

from pathlib import Path
from typing import List

import joblib
import pandas as pd


class LinearAQIPredictor:
    def __init__(self, model_path: Path, feature_columns_path: Path) -> None:
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        if not feature_columns_path.exists():
            raise FileNotFoundError(f"Feature columns file not found: {feature_columns_path}")

        self.model = joblib.load(model_path)
        columns = joblib.load(feature_columns_path)
        self.feature_columns = self._normalize_feature_columns(columns)

    @staticmethod
    def _normalize_feature_columns(columns: object) -> List[str]:
        if isinstance(columns, list):
            return [str(col) for col in columns]

        if isinstance(columns, tuple):
            return [str(col) for col in columns]

        raise TypeError("feature_columns.pkl must contain a list or tuple of feature names.")

    def predict(self, features: pd.DataFrame) -> float:
        if features.shape[0] != 1:
            raise ValueError("Inference DataFrame must contain exactly one row.")

        prediction = self.model.predict(features)
        return float(prediction[0])
