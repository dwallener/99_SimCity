#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import h3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simcity.config import DATA_DIR, DISPLAY_RESOLUTIONS
from simcity.water import WATER_R7_CELLS


def dominant_activity(values: pd.Series) -> str:
    if values.empty:
        return ""
    return str(values.value_counts().index[0])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", default=str(DATA_DIR / "simulated_events" / "events_25k_14d.parquet"))
    parser.add_argument("--output", default=str(DATA_DIR / "h3_aggregates" / "h3_hourly_25k_14d.parquet"))
    parser.add_argument(
        "--exclude-forbidden-r7",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Drop events whose r10 cell rolls up into the narrow forbidden r7 cell list.",
    )
    args = parser.parse_args()

    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    events = pd.read_parquet(args.events)
    if args.exclude_forbidden_r7:
        before = len(events)
        h3_r7 = events["h3_r10"].map(lambda cell: h3.cell_to_parent(str(cell), 7))
        events = events.loc[~h3_r7.isin(WATER_R7_CELLS)].copy()
        print(f"excluded forbidden r7 events: {before:,} -> {len(events):,}")
    events["hour"] = pd.to_datetime(events["timestamp"]).dt.floor("h")

    frames = []
    for resolution in DISPLAY_RESOLUTIONS:
        if resolution == 10:
            events["h3_cell"] = events["h3_r10"]
        else:
            events["h3_cell"] = events["h3_r10"].map(lambda cell: h3.cell_to_parent(cell, resolution))
        grouped = (
            events.groupby(["hour", "h3_cell"], observed=True)
            .agg(
                resident_count=("resident_id", "nunique"),
                ping_count=("resident_id", "size"),
                dwell_count=("activity_type", lambda s: int((s != "travel").sum())),
                dominant_activity_type=("activity_type", dominant_activity),
            )
            .reset_index()
        )
        grouped.insert(1, "h3_resolution", resolution)
        frames.append(grouped)
        print(f"r{resolution}: {len(grouped):,} aggregate rows")

    aggregate = pd.concat(frames, ignore_index=True)
    aggregate.to_parquet(output, index=False, compression="zstd")
    print(f"wrote {output}")
    print(f"rows: {len(aggregate):,}")


if __name__ == "__main__":
    main()
