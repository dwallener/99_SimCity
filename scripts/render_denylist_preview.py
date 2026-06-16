#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import h3
import pandas as pd
import pydeck as pdk

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simcity.config import DATA_DIR
from simcity.water import WATER_R7_CELLS


def cell_polygon(cell: str) -> list[list[float]]:
    boundary = h3.cell_to_boundary(cell)
    return [[lon, lat] for lat, lon in boundary]


def feature_for_cell(cell: str, removed_events: int) -> dict:
    lat, lon = h3.cell_to_latlng(cell)
    resolution = h3.get_resolution(cell)
    return {
        "type": "Feature",
        "properties": {
            "h3_cell": cell,
            "resolution": resolution,
            "removed_events": int(removed_events),
            "label": f"r{resolution}\\n{cell}\\n{removed_events:,}",
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [cell_polygon(cell)],
        },
        "centroid": [lon, lat],
    }


def removed_event_counts(events_path: Path, cells: list[str]) -> dict[str, int]:
    if not events_path.exists():
        return {cell: 0 for cell in cells}

    events = pd.read_parquet(events_path, columns=["h3_r10"])
    counts: dict[str, int] = {}
    for cell in cells:
        resolution = h3.get_resolution(cell)
        if resolution == 10:
            mask = events["h3_r10"] == cell
        else:
            mask = events["h3_r10"].map(lambda value: h3.cell_to_parent(str(value), resolution)) == cell
        counts[cell] = int(mask.sum())
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--events",
        default=str(DATA_DIR / "simulated_events" / "events_15k_clean_14d.parquet"),
        help="Optional source event parquet used only to annotate removed-event counts.",
    )
    parser.add_argument(
        "--geojson",
        default=str(DATA_DIR / "diagnostics" / "forbidden_h3_cells.geojson"),
    )
    parser.add_argument(
        "--html",
        default=str(DATA_DIR / "diagnostics" / "forbidden_h3_cells.html"),
    )
    args = parser.parse_args()

    cells = sorted(WATER_R7_CELLS)
    events_path = Path(args.events).expanduser().resolve()
    geojson_path = Path(args.geojson).expanduser().resolve()
    html_path = Path(args.html).expanduser().resolve()
    geojson_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.parent.mkdir(parents=True, exist_ok=True)

    counts = removed_event_counts(events_path, cells)
    features = [feature_for_cell(cell, counts[cell]) for cell in cells]
    geojson = {"type": "FeatureCollection", "features": features}
    geojson_path.write_text(json.dumps(geojson, indent=2), encoding="utf-8")

    polygon_rows = [
        {
            "h3_cell": feature["properties"]["h3_cell"],
            "resolution": feature["properties"]["resolution"],
            "removed_events": feature["properties"]["removed_events"],
            "polygon": feature["geometry"]["coordinates"][0],
        }
        for feature in features
    ]
    label_rows = [
        {
            "h3_cell": feature["properties"]["h3_cell"],
            "label": feature["properties"]["label"],
            "position": feature["centroid"],
            "removed_events": feature["properties"]["removed_events"],
        }
        for feature in features
    ]

    view_state = pdk.ViewState(latitude=49.295, longitude=-123.12, zoom=10.5, pitch=0, bearing=0)
    deck = pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=view_state,
        layers=[
            pdk.Layer(
                "PolygonLayer",
                polygon_rows,
                get_polygon="polygon",
                get_fill_color="[245, 85, 65, 90]",
                get_line_color="[210, 35, 20, 255]",
                line_width_min_pixels=2,
                pickable=True,
            ),
            pdk.Layer(
                "TextLayer",
                label_rows,
                get_position="position",
                get_text="label",
                get_color="[35, 35, 45, 255]",
                get_size=12,
                get_alignment_baseline="'center'",
                get_text_anchor="'middle'",
                size_units="pixels",
            ),
        ],
        tooltip={
            "html": "<b>{h3_cell}</b><br/>r{resolution}<br/>{removed_events} events",
        },
    )
    deck.to_html(html_path.as_posix(), open_browser=False)

    print(f"wrote {geojson_path}")
    print(f"wrote {html_path}")
    for cell in cells:
        print(f"{cell} r{h3.get_resolution(cell)} removed_events={counts[cell]:,}")


if __name__ == "__main__":
    main()
