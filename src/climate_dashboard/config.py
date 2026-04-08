"""Shared project settings."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
RAW_LOCATIONS_PATH = RAW_DATA_DIR / "locations.csv"
RAW_WEATHER_PATH = RAW_DATA_DIR / "weather_daily.csv"
RAW_AIR_QUALITY_PATH = RAW_DATA_DIR / "air_quality_hourly.csv"
PROCESSED_FEATURES_PATH = PROCESSED_DATA_DIR / "city_day_features.csv"

GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"
HISTORICAL_WEATHER_API_URL = "https://archive-api.open-meteo.com/v1/archive"
AIR_QUALITY_API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

DEFAULT_CITIES = [
    "Karachi",
    "Lahore",
    "Dubai",
    "London",
    "Singapore",
]

WEATHER_DAILY_FIELDS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "rain_sum",
    "windspeed_10m_max",
]

AIR_QUALITY_HOURLY_FIELDS = [
    "pm2_5",
    "pm10",
    "nitrogen_dioxide",
    "ozone",
    "us_aqi",
]

MONTH_ORDER = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]
