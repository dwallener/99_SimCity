#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from simcity.config import DATA_DIR, DEFAULT_RESIDENT_COUNT
from simcity.geography import choose_home_anchors, sample_near_anchor
from simcity.h3util import latlon_to_h3
from simcity.schedules import PROFILE_MODES, PROFILE_WEIGHTS
from simcity.water import is_probably_water


def weighted_choice(rng: np.random.Generator, values: list[str], weights: list[float], count: int) -> np.ndarray:
    probs = np.array(weights, dtype=float)
    probs = probs / probs.sum()
    return rng.choice(values, size=count, p=probs)


def sample_poi_ids(
    rng: np.random.Generator,
    poi: pd.DataFrame,
    classes: set[str],
    count: int,
) -> np.ndarray:
    subset = poi[poi["category_class"].isin(classes)].copy()
    if subset.empty:
        subset = poi.copy()
    weight_col = "attraction_weight" if "attraction_weight" in subset.columns else "destination_weight"
    weights = subset[weight_col].to_numpy(dtype=float)
    weights = weights / weights.sum()
    indexes = rng.choice(subset.index.to_numpy(), size=count, replace=True, p=weights)
    return subset.loc[indexes, "poi_id"].to_numpy()


def sample_land_home(rng: np.random.Generator, anchor) -> tuple[float, float]:
    for _ in range(80):
        lat, lon = sample_near_anchor(rng, anchor)
        if not is_probably_water(lat, lon):
            return lat, lon
    return anchor.lat, anchor.lon


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--poi", default=str(DATA_DIR / "processed_poi" / "poi_vancouver.parquet"))
    parser.add_argument("--output", default=str(DATA_DIR / "residents" / "residents_25k.parquet"))
    parser.add_argument("--count", type=int, default=DEFAULT_RESIDENT_COUNT)
    parser.add_argument("--seed", type=int, default=20250616)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    poi_path = Path(args.poi).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    poi = pd.read_parquet(poi_path)
    profiles = list(PROFILE_WEIGHTS)
    profile_values = weighted_choice(rng, profiles, [PROFILE_WEIGHTS[p] for p in profiles], args.count)
    anchors = choose_home_anchors(rng, args.count)

    rows = []
    work_ids = sample_poi_ids(rng, poi, {"work_service", "retail", "health", "transport", "civic"}, args.count)
    study_ids = sample_poi_ids(rng, poi, {"education"}, args.count)
    hotel_ids = sample_poi_ids(rng, poi, {"hotel"}, args.count)
    for index, (profile, anchor) in enumerate(zip(profile_values, anchors), start=1):
        home_lat, home_lon = sample_land_home(rng, anchor)
        if profile == "student":
            primary_poi = study_ids[index - 1]
        elif profile == "tourist":
            primary_poi = hotel_ids[index - 1]
        elif profile in {"remote_worker", "retiree_local"}:
            primary_poi = None
        else:
            primary_poi = work_ids[index - 1]

        rows.append(
            {
                "resident_id": f"resident_{index:06d}",
                "home_anchor": anchor.name,
                "home_lat": home_lat,
                "home_lon": home_lon,
                "home_h3_r10": latlon_to_h3(home_lat, home_lon, 10),
                "schedule_profile": profile,
                "mobility_mode": PROFILE_MODES.get(profile, "transit"),
                "primary_poi_id": primary_poi,
            }
        )

    residents = pd.DataFrame(rows)
    residents.to_parquet(output, index=False, compression="zstd")
    print(f"wrote {output}")
    print(f"rows: {len(residents):,}")
    print(residents["schedule_profile"].value_counts().to_string())


if __name__ == "__main__":
    main()
