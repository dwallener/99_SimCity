# Data Directory

Generated simulation artifacts live here and are ignored by Git by default.

The repository intentionally commits the minimum runtime dataset needed by
Streamlit Cloud:

- `processed_poi/poi_vancouver.parquet`
- `simulated_events/events_15k_clean_excluded_14d.parquet`
- `h3_aggregates/h3_hourly_15k_clean_excluded_14d.parquet`

Rebuild order:

1. `scripts/prepare_poi.py`
2. `scripts/generate_residents.py` or `scripts/downsample_residents.py`
3. `scripts/simulate_movement.py`
4. `scripts/aggregate_h3_timeslices.py`

The Streamlit app reads aggregate parquet files from `data/h3_aggregates/`.
