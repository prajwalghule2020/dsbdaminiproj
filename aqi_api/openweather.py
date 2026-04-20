"""OpenWeather API client helpers for geocoding and pollution data."""

from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
import requests

from .constants import OPENWEATHER_COMPONENT_MAP


class OpenWeatherClientError(RuntimeError):
    """Raised when OpenWeather returns an error or unexpected payload."""


class OpenWeatherClient:
    def __init__(
        self,
        api_key: str,
        air_base_url: str,
        geocoding_base_url: str,
        timeout_seconds: int = 20,
    ) -> None:
        self.api_key = api_key
        self.air_base_url = air_base_url.rstrip("/")
        self.geocoding_base_url = geocoding_base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()

    def geocode_city(self, city: str) -> Tuple[str, float, float]:
        params = {
            "q": city,
            "limit": 1,
            "appid": self.api_key,
        }
        payload = self._get_json(f"{self.geocoding_base_url}/geo/1.0/direct", params)

        if not isinstance(payload, list) or not payload:
            raise ValueError(f"City '{city}' was not found in OpenWeather geocoding response.")

        location = payload[0]
        resolved_city = str(location.get("name", city)).strip() or city

        try:
            lat = float(location["lat"])
            lon = float(location["lon"])
        except (KeyError, TypeError, ValueError) as exc:
            raise OpenWeatherClientError("Invalid geocoding payload from OpenWeather.") from exc

        return resolved_city, lat, lon

    def fetch_air_pollution_history(
        self,
        lat: float,
        lon: float,
        start_unix_utc: int,
        end_unix_utc: int,
    ) -> pd.DataFrame:
        params = {
            "lat": lat,
            "lon": lon,
            "start": start_unix_utc,
            "end": end_unix_utc,
            "appid": self.api_key,
        }
        payload = self._get_json(
            f"{self.air_base_url}/data/2.5/air_pollution/history", params
        )

        measurements = payload.get("list", []) if isinstance(payload, dict) else []
        if not measurements:
            raise ValueError("OpenWeather history endpoint returned no hourly measurements.")

        return self._measurements_to_hourly_dataframe(measurements)

    def fetch_air_pollution_current(self, lat: float, lon: float) -> pd.DataFrame:
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
        }
        payload = self._get_json(f"{self.air_base_url}/data/2.5/air_pollution", params)

        measurements = payload.get("list", []) if isinstance(payload, dict) else []
        if not measurements:
            raise ValueError("OpenWeather current endpoint returned no measurements.")

        return self._measurements_to_hourly_dataframe(measurements)

    def fetch_air_pollution_forecast(self, lat: float, lon: float) -> pd.DataFrame:
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
        }
        payload = self._get_json(
            f"{self.air_base_url}/data/2.5/air_pollution/forecast", params
        )

        measurements = payload.get("list", []) if isinstance(payload, dict) else []
        if not measurements:
            raise ValueError("OpenWeather forecast endpoint returned no hourly measurements.")

        return self._measurements_to_hourly_dataframe(measurements)

    def _measurements_to_hourly_dataframe(self, measurements: Any) -> pd.DataFrame:
        rows = []
        for item in measurements:
            dt_unix = item.get("dt")
            components = item.get("components", {})
            if dt_unix is None:
                continue

            row: Dict[str, Any] = {
                "Datetime": pd.to_datetime(dt_unix, unit="s", utc=True),
            }
            for api_component, model_column in OPENWEATHER_COMPONENT_MAP.items():
                value = components.get(api_component)
                row[model_column] = float(value) if value is not None else np.nan

            rows.append(row)

        if not rows:
            raise ValueError("No valid hourly records were parsed from OpenWeather response.")

        history_df = pd.DataFrame(rows).sort_values("Datetime").reset_index(drop=True)
        history_df["NOx"] = history_df["NO"] + history_df["NO2"]

        return history_df

    def _get_json(self, url: str, params: Dict[str, Any]) -> Any:
        try:
            response = self.session.get(url, params=params, timeout=self.timeout_seconds)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise OpenWeatherClientError(f"OpenWeather request failed: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise OpenWeatherClientError("OpenWeather response is not valid JSON.") from exc
