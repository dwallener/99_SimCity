from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

POI_SOURCE_DIR = (
    PROJECT_ROOT.parents[0]
    / "Q1_poi"
    / "ca_everything_clean"
    / "geometry_upgrade_v1"
    / "region_BC_site_policy_v1"
)

GREATER_VANCOUVER_LOCALITIES = [
    "Vancouver",
    "Burnaby",
    "Richmond",
    "North Vancouver",
    "North Vancouver District",
    "New Westminster",
    "Surrey",
    "Coquitlam",
    "Port Coquitlam",
    "Port Moody",
    "West Vancouver",
    "Delta",
]

VANCOUVER_BOUNDS = {
    "lon_min": -123.35,
    "lon_max": -122.55,
    "lat_min": 49.00,
    "lat_max": 49.40,
}

DISPLAY_RESOLUTIONS = [6, 7, 8, 9, 10]
DEFAULT_START = "2026-06-01T00:00:00"
DEFAULT_DAYS = 14
DEFAULT_RESIDENT_COUNT = 25_000
