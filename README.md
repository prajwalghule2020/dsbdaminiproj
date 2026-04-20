# DSBDA Mini Project - AQI Prediction

This repository contains:
- a FastAPI backend that predicts next-day AQI from OpenWeather data
- a Next.js frontend dashboard that calls the backend through a server route

## Repository Layout

- `aqi_api/` - FastAPI service and prediction pipeline
- `aqi_web/` - Next.js frontend
- `cache/` - generated cache files (runtime)
- `city_day.csv`, `city_hour.csv` - dataset files
- `aqi_linear_model.pkl`, `feature_columns.pkl` - trained model artifacts

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm
- OpenWeather API key with air pollution access

## 1) Backend Setup (FastAPI)

1. Create a backend env file (choose one):

   Option A (recommended):
   - Copy `aqi_api/example.env` to `aqi_api/.env`

   Option B:
   - Copy root `example.env` to `.env`

2. Set `OPENWEATHER_API_KEY` in the file you copied.

3. Install Python dependencies from repository root:

   ```bash
   pip install -r requirements.txt
   ```

4. Start backend from repository root:

   ```bash
   uvicorn aqi_api.api:app --reload
   ```

5. Verify backend:
- Health: `http://127.0.0.1:8000/health`
- Predict endpoint: `POST http://127.0.0.1:8000/predict`

## 2) Frontend Setup (Next.js)

1. Copy `aqi_web/example.env` to `aqi_web/.env.local`.
2. Update `AQI_API_BASE_URL` only if your backend is not running on `http://127.0.0.1:8000`.
3. Install dependencies:

   ```bash
   cd aqi_web
   npm install
   ```

4. Start frontend:

   ```bash
   npm run dev
   ```

5. Open `http://localhost:3000`.

## Environment Variables

### Backend (`aqi_api/.env` or root `.env`)

- `OPENWEATHER_API_KEY` (required)
- `OPENWEATHER_BASE_URL` (optional)
- `OPENWEATHER_GEOCODING_BASE_URL` (optional)
- `OPENWEATHER_TIMEOUT_SECONDS` (optional)
- `OPENWEATHER_HISTORY_DAYS` (optional, minimum enforced: 8)
- `AQI_MODEL_PATH` (optional)
- `AQI_FEATURE_COLUMNS_PATH` (optional)
- `AQI_CITY_DAY_PATH` (optional)
- `AQI_CACHE_DIR` (optional)

### Frontend (`aqi_web/.env.local`)

- `AQI_API_BASE_URL` (optional, default in code is `http://127.0.0.1:8000`)

## Notes

- Backend settings load order is:
  1. `aqi_api/.env`
  2. root `.env`

  Variables already set from `aqi_api/.env` are not overridden by root `.env`.
- If OpenWeather history access is limited, the backend falls back to forecast and fills missing fields from priors.
