#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import h3
import pandas as pd

from simcity.config import DATA_DIR, GREATER_VANCOUVER_LOCALITIES, POI_SOURCE_DIR, VANCOUVER_BOUNDS
from simcity.poi import attraction_weight, classify_category, destination_weight
from simcity.water import is_probably_water


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default=str(POI_SOURCE_DIR))
    parser.add_argument("--output", default=str(DATA_DIR / "processed_poi" / "poi_vancouver.parquet"))
    parser.add_argument(
        "--filter-water-poi",
        action="store_true",
        help="Drop POI whose centroid falls in the rough water mask. Off by default.",
    )
    args = parser.parse_args()

    source = Path(args.source_dir).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    entities = source / "poi_entities.parquet"
    geometries = source / "poi_geometries.parquet"
    if not entities.exists() or not geometries.exists():
        raise SystemExit(f"Missing POI entities/geometries under {source}")

    localities = ", ".join("'" + value.lower().replace("'", "''") + "'" for value in GREATER_VANCOUVER_LOCALITIES)
    bounds = VANCOUVER_BOUNDS
    sql = f"""
      SELECT
        e.entity_id AS poi_id,
        e.name,
        e.brand,
        e.category_primary,
        e.locality,
        e.region,
        e.operating_status,
        e.confidence,
        e.geometry_grade,
        e.geometry_source,
        (g.bbox.xmin + g.bbox.xmax) / 2.0 AS lon,
        (g.bbox.ymin + g.bbox.ymax) / 2.0 AS lat
      FROM read_parquet('{entities.as_posix()}') e
      JOIN read_parquet('{geometries.as_posix()}') g USING (entity_id)
      WHERE lower(e.locality) IN ({localities})
        AND (g.bbox.xmin + g.bbox.xmax) / 2.0 BETWEEN {bounds["lon_min"]} AND {bounds["lon_max"]}
        AND (g.bbox.ymin + g.bbox.ymax) / 2.0 BETWEEN {bounds["lat_min"]} AND {bounds["lat_max"]}
        AND (e.operating_status IS NULL OR lower(e.operating_status) NOT IN ('closed', 'inactive'))
        AND e.name IS NOT NULL
    """
    df = duckdb.connect().execute(sql).fetchdf()
    if df.empty:
        raise SystemExit("No Vancouver-area POI rows matched the source layer")

    if args.filter_water_poi:
        before_water_filter = len(df)
        df = df[
            [
                not is_probably_water(float(lat), float(lon))
                for lat, lon in zip(df["lat"], df["lon"])
            ]
        ].copy()
        print(f"water-filtered POI rows: {before_water_filter:,} -> {len(df):,}")

    df["category_class"] = df["category_primary"].map(classify_category)
    df["destination_weight"] = df["category_class"].map(destination_weight)
    df["attraction_weight"] = [
        attraction_weight(name, brand, category, category_class)
        for name, brand, category, category_class in zip(
            df["name"],
            df["brand"],
            df["category_primary"],
            df["category_class"],
        )
    ]
    df["h3_r10"] = [h3.latlng_to_cell(lat, lon, 10) for lat, lon in zip(df["lat"], df["lon"])]
    df = df.sort_values(["locality", "category_class", "name"], na_position="last")
    df.to_parquet(output, index=False, compression="zstd")

    print(f"wrote {output}")
    print(f"rows: {len(df):,}")
    print(df["category_class"].value_counts().to_string())


if __name__ == "__main__":
    main()
