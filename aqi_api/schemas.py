"""Pydantic request and response schemas for FastAPI routes."""

from __future__ import annotations

from datetime import date, datetime
from typing import List

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    city: str = Field(..., min_length=1, description="City name, for example Delhi")


class PredictionDiagnostics(BaseModel):
    history_start_utc: datetime
    history_end_utc: datetime
    hourly_rows_used: int
    daily_rows_built: int
    imputed_fields: List[str]


class PredictResponse(BaseModel):
    city: str
    predicted_aqi: float
    category: str
    prediction_for_date: date
    diagnostics: PredictionDiagnostics
