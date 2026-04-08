"""Data ingestion and transformation pipeline for the dashboard."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests

from climate_dashboard.config import (
    AIR_QUALITY_API_URL,
    AIR_QUALITY_HOURLY_FIELDS,
    DEFAULT_CITIES,
    GEOCODING_API_URL,
    HISTORICAL_WEATHER_API_URL,
    PROCESSED_FEATURES_PATH,
    RAW_AIR_QUALITY_PATH,
    RAW_LOCATIONS_PATH,
    RAW_WEATHER_PATH,
    WEATHER_DAILY_FIELDS,
)

REQUEST_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class Location:
    """Normalized city metadata used across the project."""

    city: str
    country: str
    latitude: float
    longitude: float
    timezone: str


def _request_json(url: str, params: dict[str, object]) -> dict[str, object]:
    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def geocode_city(city_name: str) -> Location:
    """Resolve a city name into coordinates and timezone metadata."""

    payload = _request_json(
        GEOCODING_API_URL,
        {
            "name": city_name,
            "count": 1,
            "language": "en",
            "format": "json",
        },
    )
    results = payload.get("results", [])
    if not results:
        raise ValueError(f"City lookup returned no results for '{city_name}'.")

    best_match = results[0]
    return Location(
        city=city_name,
        country=best_match.get("country", "Unknown"),
        latitude=best_match["latitude"],
        longitude=best_match["longitude"],
        timezone=best_match.get("timezone", "auto"),
    )


def build_location_table(cities: Iterable[str]) -> pd.DataFrame:
    locations = [asdict(geocode_city(city_name)) for city_name in cities]
    return pd.DataFrame(locations)


def fetch_weather_daily(location: Location, start_date: date, end_date: date) -> pd.DataFrame:
    """Fetch daily weather metrics for a single location."""

    payload = _request_json(
        HISTORICAL_WEATHER_API_URL,
        {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": ",".join(WEATHER_DAILY_FIELDS),
            "timezone": location.timezone,
        },
    )

    daily_frame = pd.DataFrame(payload["daily"]).rename(columns={"time": "date"})
    daily_frame["date"] = pd.to_datetime(daily_frame["date"])
    daily_frame["city"] = location.city
    daily_frame["country"] = location.country
    daily_frame["latitude"] = location.latitude
    daily_frame["longitude"] = location.longitude
    daily_frame["timezone"] = location.timezone
    return daily_frame


def fetch_air_quality_hourly(location: Location, start_date: date, end_date: date) -> pd.DataFrame:
    """Fetch hourly air quality metrics for a single location."""

    payload = _request_json(
        AIR_QUALITY_API_URL,
        {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "hourly": ",".join(AIR_QUALITY_HOURLY_FIELDS),
            "timezone": location.timezone,
        },
    )

    hourly_frame = pd.DataFrame(payload["hourly"]).rename(columns={"time": "timestamp"})
    hourly_frame["timestamp"] = pd.to_datetime(hourly_frame["timestamp"])
    hourly_frame["city"] = location.city
    hourly_frame["country"] = location.country
    hourly_frame["latitude"] = location.latitude
    hourly_frame["longitude"] = location.longitude
    hourly_frame["timezone"] = location.timezone
    return hourly_frame


def aggregate_air_quality_daily(hourly_frame: pd.DataFrame) -> pd.DataFrame:
    """Convert hourly AQ metrics into daily features for dashboarding."""

    if hourly_frame.empty:
        return hourly_frame.copy()

    daily_frame = hourly_frame.copy()
    daily_frame["date"] = daily_frame["timestamp"].dt.floor("D")

    aggregated = (
        daily_frame.groupby(
            ["city", "country", "latitude", "longitude", "timezone", "date"],
            as_index=False,
        )
        .agg(
            pm2_5_avg=("pm2_5", "mean"),
            pm10_avg=("pm10", "mean"),
            nitrogen_dioxide_avg=("nitrogen_dioxide", "mean"),
            ozone_avg=("ozone", "mean"),
            us_aqi_avg=("us_aqi", "mean"),
            us_aqi_peak=("us_aqi", "max"),
        )
        .sort_values(["city", "date"])
    )
    return aggregated


def build_feature_dataset(weather_frame: pd.DataFrame, air_quality_frame: pd.DataFrame) -> pd.DataFrame:
    """Merge weather and air quality data into one daily analytical table."""

    air_quality_daily = aggregate_air_quality_daily(air_quality_frame)
    merged = weather_frame.merge(
        air_quality_daily,
        on=["city", "country", "latitude", "longitude", "timezone", "date"],
        how="left",
    ).sort_values(["city", "date"])

    merged["temperature_range"] = (
        merged["temperature_2m_max"] - merged["temperature_2m_min"]
    )
    merged["rolling_temp_7d"] = (
        merged.groupby("city")["temperature_2m_max"]
        .transform(lambda series: series.rolling(7, min_periods=1).mean())
    )
    merged["rolling_aqi_7d"] = (
        merged.groupby("city")["us_aqi_avg"]
        .transform(lambda series: series.rolling(7, min_periods=1).mean())
    )
    merged["month_name"] = merged["date"].dt.strftime("%b")
    merged["month_number"] = merged["date"].dt.month
    merged["year"] = merged["date"].dt.year
    merged["is_rainy_day"] = merged["precipitation_sum"].fillna(0).gt(0).astype(int)
    return merged


def _write_csv(frame: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)


def build_project_data(
    cities: list[str] | None = None,
    lookback_days: int = 365,
) -> pd.DataFrame:
    """Fetch public API data, save intermediate files, and return the final dataset."""

    selected_cities = cities or DEFAULT_CITIES
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=lookback_days - 1)

    locations_frame = build_location_table(selected_cities)
    locations = [Location(**row) for row in locations_frame.to_dict(orient="records")]

    weather_frames = []
    air_quality_frames = []
    for location in locations:
        weather_frames.append(fetch_weather_daily(location, start_date, end_date))
        air_quality_frames.append(fetch_air_quality_hourly(location, start_date, end_date))

    weather_frame = pd.concat(weather_frames, ignore_index=True)
    air_quality_frame = pd.concat(air_quality_frames, ignore_index=True)
    feature_frame = build_feature_dataset(weather_frame, air_quality_frame)

    _write_csv(locations_frame, RAW_LOCATIONS_PATH)
    _write_csv(weather_frame, RAW_WEATHER_PATH)
    _write_csv(air_quality_frame, RAW_AIR_QUALITY_PATH)
    _write_csv(feature_frame, PROCESSED_FEATURES_PATH)

    return feature_frame


def load_processed_dataset() -> pd.DataFrame:
    """Load the transformed dataset from disk."""

    if not PROCESSED_FEATURES_PATH.exists():
        raise FileNotFoundError(
            "No processed dataset found yet. Run the data pipeline first."
        )

    frame = pd.read_csv(PROCESSED_FEATURES_PATH, parse_dates=["date"])
    return frame.sort_values(["city", "date"])


def ensure_project_data(
    refresh: bool = False,
    cities: list[str] | None = None,
    lookback_days: int = 365,
) -> pd.DataFrame:
    """Load cached data when available, or fetch fresh data on demand."""

    if refresh or not PROCESSED_FEATURES_PATH.exists():
        return build_project_data(cities=cities, lookback_days=lookback_days)
    return load_processed_dataset()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Open-Meteo data for the dashboard.")
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=365,
        help="Number of days of history to fetch per city.",
    )
    parser.add_argument(
        "--city",
        action="append",
        dest="cities",
        help="Override the default city list by passing --city multiple times.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset = build_project_data(cities=args.cities, lookback_days=args.lookback_days)
    print(
        f"Saved {len(dataset):,} daily rows to {PROCESSED_FEATURES_PATH.relative_to(Path.cwd())}."
    )


if __name__ == "__main__":
    main()
