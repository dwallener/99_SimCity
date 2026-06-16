#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import h3
import pandas as pd

from simcity.config import DATA_DIR, DISPLAY_RESOLUTIONS


def dominant_activity(values: pd.Series) -> str:
    if values.empty:
        return ""
    return str(values.value_counts().index[0])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", default=str(DATA_DIR / "simulated_events" / "events_25k_14d.parquet"))
    parser.add_argument("--output", default=str(DATA_DIR / "h3_aggregates" / "h3_hourly_25k_14d.parquet"))
    args = parser.parse_args()

    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    events = pd.read_parquet(args.events)
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
