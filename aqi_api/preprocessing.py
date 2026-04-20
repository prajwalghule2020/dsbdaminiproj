"""Dataframe transformations that mirror the notebook training pipeline."""

from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd

from .constants import LAG_DAYS, POLLUTANT_COLUMNS


def build_daily_averages_from_hourly(hourly_df: pd.DataFrame, window_count: int) -> pd.DataFrame:
    if hourly_df.empty:
        raise ValueError("Hourly dataframe is empty. Cannot build daily averages.")

    frame = hourly_df.copy()
    frame["Datetime"] = pd.to_datetime(frame["Datetime"], errors="coerce", utc=True)
    frame = frame.dropna(subset=["Datetime"]).sort_values("Datetime").reset_index(drop=True)

    latest_hour = frame["Datetime"].max().floor("h")

    rows = []
    for offset in range(window_count - 1, -1, -1):
        window_end = latest_hour - pd.Timedelta(days=offset)
        window_start = window_end - pd.Timedelta(hours=24)
        window_df = frame.loc[
            (frame["Datetime"] > window_start) & (frame["Datetime"] <= window_end)
        ]

        row = {
            "Datetime": window_end.floor("D"),
            "_hours_in_window": int(window_df.shape[0]),
        }
        for pollutant in POLLUTANT_COLUMNS:
            if pollutant in window_df.columns:
                values = pd.to_numeric(window_df[pollutant], errors="coerce")
                row[pollutant] = float(values.mean()) if not values.dropna().empty else np.nan
            else:
                row[pollutant] = np.nan

        rows.append(row)

    daily_df = pd.DataFrame(rows)
    daily_df = (
        daily_df.sort_values("Datetime")
        .drop_duplicates(subset=["Datetime"], keep="last")
        .reset_index(drop=True)
    )

    return daily_df


def build_inference_features(
    daily_df: pd.DataFrame, feature_columns: List[str]
) -> Tuple[pd.DataFrame, pd.Timestamp]:
    if daily_df.empty:
        raise ValueError("Daily dataframe is empty. Cannot build inference row.")

    frame = daily_df.copy().sort_values("Datetime").reset_index(drop=True)
    frame["Datetime"] = pd.to_datetime(frame["Datetime"], errors="coerce", utc=True)
    frame = frame.dropna(subset=["Datetime"]).copy()

    if frame.shape[0] < LAG_DAYS + 1:
        raise ValueError(
            f"At least {LAG_DAYS + 1} daily rows are required to build lag features."
        )

    for pollutant in POLLUTANT_COLUMNS:
        if pollutant not in frame.columns:
            raise ValueError(f"Required pollutant column '{pollutant}' is missing.")
        frame[pollutant] = pd.to_numeric(frame[pollutant], errors="coerce")

    for pollutant in POLLUTANT_COLUMNS:
        for lag in range(1, LAG_DAYS + 1):
            frame[f"{pollutant}_lag_{lag}"] = frame[pollutant].shift(lag)

    frame["day_of_week"] = frame["Datetime"].dt.dayofweek
    frame["month"] = frame["Datetime"].dt.month
    frame["day"] = frame["Datetime"].dt.day

    latest_row = frame.tail(1).copy()

    missing_features = [column for column in feature_columns if column not in latest_row.columns]
    if missing_features:
        raise ValueError(
            "Inference row is missing expected feature columns: "
            + ", ".join(missing_features[:10])
        )

    ordered_features = latest_row.reindex(columns=feature_columns)

    if ordered_features.isna().any().any():
        missing_nan_columns = ordered_features.columns[ordered_features.isna().any()].tolist()
        raise ValueError(
            "Inference row has NaN values after preprocessing for columns: "
            + ", ".join(missing_nan_columns[:10])
        )

    feature_datetime = pd.Timestamp(latest_row["Datetime"].iloc[0])
    return ordered_features, feature_datetime
