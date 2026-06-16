from __future__ import annotations

import h3


def latlon_to_h3(lat: float, lon: float, resolution: int) -> str:
    return h3.latlng_to_cell(float(lat), float(lon), int(resolution))


def h3_parent(cell: str, resolution: int) -> str:
    return h3.cell_to_parent(str(cell), int(resolution))


def h3_latlon(cell: str) -> tuple[float, float]:
    lat, lon = h3.cell_to_latlng(str(cell))
    return float(lat), float(lon)
