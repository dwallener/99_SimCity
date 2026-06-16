from __future__ import annotations


PROFILE_WEIGHTS = {
    "standard_weekday": 0.35,
    "early_shift": 0.08,
    "late_shift": 0.08,
    "night_shift": 0.04,
    "part_time": 0.10,
    "hybrid_worker": 0.10,
    "remote_worker": 0.08,
    "student": 0.07,
    "retiree_local": 0.06,
    "tourist": 0.04,
}


PROFILE_MODES = {
    "standard_weekday": "transit",
    "early_shift": "car",
    "late_shift": "car",
    "night_shift": "car",
    "part_time": "transit",
    "hybrid_worker": "transit",
    "remote_worker": "walk",
    "student": "transit",
    "retiree_local": "walk",
    "tourist": "walk",
}


def is_primary_active(profile: str, weekday: int, day_index: int) -> bool:
    is_weekend = weekday >= 5
    if profile == "standard_weekday":
        return not is_weekend
    if profile in {"early_shift", "late_shift", "night_shift"}:
        return day_index % 7 not in {2, 5}
    if profile == "part_time":
        return day_index % 2 == 0 or weekday in {4, 5}
    if profile == "hybrid_worker":
        return weekday in {0, 2, 3}
    if profile == "remote_worker":
        return False
    if profile == "student":
        return not is_weekend and weekday != 4
    if profile == "retiree_local":
        return False
    if profile == "tourist":
        return True
    return not is_weekend


def primary_window(profile: str) -> tuple[float, float]:
    if profile == "early_shift":
        return 6.0, 14.0
    if profile == "late_shift":
        return 14.0, 22.0
    if profile == "night_shift":
        return 21.0, 29.0
    if profile == "part_time":
        return 10.0, 15.0
    if profile == "student":
        return 9.0, 16.0
    if profile == "tourist":
        return 10.0, 20.0
    return 9.0, 17.0
