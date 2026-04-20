# AQI Web Frontend

Minimal dark-theme Next.js frontend for AQI next-day prediction.

## Prerequisites

1. FastAPI backend running from the sibling project.
2. Backend OpenWeather key set in the backend environment:
	- OPENWEATHER_API_KEY

## Run

1. Install dependencies:
```bash
npm install
```

2. Configure backend URL (optional, default is already http://127.0.0.1:8000):
```powershell
$env:AQI_API_BASE_URL="http://127.0.0.1:8000"
```

3. Start frontend dev server:
```bash
npm run dev
```

4. Open:
http://localhost:3000

## Notes

- The browser calls Next route handler at app/api/predict/route.ts.
- Route handler forwards requests to FastAPI /predict endpoint.
- This avoids browser CORS issues for local development.
