#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import h3
import numpy as np
import pandas as pd

from simcity.config import DATA_DIR, DEFAULT_DAYS, DEFAULT_START
from simcity.schedules import is_primary_active, primary_window
from simcity.water import snap_travel_point_to_land


ERRAND_CLASSES = {"food_drink", "retail", "recreation", "health", "civic", "transport"}
OUTPUT_COLUMNS = [
    "resident_id",
    "timestamp",
    "lat",
    "lon",
    "h3_r10",
    "activity_type",
    "destination_type",
    "poi_id",
]


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


class PoiSampler:
    def __init__(self, poi: pd.DataFrame) -> None:
        self.poi = poi
        self.pools: dict[frozenset[str], tuple[np.ndarray, np.ndarray]] = {}

    def pool(self, classes: set[str]) -> tuple[np.ndarray, np.ndarray]:
        key = frozenset(classes)
        if key in self.pools:
            return self.pools[key]
        subset = self.poi[self.poi["category_class"].isin(classes)]
        if subset.empty:
            subset = self.poi
        indexes = subset.index.to_numpy()
        weight_col = "attraction_weight" if "attraction_weight" in subset.columns else "destination_weight"
        weights = subset[weight_col].to_numpy(dtype=float)
        weights = weights / weights.sum()
        self.pools[key] = (indexes, weights)
        return indexes, weights

    def choose(self, rng: np.random.Generator, classes: set[str]) -> pd.Series:
        indexes, weights = self.pool(classes)
        index = rng.choice(indexes, p=weights)
        return self.poi.loc[index]


def sql_path(path: Path) -> str:
    return path.as_posix().replace("'", "''")


