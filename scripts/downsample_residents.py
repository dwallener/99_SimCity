#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from simcity.config import DATA_DIR
from simcity.water import is_probably_water


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DATA_DIR / "residents" / "residents_25k.parquet"))
    parser.add_argument("--output", default=str(DATA_DIR / "residents" / "residents_15k.parquet"))
    parser.add_argument("--count", type=int, default=15_000)
    parser.add_argument("--seed", type=int, default=20250618)
    parser.add_argument("--allow-water-homes", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    residents = pd.read_parquet(input_path)
    if not args.allow_water_homes:
        before = len(residents)
        residents = residents[
            [
                not is_probably_water(float(lat), float(lon))
                for lat, lon in zip(residents["home_lat"], residents["home_lon"])
            ]
        ].copy()
        print(f"water-filtered residents: {before:,} -> {len(residents):,}")
    if args.count > len(residents):
        raise SystemExit(f"--count {args.count} exceeds input rows {len(residents)}")
    sampled = (
        residents.sample(n=args.count, random_state=args.seed)
        .sort_values("resident_id")
        .reset_index(drop=True)
    )
    sampled.to_parquet(output_path, index=False, compression="zstd")
    print(f"wrote {output_path}")
    print(f"rows: {len(sampled):,}")
    print(sampled["schedule_profile"].value_counts().to_string())


if __name__ == "__main__":
    main()
