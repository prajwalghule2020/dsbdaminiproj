"""Local cache and estimation utilities for hourly and daily pollutant data."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from .constants import AROMATIC_COLUMNS, POLLUTANT_COLUMNS


class LocalPollutionStore:
    def __init__(self, cache_dir: Path, city_day_path: Path) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.hourly_cache_path = self.cache_dir / "hourly_cache.csv"
        self.aromatic_cache_path = self.cache_dir / "aromatic_daily_cache.csv"
        self.city_day_path = city_day_path

        self._bootstrap_aromatic_cache()

    def upsert_hourly(self, city: str, hourly_df: pd.DataFrame) -> pd.DataFrame:
        if hourly_df.empty:
            raise ValueError("Cannot cache empty hourly history.")

        frame = hourly_df.copy()
        frame["City"] = city
        frame["Datetime"] = pd.to_datetime(frame["Datetime"], errors="coerce", utc=True)
        frame = frame.dropna(subset=["Datetime"])

        for pollutant in POLLUTANT_COLUMNS:
            if pollutant not in frame.columns:
                frame[pollutant] = np.nan
            frame[pollutant] = pd.to_numeric(frame[pollutant], errors="coerce")

        frame = frame[["City", "Datetime", *POLLUTANT_COLUMNS]].copy()

        cache = self._read_hourly_cache()
        combined = pd.concat([cache, frame], ignore_index=True)
        combined = (
            combined.drop_duplicates(subset=["City", "Datetime"], keep="last")
            .sort_values(["City", "Datetime"])
            .reset_index(drop=True)
        )

        self._write_hourly_cache(combined)

        city_mask = combined["City"].str.lower() == city.lower()
        return combined.loc[city_mask].reset_index(drop=True)

    def fill_aromatic_estimates(
        self, city: str, daily_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[str]]:
        if daily_df.empty:
            raise ValueError("Daily dataframe is empty. Cannot estimate aromatic pollutants.")

        frame = daily_df.copy()
        frame["Datetime"] = pd.to_datetime(frame["Datetime"], errors="coerce", utc=True)
        frame = frame.dropna(subset=["Datetime"]).sort_values("Datetime").reset_index(drop=True)

        for pollutant in AROMATIC_COLUMNS:
            if pollutant not in frame.columns:
                frame[pollutant] = np.nan
            frame[pollutant] = pd.to_numeric(frame[pollutant], errors="coerce")

        frame["Date"] = frame["Datetime"].dt.date

        aromatic_cache = self._read_aromatic_cache()
        city_history = aromatic_cache.loc[
            aromatic_cache["City"].str.lower() == city.lower()
        ].copy()
        city_history = city_history.sort_values("Date").reset_index(drop=True)

        imputed_fields = set()

        for idx in frame.index:
            current_date = frame.at[idx, "Date"]
            for pollutant in AROMATIC_COLUMNS:
                if pd.notna(frame.at[idx, pollutant]):
                    continue

                estimate = self._estimate_aromatic_value(
                    pollutant=pollutant,
                    row_date=current_date,
                    city=city,
                    city_history=city_history,
                    full_history=aromatic_cache,
                )
                frame.at[idx, pollutant] = float(estimate)
                imputed_fields.add(pollutant)

            new_row = {
                "City": city,
                "Date": current_date,
                "Benzene": float(frame.at[idx, "Benzene"]),
                "Toluene": float(frame.at[idx, "Toluene"]),
                "Xylene": float(frame.at[idx, "Xylene"]),
            }
            city_history = pd.concat([city_history, pd.DataFrame([new_row])], ignore_index=True)
            city_history = (
                city_history.drop_duplicates(subset=["Date"], keep="last")
                .sort_values("Date")
                .reset_index(drop=True)
            )

        self._upsert_aromatic_cache(city, frame[["Date", *AROMATIC_COLUMNS]])

        return frame.drop(columns=["Date"]), sorted(imputed_fields)

    def get_city_pollutant_priors(self, city: str) -> Dict[str, float]:
        default_priors = {pollutant: 0.0 for pollutant in POLLUTANT_COLUMNS}
        if not self.city_day_path.exists():
            return default_priors

        source_df = pd.read_csv(self.city_day_path)
        required = {"City", *POLLUTANT_COLUMNS}
        if not required.issubset(set(source_df.columns)):
            return default_priors

        source_df["City"] = source_df["City"].astype(str)
        for pollutant in POLLUTANT_COLUMNS:
            source_df[pollutant] = pd.to_numeric(source_df[pollutant], errors="coerce")

        city_mask = source_df["City"].str.lower() == city.lower()
        city_df = source_df.loc[city_mask]
        reference_df = city_df if not city_df.empty else source_df

        priors: Dict[str, float] = {}
        for pollutant in POLLUTANT_COLUMNS:
            mean_value = reference_df[pollutant].dropna().mean()
            if pd.isna(mean_value):
                mean_value = source_df[pollutant].dropna().mean()
            priors[pollutant] = float(mean_value) if pd.notna(mean_value) else 0.0

        return priors

    def _estimate_aromatic_value(
        self,
        pollutant: str,
        row_date,
        city: str,
        city_history: pd.DataFrame,
        full_history: pd.DataFrame,
    ) -> float:
        same_day = city_history.loc[city_history["Date"] == row_date, pollutant].dropna()
        if not same_day.empty:
            return float(same_day.iloc[-1])

        trailing = city_history.loc[city_history["Date"] < row_date, pollutant].dropna().tail(7)
        if not trailing.empty:
            return float(trailing.mean())

        city_values = full_history.loc[
            full_history["City"].str.lower() == city.lower(), pollutant
        ].dropna()
        if not city_values.empty:
            return float(city_values.mean())

        global_values = full_history[pollutant].dropna()
        if not global_values.empty:
            return float(global_values.mean())

        return 0.0

    def _bootstrap_aromatic_cache(self) -> None:
        if self.aromatic_cache_path.exists():
            return

        columns = ["City", "Date", *AROMATIC_COLUMNS]
        if not self.city_day_path.exists():
            pd.DataFrame(columns=columns).to_csv(self.aromatic_cache_path, index=False)
            return

        source_df = pd.read_csv(self.city_day_path)
        required = {"City", "Datetime", *AROMATIC_COLUMNS}
        if not required.issubset(set(source_df.columns)):
            pd.DataFrame(columns=columns).to_csv(self.aromatic_cache_path, index=False)
            return

        source_df["Datetime"] = pd.to_datetime(source_df["Datetime"], errors="coerce")
        source_df = source_df.dropna(subset=["Datetime"]).copy()
        source_df["Date"] = source_df["Datetime"].dt.date

        for pollutant in AROMATIC_COLUMNS:
            source_df[pollutant] = pd.to_numeric(source_df[pollutant], errors="coerce")

        bootstrap = (
            source_df[["City", "Date", *AROMATIC_COLUMNS]]
            .groupby(["City", "Date"], as_index=False)[AROMATIC_COLUMNS]
            .mean()
        )

        bootstrap.to_csv(self.aromatic_cache_path, index=False)

    def _read_hourly_cache(self) -> pd.DataFrame:
        columns = ["City", "Datetime", *POLLUTANT_COLUMNS]
        if not self.hourly_cache_path.exists():
            return pd.DataFrame(columns=columns)

        cache = pd.read_csv(self.hourly_cache_path)
        if cache.empty:
            return pd.DataFrame(columns=columns)

        cache["Datetime"] = pd.to_datetime(cache["Datetime"], errors="coerce", utc=True)
        cache = cache.dropna(subset=["Datetime"]).copy()
        cache["City"] = cache["City"].astype(str)

        for pollutant in POLLUTANT_COLUMNS:
            if pollutant not in cache.columns:
                cache[pollutant] = np.nan
            cache[pollutant] = pd.to_numeric(cache[pollutant], errors="coerce")

        return cache[["City", "Datetime", *POLLUTANT_COLUMNS]].copy()

    def _write_hourly_cache(self, cache: pd.DataFrame) -> None:
        cache.to_csv(self.hourly_cache_path, index=False)

    def _read_aromatic_cache(self) -> pd.DataFrame:
        columns = ["City", "Date", *AROMATIC_COLUMNS]
        if not self.aromatic_cache_path.exists():
            return pd.DataFrame(columns=columns)

        cache = pd.read_csv(self.aromatic_cache_path)
        if cache.empty:
            return pd.DataFrame(columns=columns)

        cache["City"] = cache["City"].astype(str)
        cache["Date"] = pd.to_datetime(cache["Date"], errors="coerce").dt.date
        cache = cache.dropna(subset=["Date"]).copy()

        for pollutant in AROMATIC_COLUMNS:
            if pollutant not in cache.columns:
                cache[pollutant] = np.nan
            cache[pollutant] = pd.to_numeric(cache[pollutant], errors="coerce")

        return cache[["City", "Date", *AROMATIC_COLUMNS]].copy()

    def _upsert_aromatic_cache(self, city: str, updates: pd.DataFrame) -> None:
        cache = self._read_aromatic_cache()

        frame = updates.copy()
        frame["City"] = city
        frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce").dt.date

        for pollutant in AROMATIC_COLUMNS:
            frame[pollutant] = pd.to_numeric(frame[pollutant], errors="coerce")

        combined = pd.concat([cache, frame[["City", "Date", *AROMATIC_COLUMNS]]], ignore_index=True)
        combined = (
            combined.drop_duplicates(subset=["City", "Date"], keep="last")
            .sort_values(["City", "Date"])
            .reset_index(drop=True)
        )

        combined.to_csv(self.aromatic_cache_path, index=False)
