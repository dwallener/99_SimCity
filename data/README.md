# Data Directory

Generated simulation artifacts live here and are intentionally ignored by Git.

Rebuild order:

1. `scripts/prepare_poi.py`
2. `scripts/generate_residents.py` or `scripts/downsample_residents.py`
3. `scripts/simulate_movement.py`
4. `scripts/aggregate_h3_timeslices.py`

The Streamlit app reads aggregate parquet files from `data/h3_aggregates/`.
