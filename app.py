from __future__ import annotations

from pathlib import Path
import time

import duckdb
import pandas as pd
import pydeck as pdk
import streamlit as st


ROOT = Path(__file__).resolve().parent
AGG_DIR = ROOT / "data" / "h3_aggregates"
POI_PATH = ROOT / "data" / "processed_poi" / "poi_vancouver.parquet"


@st.cache_data(show_spinner=False)
def load_hours(path: Path) -> list[pd.Timestamp]:
    con = duckdb.connect()
    rows = con.execute(
        f"""
        SELECT DISTINCT hour
        FROM read_parquet('{sql_literal(path.as_posix())}')
        ORDER BY hour
        """
    ).fetchall()
    return [pd.Timestamp(row[0]) for row in rows]


@st.cache_data(show_spinner=False)
def load_frame(path: Path, hour_iso: str, resolution: int) -> pd.DataFrame:
    hour = pd.Timestamp(hour_iso)
    aggregate_sql = sql_literal(path.as_posix())
    hour_sql = sql_literal(hour.isoformat(sep=" "))
    con = duckdb.connect()
    return con.execute(
        f"""
        SELECT *
        FROM read_parquet('{aggregate_sql}')
        WHERE hour = TIMESTAMP '{hour_sql}'
          AND h3_resolution = {int(resolution)}
        """
    ).fetchdf()


@st.cache_data(show_spinner=False)
def load_localities(path: Path) -> list[str]:
    if not path.exists():
        return []
    poi = pd.read_parquet(path, columns=["locality"])
    values = sorted(value for value in poi["locality"].dropna().unique().tolist() if value)
    return ["All Metro Vancouver", *values]


@st.cache_data(show_spinner=False)
def load_poi(path: Path, focus_area: str) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    poi = pd.read_parquet(path)
    columns = ["name", "category_primary", "category_class", "lat", "lon", "locality"]
    poi = poi[columns].dropna(subset=["lat", "lon"])
    if focus_area != "All Metro Vancouver":
        poi = poi[poi["locality"] == focus_area]
    if len(poi) > 5000:
        poi = poi.sample(n=5000, random_state=99)
    return poi


def resolution_for_zoom(zoom: float) -> int:
    if zoom <= 8:
        return 6
    if zoom <= 10:
        return 7
    if zoom <= 12:
        return 8
    if zoom <= 14:
        return 9
    return 10


def clamp_hour_index(value: object, max_index: int) -> int:
    try:
        if isinstance(value, list):
            value = value[0]
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 8
    return max(0, min(parsed, max_index))


def event_path_for_aggregate(aggregate_path: Path) -> Path:
    suffix = aggregate_path.name.removeprefix("h3_hourly_")
    return ROOT / "data" / "simulated_events" / f"events_{suffix}"


def sql_literal(value: str) -> str:
    return value.replace("'", "''")


