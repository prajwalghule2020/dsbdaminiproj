"""Environment-driven configuration for the AQI API service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    openweather_api_key: str
    openweather_base_url: str
    geocoding_base_url: str
    request_timeout_seconds: int
    history_days: int
    model_path: Path
    feature_columns_path: Path
    city_day_path: Path
    cache_dir: Path


def load_settings() -> Settings:
    package_dir = Path(__file__).resolve().parent
    # Allow local development without forcing --env-file on uvicorn.
    load_dotenv(package_dir / ".env", override=False)
    load_dotenv(package_dir.parent / ".env", override=False)

    api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENWEATHER_API_KEY is required. Set it before starting the FastAPI app."
        )

    return Settings(
        openweather_api_key=api_key,
        openweather_base_url=os.getenv("OPENWEATHER_BASE_URL", "https://api.openweathermap.org"),
        geocoding_base_url=os.getenv("OPENWEATHER_GEOCODING_BASE_URL", "https://api.openweathermap.org"),
        request_timeout_seconds=int(os.getenv("OPENWEATHER_TIMEOUT_SECONDS", "20")),
        history_days=max(8, int(os.getenv("OPENWEATHER_HISTORY_DAYS", "10"))),
        model_path=Path(os.getenv("AQI_MODEL_PATH", "aqi_linear_model.pkl")),
        feature_columns_path=Path(os.getenv("AQI_FEATURE_COLUMNS_PATH", "feature_columns.pkl")),
        city_day_path=Path(os.getenv("AQI_CITY_DAY_PATH", "city_day.csv")),
        cache_dir=Path(os.getenv("AQI_CACHE_DIR", "cache")),
    )