def position_for_hour(
    hour_float: float,
    home_lat: float,
    home_lon: float,
    dest_lat: float,
    dest_lon: float,
    depart: float,
    arrive: float,
    leave: float,
    return_home: float,
) -> tuple[float, float, str]:
    if hour_float < depart:
        return home_lat, home_lon, "home"
    if depart <= hour_float < arrive:
        t = (hour_float - depart) / max(arrive - depart, 0.01)
        lat = lerp(home_lat, dest_lat, t)
        lon = lerp(home_lon, dest_lon, t)
        lat, lon = snap_travel_point_to_land(lat, lon, home_lat, home_lon, dest_lat, dest_lon)
        return lat, lon, "travel"
    if arrive <= hour_float < leave:
        return dest_lat, dest_lon, "primary"
    if leave <= hour_float < return_home:
        t = (hour_float - leave) / max(return_home - leave, 0.01)
        lat = lerp(dest_lat, home_lat, t)
        lon = lerp(dest_lon, home_lon, t)
        lat, lon = snap_travel_point_to_land(lat, lon, home_lat, home_lon, dest_lat, dest_lon)
        return lat, lon, "travel"
    return home_lat, home_lon, "home"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--residents", default=str(DATA_DIR / "residents" / "residents_25k.parquet"))
    parser.add_argument("--poi", default=str(DATA_DIR / "processed_poi" / "poi_vancouver.parquet"))
    parser.add_argument("--output", default=str(DATA_DIR / "simulated_events" / "events_25k_14d.parquet"))
    parser.add_argument("--partial-dir", default=None)
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--event-step-minutes", type=int, default=60)
    parser.add_argument("--seed", type=int, default=20250617)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    residents = pd.read_parquet(args.residents)
    poi = pd.read_parquet(args.poi).set_index("poi_id", drop=False)
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    partial_dir = (
        Path(args.partial_dir).expanduser().resolve()
        if args.partial_dir
        else output.parent / f"{output.stem}_parts"
    )
    partial_dir.mkdir(parents=True, exist_ok=True)
    sampler = PoiSampler(poi)

    start = pd.Timestamp(args.start)
    timestamps = pd.date_range(
        start,
        periods=int(args.days * 24 * 60 / args.event_step_minutes),
        freq=f"{args.event_step_minutes}min",
    )

    for day_index in range(args.days):
        day_part = partial_dir / f"day_{day_index + 1:02d}.parquet"
        if day_part.exists() and not args.overwrite:
            print(f"[day {day_index + 1:02d}/{args.days:02d}] skip existing {day_part.name}", flush=True)
            continue

        day_start = start + pd.Timedelta(days=day_index)
        weekday = int(day_start.weekday())
        day_times = [ts for ts in timestamps if ts.date() == day_start.date()]
        records = []
        print(f"[day {day_index + 1:02d}/{args.days:02d}] simulate {len(residents):,} residents", flush=True)

        for resident in residents.itertuples(index=False):
            profile = resident.schedule_profile
            home_lat = float(resident.home_lat)
            home_lon = float(resident.home_lon)
            primary_poi_id = getattr(resident, "primary_poi_id")
            active = is_primary_active(profile, weekday, day_index)
            if active and pd.notna(primary_poi_id) and primary_poi_id in poi.index:
                dest = poi.loc[primary_poi_id]
            else:
                dest = sampler.choose(rng, ERRAND_CLASSES)

            dest_lat = float(dest["lat"])
            dest_lon = float(dest["lon"])
            base_start, base_end = primary_window(profile)
            jitter = float(rng.normal(0.0, 0.45))
            dwell_adjust = float(rng.normal(0.0, 0.5))
            depart = max(0.0, base_start - 0.7 + jitter)
            arrive = depart + float(rng.uniform(0.3, 1.1))
            leave = max(arrive + 0.5, base_end + dwell_adjust)
            return_home = leave + float(rng.uniform(0.3, 1.2))

            if not active:
                if rng.random() < 0.45:
                    depart = float(rng.uniform(10.0, 18.0))
                    arrive = depart + float(rng.uniform(0.15, 0.5))
                    leave = arrive + float(rng.uniform(0.5, 2.5))
                    return_home = leave + float(rng.uniform(0.15, 0.5))
                else:
                    depart = arrive = leave = return_home = 99.0

            for ts in day_times:
                hour_float = ts.hour + ts.minute / 60.0
                lat, lon, activity = position_for_hour(
                    hour_float,
                    home_lat,
                    home_lon,
                    dest_lat,
                    dest_lon,
                    depart,
                    arrive,
                    leave,
                    return_home,
                )
                if activity == "home":
                    poi_id = None
                    destination_type = "home"
                elif activity == "travel":
                    poi_id = None
                    destination_type = "travel"
                else:
                    poi_id = str(dest["poi_id"])
                    destination_type = str(dest["category_class"])

                records.append(
                    (
                        resident.resident_id,
                        ts,
                        lat,
                        lon,
                        h3.latlng_to_cell(lat, lon, 10),
                        activity,
                        destination_type,
                        poi_id,
                    )
                )

        events = pd.DataFrame.from_records(records, columns=OUTPUT_COLUMNS)
        tmp_part = day_part.with_suffix(day_part.suffix + ".partial")
        events.to_parquet(tmp_part, index=False, compression="zstd")
        tmp_part.replace(day_part)
        print(f"[day {day_index + 1:02d}/{args.days:02d}] wrote {day_part} ({len(events):,} rows)", flush=True)

    part_glob = partial_dir / "day_*.parquet"
    tmp_output = output.with_suffix(output.suffix + ".partial")
    if tmp_output.exists():
        tmp_output.unlink()
    duckdb.connect().execute(
        f"""
        COPY (
          SELECT *
          FROM read_parquet('{sql_path(part_glob)}')
          ORDER BY timestamp, resident_id
        ) TO '{sql_path(tmp_output)}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """
    )
    tmp_output.replace(output)
    row_count = duckdb.connect().execute(
        f"SELECT COUNT(*) FROM read_parquet('{sql_path(output)}')"
    ).fetchone()[0]
    print(f"wrote {output}")
    print(f"rows: {row_count:,}")


if __name__ == "__main__":
    main()
