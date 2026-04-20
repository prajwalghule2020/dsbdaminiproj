"""Shared constants used across AQI prediction modules."""

POLLUTANT_COLUMNS = [
    "PM2.5",
    "PM10",
    "NO",
    "NO2",
    "NOx",
    "NH3",
    "CO",
    "SO2",
    "O3",
    "Benzene",
    "Toluene",
    "Xylene",
]

AROMATIC_COLUMNS = ["Benzene", "Toluene", "Xylene"]

OPENWEATHER_COMPONENT_MAP = {
    "pm2_5": "PM2.5",
    "pm10": "PM10",
    "no": "NO",
    "no2": "NO2",
    "nh3": "NH3",
    "co": "CO",
    "so2": "SO2",
    "o3": "O3",
}

LAG_DAYS = 7
