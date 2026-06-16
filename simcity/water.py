from __future__ import annotations


Point = tuple[float, float]  # lat, lon


WATER_POLYGONS: list[list[Point]] = [
    # English Bay and Burrard Inlet, broad enough to catch the visible over-water blobs.
    [
        (49.335, -123.300),
        (49.325, -123.205),
        (49.305, -123.085),
        (49.300, -122.920),
        (49.315, -122.855),
        (49.285, -122.830),
        (49.270, -122.965),
        (49.260, -123.110),
        (49.255, -123.235),
        (49.275, -123.310),
    ],
    # False Creek.
    [
        (49.276, -123.150),
        (49.273, -123.118),
        (49.269, -123.096),
        (49.263, -123.095),
        (49.264, -123.130),
        (49.268, -123.155),
    ],
    # Fraser River north arm / Richmond north edge.
    [
        (49.225, -123.220),
        (49.220, -123.055),
        (49.210, -122.940),
        (49.198, -122.885),
        (49.188, -122.900),
        (49.196, -123.010),
        (49.203, -123.160),
        (49.208, -123.235),
    ],
    # Fraser main channel along south Richmond / Delta / Surrey.
    [
        (49.150, -123.220),
        (49.142, -123.080),
        (49.125, -122.940),
        (49.105, -122.820),
        (49.090, -122.720),
        (49.070, -122.710),
        (49.085, -122.850),
        (49.105, -123.020),
        (49.115, -123.230),
    ],
]


def _point_in_polygon(lat: float, lon: float, polygon: list[Point]) -> bool:
    inside = False
    j = len(polygon) - 1
    for i, (lat_i, lon_i) in enumerate(polygon):
        lat_j, lon_j = polygon[j]
        intersects = (lon_i > lon) != (lon_j > lon)
        if intersects:
            lat_at_lon = (lat_j - lat_i) * (lon - lon_i) / ((lon_j - lon_i) or 1e-12) + lat_i
            if lat < lat_at_lon:
                inside = not inside
        j = i
    return inside


def is_probably_water(lat: float, lon: float) -> bool:
    return any(_point_in_polygon(lat, lon, polygon) for polygon in WATER_POLYGONS)


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
