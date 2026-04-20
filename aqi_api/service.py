"""High-level AQI prediction workflow service."""

from __future__ import annotations

from datetime import timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .categories import to_cpcb_category
from .config import Settings
from .constants import LAG_DAYS, POLLUTANT_COLUMNS
from .openweather import OpenWeatherClient, OpenWeatherClientError
from .predictor import LinearAQIPredictor
from .preprocessing import build_daily_averages_from_hourly, build_inference_features
from .store import LocalPollutionStore


class AQIPredictionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.openweather_client = OpenWeatherClient(
            api_key=settings.openweather_api_key,
            air_base_url=settings.openweather_base_url,
            geocoding_base_url=settings.geocoding_base_url,
            timeout_seconds=settings.request_timeout_seconds,
        )
        self.store = LocalPollutionStore(
            cache_dir=settings.cache_dir,
            city_day_path=settings.city_day_path,
        )
        self.predictor = LinearAQIPredictor(
            model_path=settings.model_path,
            feature_columns_path=settings.feature_columns_path,
        )

    def predict_next_day(self, city: str) -> Dict[str, object]:
        city = city.strip()
        if not city:
            raise ValueError("City name is required.")

        resolved_city, lat, lon = self.openweather_client.geocode_city(city)

        end_dt = pd.Timestamp.utcnow().floor("h")
        start_dt = end_dt - pd.Timedelta(days=self.settings.history_days)

        hourly_api_df = self._fetch_hourly_pollution_with_fallback(
            lat=lat,
            lon=lon,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        cached_city_df = self.store.upsert_hourly(resolved_city, hourly_api_df)

        recent_start = end_dt - pd.Timedelta(days=self.settings.history_days)
        recent_hourly_df = cached_city_df.loc[
            (cached_city_df["Datetime"] >= recent_start)
            & (cached_city_df["Datetime"] <= end_dt)
        ].copy()

        if recent_hourly_df.empty:
            raise ValueError("No hourly history found for the requested city.")

        daily_df = build_daily_averages_from_hourly(
            hourly_df=recent_hourly_df,
            window_count=LAG_DAYS + 1,
        )

        daily_df, imputed_pollutants = self._fill_missing_pollutants_from_priors(
            resolved_city, daily_df
        )
        daily_df, imputed_aromatics = self.store.fill_aromatic_estimates(resolved_city, daily_df)
        imputed_fields = sorted(set(imputed_pollutants + imputed_aromatics))

        model_features, feature_day = build_inference_features(
            daily_df=daily_df,
            feature_columns=self.predictor.feature_columns,
        )

        predicted_aqi = max(0.0, self.predictor.predict(model_features))
        predicted_aqi = round(predicted_aqi, 3)

        return {
            "city": resolved_city,
            "predicted_aqi": predicted_aqi,
            "category": to_cpcb_category(predicted_aqi),
            "prediction_for_date": (feature_day + timedelta(days=1)).date(),
            "diagnostics": {
                "history_start_utc": start_dt.to_pydatetime(),
                "history_end_utc": end_dt.to_pydatetime(),
                "hourly_rows_used": int(recent_hourly_df.shape[0]),
                "daily_rows_built": int(daily_df.shape[0]),
                "imputed_fields": sorted(imputed_fields),
            },
        }

    def _fetch_hourly_pollution_with_fallback(
        self,
        lat: float,
        lon: float,
        start_dt: pd.Timestamp,
        end_dt: pd.Timestamp,
    ) -> pd.DataFrame:
        history_error: Optional[str] = None
        try:
            return self.openweather_client.fetch_air_pollution_history(
                lat=lat,
                lon=lon,
                start_unix_utc=int(start_dt.timestamp()),
                end_unix_utc=int(end_dt.timestamp()),
            )
        except (OpenWeatherClientError, ValueError) as exc:
            history_error = str(exc)

        try:
            current_df = self.openweather_client.fetch_air_pollution_current(lat=lat, lon=lon)
        except (OpenWeatherClientError, ValueError):
            current_df = pd.DataFrame()

        try:
            forecast_df = self.openweather_client.fetch_air_pollution_forecast(lat=lat, lon=lon)
            fallback_df = pd.concat([current_df, forecast_df], ignore_index=True)
            if fallback_df.empty:
                raise ValueError("Fallback pollution data is empty.")

            fallback_df = (
                fallback_df.sort_values("Datetime")
                .drop_duplicates(subset=["Datetime"], keep="last")
                .reset_index(drop=True)
            )
            return fallback_df
        except (OpenWeatherClientError, ValueError) as exc:
            raise OpenWeatherClientError(
                "OpenWeather history endpoint is unavailable for this API key and "
                "forecast fallback also failed. "
                f"History error: {history_error}. Forecast error: {exc}"
            ) from exc

    def _fill_missing_pollutants_from_priors(
        self, city: str, daily_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[str]]:
        frame = daily_df.copy()
        priors = self.store.get_city_pollutant_priors(city)
        imputed_columns = set()

        for pollutant in POLLUTANT_COLUMNS:
            if pollutant not in frame.columns:
                frame[pollutant] = pd.NA

            frame[pollutant] = pd.to_numeric(frame[pollutant], errors="coerce")
            missing_before = frame[pollutant].isna()

            frame[pollutant] = frame[pollutant].ffill().bfill()
            frame[pollutant] = frame[pollutant].fillna(priors.get(pollutant, 0.0))

            if missing_before.any() and frame.loc[missing_before, pollutant].notna().any():
                imputed_columns.add(pollutant)

        return frame, sorted(imputed_columns)
