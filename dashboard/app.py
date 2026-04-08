"""Streamlit entry point for the portfolio dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from climate_dashboard.config import MONTH_ORDER
from climate_dashboard.pipeline import ensure_project_data

METRIC_LABELS = {
    "temperature_2m_max": "Max Temperature (C)",
    "precipitation_sum": "Precipitation (mm)",
    "windspeed_10m_max": "Wind Speed (km/h)",
    "us_aqi_avg": "Average U.S. AQI",
    "pm2_5_avg": "PM2.5 (ug/m3)",
}


@st.cache_data(show_spinner=False)
def load_dashboard_data(refresh: bool = False) -> pd.DataFrame:
    return ensure_project_data(refresh=refresh)


def format_compact(value: float) -> str:
    return f"{value:,.1f}"


st.set_page_config(page_title="City Climate Explorer", layout="wide")

st.title("City Climate and Air Quality Explorer")
st.caption(
    "A lightweight portfolio dashboard built with public Open-Meteo weather and air-quality APIs."
)

with st.sidebar:
    st.header("Controls")
    refresh_data = st.button("Refresh Public Data", use_container_width=True)

try:
    if refresh_data:
        st.cache_data.clear()
        with st.spinner("Fetching the latest public data from Open-Meteo..."):
            dataset = load_dashboard_data(refresh=True)
    else:
        dataset = load_dashboard_data()
except FileNotFoundError:
    st.info("No cached dataset found yet. Use the sidebar button to fetch public data.")
    st.stop()

available_cities = sorted(dataset["city"].unique().tolist())
default_cities = available_cities[: min(3, len(available_cities))]

with st.sidebar:
    selected_cities = st.multiselect(
        "Cities",
        options=available_cities,
        default=default_cities,
    )
    selected_metric = st.selectbox(
        "Primary metric",
        options=list(METRIC_LABELS),
        format_func=lambda metric: METRIC_LABELS[metric],
    )
    min_date = dataset["date"].min().date()
    max_date = dataset["date"].max().date()
    date_range = st.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

if len(date_range) != 2:
    st.warning("Please select both a start and end date.")
    st.stop()

filtered = dataset[
    dataset["city"].isin(selected_cities)
    & dataset["date"].between(pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))
].copy()

if filtered.empty:
    st.warning("No data matches the current filters.")
    st.stop()

summary_by_city = filtered.groupby("city", as_index=False).agg(
    avg_max_temp=("temperature_2m_max", "mean"),
    avg_aqi=("us_aqi_avg", "mean"),
    total_precipitation=("precipitation_sum", "sum"),
)

warmest_city = summary_by_city.sort_values("avg_max_temp", ascending=False).iloc[0]
cleanest_air_city = summary_by_city.sort_values("avg_aqi", ascending=True).iloc[0]
wettest_city = summary_by_city.sort_values("total_precipitation", ascending=False).iloc[0]

metric_columns = st.columns(3)
metric_columns[0].metric(
    "Warmest City",
    warmest_city["city"],
    f"{format_compact(warmest_city['avg_max_temp'])} C avg max",
)
metric_columns[1].metric(
    "Cleanest Air",
    cleanest_air_city["city"],
    f"{format_compact(cleanest_air_city['avg_aqi'])} AQI avg",
)
metric_columns[2].metric(
    "Wettest City",
    wettest_city["city"],
    f"{format_compact(wettest_city['total_precipitation'])} mm total",
)

line_chart = px.line(
    filtered,
    x="date",
    y=selected_metric,
    color="city",
    title=f"{METRIC_LABELS[selected_metric]} Over Time",
    labels={selected_metric: METRIC_LABELS[selected_metric], "date": "Date"},
)
line_chart.update_layout(legend_title_text="City")

heatmap_source = (
    filtered.groupby(["city", "month_name", "month_number"], as_index=False)[selected_metric]
    .mean()
    .sort_values(["city", "month_number"])
)
heatmap_source["month_name"] = pd.Categorical(
    heatmap_source["month_name"], categories=MONTH_ORDER, ordered=True
)
heatmap_frame = (
    heatmap_source.pivot(index="city", columns="month_name", values=selected_metric)
    .reindex(columns=MONTH_ORDER)
)
heatmap_chart = px.imshow(
    heatmap_frame,
    aspect="auto",
    color_continuous_scale="YlOrRd",
    title=f"Monthly Average {METRIC_LABELS[selected_metric]}",
    labels={"x": "Month", "y": "City", "color": METRIC_LABELS[selected_metric]},
)

distribution_chart = px.box(
    filtered,
    x="city",
    y=selected_metric,
    color="city",
    title=f"Distribution of {METRIC_LABELS[selected_metric]} by City",
    labels={"city": "City", selected_metric: METRIC_LABELS[selected_metric]},
)
distribution_chart.update_layout(showlegend=False)

scatter_source = filtered.dropna(
    subset=["temperature_2m_max", "us_aqi_avg", "precipitation_sum"]
).copy()
scatter_source["bubble_size"] = scatter_source["precipitation_sum"].clip(lower=0.1)
relationship_chart = px.scatter(
    scatter_source,
    x="temperature_2m_max",
    y="us_aqi_avg",
    color="city",
    size="bubble_size",
    hover_data=["date", "pm2_5_avg", "ozone_avg"],
    title="Temperature vs. AQI Relationship",
    labels={
        "temperature_2m_max": "Max Temperature (C)",
        "us_aqi_avg": "Average U.S. AQI",
        "bubble_size": "Precipitation (mm)",
    },
)

top_row = st.columns(2)
top_row[0].plotly_chart(line_chart, use_container_width=True)
top_row[1].plotly_chart(heatmap_chart, use_container_width=True)

bottom_row = st.columns(2)
bottom_row[0].plotly_chart(distribution_chart, use_container_width=True)
bottom_row[1].plotly_chart(relationship_chart, use_container_width=True)

st.subheader("Data notes")
st.markdown(
    """
    - Weather data comes from the Open-Meteo Historical Weather API.
    - Air quality data comes from the Open-Meteo Air Quality API.
    - City coordinates are resolved with the Open-Meteo Geocoding API.
    - The dashboard reads from locally cached CSV files to keep repeat usage lightweight.
    """
)
