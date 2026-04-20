"""FastAPI entrypoint for next-day AQI prediction."""

from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI, HTTPException

from .config import load_settings
from .openweather import OpenWeatherClientError
from .schemas import PredictRequest, PredictResponse
from .service import AQIPredictionService


app = FastAPI(
    title="AQI Next-Day Predictor",
    version="0.1.0",
    description=(
        "Fetches OpenWeather air pollution history (with forecast fallback for limited plans), "
        "rebuilds the training-time feature pipeline, and predicts next-day AQI using a "
        "saved LinearRegression model."
    ),
)


@lru_cache(maxsize=1)
def get_service() -> AQIPredictionService:
    settings = load_settings()
    return AQIPredictionService(settings)


@app.get("/health")
def health() -> dict:
    try:
        service = get_service()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "status": "ok",
        "model_loaded": True,
        "feature_count": len(service.predictor.feature_columns),
    }


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest) -> PredictResponse:
    try:
        response_payload = get_service().predict_next_day(payload.city)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OpenWeatherClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc

    return PredictResponse(**response_payload)
