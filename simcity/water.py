from __future__ import annotations

import h3


# Deliberately narrow denylist. These are the r7 cells covering the obvious
# over-water blobs in English Bay / Burrard Inlet. This is not a general
# land/water classifier.
WATER_R7_CELLS = {
    "8728de160ffffff",
    "8728de161ffffff",
    "8728de164ffffff",
    "8728de165ffffff",
    "8728de166ffffff",
    "8728de8caffffff",
    "8728deb92ffffff",
    "8728deb96ffffff",
    "8728de8cbffffff",
    "8728de8daffffff",
    "8728de12dffffff",
}


def is_probably_water(lat: float, lon: float) -> bool:
    return h3.latlng_to_cell(float(lat), float(lon), 7) in WATER_R7_CELLS


def snap_travel_point_to_land(
    lat: float,
    lon: float,
    home_lat: float,
    home_lon: float,
    dest_lat: float,
    dest_lon: float,
) -> tuple[float, float]:
    if not is_probably_water(lat, lon):
        return lat, lon

    candidates = [
        (home_lat, home_lon),
        (dest_lat, dest_lon),
        ((lat + home_lat) / 2.0, (lon + home_lon) / 2.0),
        ((lat + dest_lat) / 2.0, (lon + dest_lon) / 2.0),
    ]
    land_candidates = [point for point in candidates if not is_probably_water(point[0], point[1])]
    if not land_candidates:
        return home_lat, home_lon

    return min(
        land_candidates,
        key=lambda point: (point[0] - lat) ** 2 + (point[1] - lon) ** 2,
    )
