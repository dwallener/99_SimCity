# PLAN_001: Simulated Greater Vancouver Movement Map

This plan covers the first usable version of `99_SimCity`: a Streamlit/Pydeck app that visualizes simulated Greater Vancouver movement over a two-week window using H3 hourly aggregates.

## Goals

- Generate 25,000 simulated residents for Greater Vancouver.
- Use the Milkcrate POI layer as the destination source once available.
- Simulate two weeks of movement with varied resident schedules.
- Store event-level movement at H3 r10.
- Aggregate to hourly H3 frames at r6, r7, r8, r9, and r10.
- Render a responsive Streamlit map with time controls and zoom-aware H3 display.

## Non-Goals For The First Pass

- Do not model full road-network routing.
- Do not ingest real ping shards yet.
- Do not require a database service.
- Do not optimize for Cloudflare deployment until the local app is useful.
- Do not chase perfect demographic realism.

## Step 1: Project Skeleton

Create the basic Python project:

```text
app.py
pyproject.toml
simcity/
scripts/
data/
```

Expected dependencies:

- `streamlit`
- `pydeck`
- `duckdb`
- `polars` or `pandas`
- `pyarrow`
- `h3`
- `numpy`

## Step 2: POI Layer Intake

Once the POI layer is copied into `/Volumes/SillyGoose/milkcrate_2`, inspect its schema and identify the useful columns.

Minimum desired fields:

```text
poi_id
name
amenity or category
lat
lon
h3_r10 or geometry/cell cover
municipality optional
```

Create a normalized local POI parquet:

```text
data/processed_poi/poi_vancouver.parquet
```

If the POI layer is delayed, create a tiny fallback anchor dataset so the simulator and app can still be built.

## Step 3: Geography Definition

Define the initial Greater Vancouver simulation bounds and weighted home anchors.

Initial area set:

- Vancouver
- Burnaby
- Richmond
- North Vancouver
- New Westminster
- Surrey
- Coquitlam

Output:

```text
data/residents/home_anchors.parquet
```

## Step 4: Resident Generation

Generate 25,000 residents with:

```text
resident_id
home_lat
home_lon
home_h3_r10
schedule_profile
mobility_mode
work_or_study_poi_id optional
preferred_activity_mix
```

Schedule profiles:

- standard weekday commuter
- early shift worker
- late shift worker
- night shift worker
- part-time worker
- hybrid worker
- remote worker
- student
- local retiree
- tourist or visitor

Output:

```text
data/residents/residents_25k.parquet
```

## Step 5: Movement Simulation

Simulate 14 days of movement.

Rules:

- Generate events every 5-15 minutes while active.
- Include dwell periods at home, work, school, POI, and errands.
- Add schedule jitter so movement is not synchronized.
- Include weekend and evening behavior.
- Store every event at r10.

Output:

```text
data/simulated_events/events_25k_14d.parquet
```

Expected columns:

```text
resident_id
timestamp
lat
lon
h3_r10
activity_type
destination_type
poi_id
```

## Step 6: H3 Hourly Aggregation

Aggregate event rows into hourly H3 frames for display.

Output:

```text
data/h3_aggregates/h3_hourly_25k_14d.parquet
```

Expected columns:

```text
hour
h3_resolution
h3_cell
resident_count
ping_count
dwell_count
dominant_activity_type
```

Generate rows for r6-r10 so the app can switch resolution without recomputing.

## Step 7: Streamlit App

Build the first app with:

- map viewport centered on Greater Vancouver
- time slider with 336 hourly frames
- play/pause control
- metric selector: resident count or ping count
- zoom-aware H3 resolution
- H3 color intensity
- optional H3 elevation
- hover tooltip for cell, count, and dominant activity
- optional POI overlay toggle

The app should read aggregate parquet, not raw events.

## Step 8: Validation

Run basic checks:

- resident count equals 25,000
- event timestamps cover 14 days
- hourly aggregate has 336 available hours
- all H3 display resolutions r6-r10 are present
- busiest cells are plausible for the POI and anchor setup
- app loads quickly enough for local iteration

## Step 9: Deployment Notes

Cloudflare serving is later. For now, keep the app local and reproducible.

When the local app is useful, evaluate:

- Streamlit Community Cloud, container, or self-hosted app behind Cloudflare Tunnel
- static aggregate snapshots versus dynamic server-side filtering
- cache strategy for hourly frames
- whether DuckDB-backed local parquet reads are sufficient
