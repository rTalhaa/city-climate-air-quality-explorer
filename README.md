# City Climate and Air Quality Explorer

This project is a small data science portfolio piece focused on clean data collection, lightweight analysis, and strong dashboard visuals.

## Why this project

- Public data only: Open-Meteo provides free geocoding, historical weather, and air-quality APIs.
- Low resource usage: we will fetch a small list of cities and cache the results locally.
- Strong portfolio signal: the project will include a reproducible pipeline, clear visuals, and an interactive dashboard.

## Project goal

Build a dashboard that lets a user compare a handful of cities across:

- temperature trends
- precipitation patterns
- wind conditions
- air quality metrics
- weather vs. AQI relationships

## Planned visuals

- multi-city trend comparisons
- monthly heatmaps
- rolling averages
- distribution plots
- scatter plots for weather and AQI relationships

## Data sources

- Open-Meteo Geocoding API
- Open-Meteo Historical Weather API
- Open-Meteo Air Quality API

## Project structure

```text
.
|-- dashboard/
|-- data/
|   |-- processed/
|   `-- raw/
|-- notebooks/
`-- src/
    `-- climate_dashboard/
```

## Delivery plan

1. Scaffold the repo and environment.
2. Build a small ingestion pipeline with caching.
3. Transform and combine weather and AQI data.
4. Create a dashboard with polished visualizations.
5. Document setup, decisions, and results.

## Quick start

```powershell
uv python install 3.12
uv sync
uv run climate-fetch --lookback-days 365
uv run streamlit run dashboard/app.py
```

## Current implementation

- `src/climate_dashboard/pipeline.py` resolves city coordinates, fetches public weather and air-quality data, and saves local CSV caches.
- `dashboard/app.py` provides an interactive Streamlit dashboard with trend, heatmap, distribution, and relationship views.
- Cached outputs are written to `data/raw/` and `data/processed/` to avoid unnecessary repeated API calls.

## Suggested development cadence

- Session 1: scaffold repo and environment
- Session 2: add data ingestion and caching
- Session 3: add transformations and quality checks
- Session 4: build dashboard visuals
- Session 5: polish docs and screenshots

## Commit plan

We will keep the history clean and realistic with small commits such as:

1. `chore: scaffold climate dashboard project`
2. `feat: add Open-Meteo data ingestion pipeline`
3. `feat: build weather and AQI transformation layer`
4. `feat: add interactive Streamlit dashboard`
5. `docs: document setup, data sources, and project story`

I will avoid fake or backdated commits. A better approach is a recurring reminder to make one intentional commit per work session.