@st.cache_data(show_spinner=False)
def load_hour_activity(
    events_path: str,
    poi_path: str,
    hour_iso: str,
    focus_area: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    events = Path(events_path)
    poi = Path(poi_path)
    if not events.exists() or not poi.exists():
        return pd.DataFrame(), pd.DataFrame()

    hour = pd.Timestamp(hour_iso)
    next_hour = hour + pd.Timedelta(hours=1)
    hour_sql = sql_literal(hour.isoformat(sep=" "))
    next_hour_sql = sql_literal(next_hour.isoformat(sep=" "))
    events_sql = sql_literal(events.as_posix())
    poi_sql = sql_literal(poi.as_posix())
    locality_filter = ""
    if focus_area != "All Metro Vancouver":
        locality_filter = f"AND p.locality = '{sql_literal(focus_area)}'"

    con = duckdb.connect()
    top_poi = con.execute(
        f"""
        SELECT
          COALESCE(p.name, 'Unknown') AS name,
          COALESCE(p.category_primary, 'unknown') AS category,
          COALESCE(p.locality, '') AS locality,
          COUNT(DISTINCT e.resident_id) AS residents,
          COUNT(*) AS pings
        FROM read_parquet('{events_sql}') e
        LEFT JOIN read_parquet('{poi_sql}') p
          ON e.poi_id = p.poi_id
        WHERE e.timestamp >= TIMESTAMP '{hour_sql}'
          AND e.timestamp < TIMESTAMP '{next_hour_sql}'
          AND e.poi_id IS NOT NULL
          {locality_filter}
        GROUP BY 1, 2, 3
        ORDER BY residents DESC, pings DESC, name ASC
        LIMIT 10
        """
    ).fetchdf()
    top_amenities = con.execute(
        f"""
        SELECT
          COALESCE(p.category_class, e.destination_type, 'unknown') AS amenity,
          COUNT(DISTINCT e.resident_id) AS residents,
          COUNT(*) AS pings
        FROM read_parquet('{events_sql}') e
        LEFT JOIN read_parquet('{poi_sql}') p
          ON e.poi_id = p.poi_id
        WHERE e.timestamp >= TIMESTAMP '{hour_sql}'
          AND e.timestamp < TIMESTAMP '{next_hour_sql}'
          AND e.destination_type NOT IN ('home', 'travel')
          {locality_filter}
        GROUP BY 1
        ORDER BY residents DESC, pings DESC, amenity ASC
        LIMIT 10
        """
    ).fetchdf()
    return top_poi, top_amenities


st.set_page_config(page_title="Metro Vancouver Movement", layout="wide")
st.title("Metro Vancouver Movement")

aggregate_files = sorted(AGG_DIR.glob("h3_hourly_*.parquet"))
if not aggregate_files:
    st.error(f"Missing aggregate data under: {AGG_DIR}")
    st.stop()
default_aggregate_index = max(
    range(len(aggregate_files)),
    key=lambda index: aggregate_files[index].stat().st_mtime,
)

with st.sidebar:
    selected_aggregate = st.selectbox(
        "Aggregate dataset",
        aggregate_files,
        index=default_aggregate_index,
        format_func=lambda path: path.name,
    )
    localities = load_localities(POI_PATH)
    focus_area = st.selectbox(
        "Focus area",
        localities or ["All Metro Vancouver"],
        index=0,
    )

hours = load_hours(selected_aggregate)
if not hours:
    st.error("Aggregate file has no hours.")
    st.stop()

with st.sidebar:
    default_hour_index = clamp_hour_index(st.query_params.get("hour"), len(hours) - 1)
    hour_index = st.slider(
        "Hour",
        0,
        len(hours) - 1,
        value=default_hour_index,
        key=f"hour_slider_{default_hour_index}",
    )
    col_play, col_stop = st.columns(2)
    if "playing" not in st.session_state:
        st.session_state.playing = False
    if col_play.button("Play", width="stretch"):
        st.session_state.playing = True
    if col_stop.button("Stop", width="stretch"):
        st.session_state.playing = False
    playback_delay = st.slider("Playback delay", 0.1, 2.0, 0.5, 0.1)
    zoom = st.slider("Zoom model", 6.0, 16.0, 10.5, 0.5)
    resolution = st.selectbox(
        "H3 resolution",
        [6, 7, 8, 9, 10],
        index=[6, 7, 8, 9, 10].index(resolution_for_zoom(zoom)),
    )
    metric = st.selectbox("Metric", ["resident_count", "ping_count", "dwell_count"])
    show_poi = st.checkbox("Show POI sample", value=False)
    elevation_scale = st.slider("Elevation scale", 0, 250, 120)

selected_hour = pd.Timestamp(hours[hour_index])
if str(hour_index) != st.query_params.get("hour"):
    st.query_params["hour"] = str(hour_index)

frame = load_frame(selected_aggregate, selected_hour.isoformat(sep=" "), resolution)
if frame.empty:
    st.warning("No cells for selected hour/resolution.")
    st.stop()

max_value = max(float(frame[metric].max()), 1.0)
frame["value"] = frame[metric].astype(float)
frame["fill_color"] = frame["value"].map(
    lambda value: [255, int(max(40, 220 - 170 * value / max_value)), 60, 170]
)

layers = [
    pdk.Layer(
        "H3HexagonLayer",
        data=frame,
        get_hexagon="h3_cell",
        get_fill_color="fill_color",
        get_elevation="value",
        elevation_scale=elevation_scale,
        elevation_range=[0, 3000],
        extruded=True,
        pickable=True,
        coverage=0.92,
    )
]

if show_poi:
    poi = load_poi(POI_PATH, focus_area)
    if not poi.empty:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=poi,
                get_position=["lon", "lat"],
                get_radius=35,
                get_fill_color=[30, 90, 210, 120],
                pickable=True,
            )
        )

view_state = pdk.ViewState(latitude=49.245, longitude=-123.04, zoom=float(zoom), pitch=45, bearing=0)
deck = pdk.Deck(
    map_style="light",
    initial_view_state=view_state,
    layers=layers,
    tooltip={
        "html": (
            "<b>H3:</b> {h3_cell}<br/>"
            "<b>Residents:</b> {resident_count}<br/>"
            "<b>Pings:</b> {ping_count}<br/>"
            "<b>Dwell:</b> {dwell_count}<br/>"
            "<b>Dominant:</b> {dominant_activity_type}"
        )
    },
)

main_col, side_col = st.columns([4.2, 1.25], gap="large")
with main_col:
    st.caption(f"{selected_hour} | r{resolution} | {len(frame):,} cells | metric: {metric}")
    st.pydeck_chart(deck, width="stretch", height=760)

with side_col:
    st.subheader("Top POI")
    events_path = event_path_for_aggregate(selected_aggregate)
    top_poi, top_amenities = load_hour_activity(
        events_path.as_posix(),
        POI_PATH.as_posix(),
        selected_hour.isoformat(sep=" "),
        focus_area,
    )
    if top_poi.empty:
        st.caption("No POI activity for this hour/focus area.")
    else:
        st.dataframe(
            top_poi.rename(
                columns={
                    "name": "POI",
                    "category": "Category",
                    "locality": "Area",
                    "residents": "Residents",
                    "pings": "Pings",
                }
            ),
            hide_index=True,
            width="stretch",
            height=300,
        )

    st.subheader("Top Amenities")
    if top_amenities.empty:
        st.caption("No amenity activity for this hour/focus area.")
    else:
        st.dataframe(
            top_amenities.rename(
                columns={
                    "amenity": "Amenity",
                    "residents": "Residents",
                    "pings": "Pings",
                }
            ),
            hide_index=True,
            width="stretch",
            height=260,
        )

if st.session_state.playing:
    time.sleep(playback_delay)
    st.query_params["hour"] = str((hour_index + 1) % len(hours))
    st.rerun()
