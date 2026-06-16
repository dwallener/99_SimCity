# 99_SimCity

`99_SimCity` is a sandbox for building a live map-style simulation of movement through Greater Vancouver. The immediate goal is to prototype the visualization and interaction model with simulated people while the real monthly ping pipeline is running.

The later goal is to reuse the same map and aggregation machinery with real ping-derived movement data.

## What We Are Building

We want an interactive map window where we can:

- pan and zoom around Greater Vancouver
- watch simulated people move over a two-week window
- aggregate movement into H3 cells at a resolution that fits the current zoom level
- play, pause, scrub, and step through time in hourly increments
- visualize traffic intensity with color and/or height
- inspect cells, agents, and hotspots
- overlay POI and amenities to explain busy areas

The first implementation target is Streamlit with Pydeck/Deck.gl. Streamlit gives us fast iteration and simple controls; Deck.gl gives us map layers, H3 hex rendering, and optional 3D elevation.

## Initial Decisions

- Geography: Greater Vancouver core, including Vancouver, Burnaby, Richmond, North Vancouver, New Westminster, Surrey, and Coquitlam.
- Starting population: 25,000 simulated residents.
- Time window: 14 days.
- Viewer step: 1 hour.
- Simulation event cadence: 5-15 minutes, aggregated to hourly frames for the app.
- Internal location resolution: H3 r10, because this lines up with POI-scale matching.
- Display resolutions: r6-r10, selected by zoom level.
- POI source: use the Milkcrate POI layer once it is copied into this project area.

## Why Simulated Movement First

The real ping data is large and still being cleaned into reusable pipeline artifacts. Starting with simulated agents lets us design the user experience and data contracts without waiting on heavy batch jobs.

The simulated data should still look like the real system we plan to plug in later:

```text
movement events
  resident_id
  timestamp
  lat
  lon
  h3_r10
  activity_type
  destination_type
  poi_id optional

      ->

time-sliced H3 aggregates
  hour
  h3_resolution
  h3_cell
  resident_count
  ping_count
  dwell_count optional
  dominant_activity_type optional

      ->

interactive map layers
  H3 traffic layer
  optional agent traces
  optional POI / amenity layer
```

## Resident Model

Residents should be generated from behavior profiles rather than as purely random walkers. The purpose is not perfect realism; it is plausible aggregate movement.

Each resident should have:

- `resident_id`
- home location
- home H3 r10
- schedule profile
- mobility mode
- optional work or study location
- local activity preferences
- POI affinity profile

Initial schedule profiles:

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

Schedules should include variance:

- departure and return jitter
- missed trips
- stay-home days
- errands before or after work
- weekend behavior
- evening and overnight activity

## Geography And POI

Homes should be distributed across Greater Vancouver using weighted area anchors. The first version can use hand-defined neighborhood anchors for home distribution, but destinations should use the POI layer where possible.

The POI layer should provide destination candidates for:

- workplaces and offices
- campuses
- hospitals and medical areas
- retail centers
- food and drink
- parks and recreation
- transit hubs
- nightlife areas
- hotels and tourist destinations

If the POI layer is not available during the first coding pass, the simulator should support a small fallback seed file so the rest of the pipeline can still be built.

## H3 Strategy

Store simulated events at r10:

```text
lat
lon
h3_r10
```

During aggregation, derive parent cells for display:

```text
r10 -> r9 -> r8 -> r7 -> r6
```

Initial zoom mapping:

```text
zoom <= 8      r6
zoom 9-10      r7
zoom 11-12     r8
zoom 13-14     r9
zoom >= 15     r10
```

The app should render pre-aggregated hourly frames rather than raw event rows.

## Later Real-Data Integration

After the real data pipeline is ready, this project should be able to consume derived artifacts from Milkcrate, likely including:

- active-device filtered ping shards
- Q1 spatial layer outputs
- homed device outputs
- device-to-postal weights
- POI / amenity cover layers

The same UI should then support real traffic summaries by H3 cell and time window.

## Design Principles

Keep the simulation, aggregation, and visualization layers separate.

The simulator should emit movement events. The aggregator should convert events to H3/time summaries. The app should only read prepared simulation or aggregate outputs and render them.

Avoid pointing Streamlit directly at huge raw ping data. The app should use small, purpose-built datasets suitable for interactive loading.

Prefer simple files and reproducible scripts at first. A database can come later if the working set becomes too large for local parquet iteration.

## Candidate Project Layout

```text
99_SimCity/
  README.md
  PLAN_001.md
  app.py
  pyproject.toml
  data/
    raw_poi/
    processed_poi/
    residents/
    simulated_events/
    h3_aggregates/
  scripts/
    inspect_poi_layer.py
    generate_residents.py
    simulate_movement.py
    aggregate_h3_timeslices.py
  simcity/
    __init__.py
    config.py
    geography.py
    poi.py
    residents.py
    schedules.py
    movement.py
    h3_aggregate.py
```

## Near-Term Plan

See `PLAN_001.md`.
