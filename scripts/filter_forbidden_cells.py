#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import h3
import pandas as pd

from simcity.config import DATA_DIR
from simcity.water import WATER_R7_CELLS


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Drop simulated events whose r10 H3 cell falls inside the forbidden r7 cells."
    )
    parser.add_argument(
        "--input",
        default=str(DATA_DIR / "simulated_events" / "events_15k_clean_14d.parquet"),
    )
    parser.add_argument(
        "--output",
        default=str(DATA_DIR / "simulated_events" / "events_15k_clean_excluded_14d.parquet"),
    )
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    events = pd.read_parquet(input_path)
    before = len(events)

    h3_r7 = events["h3_r10"].map(lambda cell: h3.cell_to_parent(str(cell), 7))
    deny_mask = h3_r7.isin(WATER_R7_CELLS)

    if deny_mask.any():
        removed_by_cell = h3_r7[deny_mask].value_counts().sort_index()
        print("removed events by forbidden r7 cell:")
        for cell, count in removed_by_cell.items():
            print(f"  {cell}: {count:,}")
    else:
        print("removed events by forbidden r7 cell: none")

    filtered = events.loc[~deny_mask].copy()
    filtered.to_parquet(output_path, index=False, compression="zstd")

    print(f"input:  {input_path}")
    print(f"output: {output_path}")
    print(f"events: {before:,} -> {len(filtered):,} removed {int(deny_mask.sum()):,}")


if __name__ == "__main__":
    main()
