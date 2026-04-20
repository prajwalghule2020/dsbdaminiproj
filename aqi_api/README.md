# AQI FastAPI Service

## Purpose
This service fetches OpenWeather Air Pollution hourly data, aggregates it into 24-hour daily averages, rebuilds the same lag/time features used in training, and predicts next-day AQI using:
- `aqi_linear_model.pkl`
- `feature_columns.pkl`

If your API key cannot access `air_pollution/history`, the service automatically falls back to
`air_pollution/forecast` and fills any feature gaps from local city priors in `city_day.csv`.

The backend auto-loads `aqi_api/.env` (and project-root `.env`) during settings initialization.

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set required environment variable:
   ```bash
   set OPENWEATHER_API_KEY=your_api_key_here
   ```
   On PowerShell:
   ```powershell
   $env:OPENWEATHER_API_KEY="your_api_key_here"
   ```
   Or put it in `aqi_api/.env`:
   ```dotenv
   OPENWEATHER_API_KEY=your_api_key_here
   ```

## Run
```bash
uvicorn aqi_api.api:app --reload --env-file aqi_api/.env
```

Plain startup also works now:
```bash
uvicorn aqi_api.api:app --reload
```

## Endpoint
- `POST /predict`

Request body:
```json
{
  "city": "Delhi"
}
```

Response includes:
- predicted next-day AQI
- CPCB category
- diagnostics (history window, rows used, imputed pollutant fields)
