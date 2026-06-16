from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class HomeAnchor:
    name: str
    lat: float
    lon: float
    weight: float
    radius_km: float


HOME_ANCHORS = [
    HomeAnchor("Downtown Vancouver", 49.2827, -123.1207, 0.08, 2.5),
    HomeAnchor("Kitsilano", 49.2684, -123.1683, 0.05, 2.0),
    HomeAnchor("Mount Pleasant", 49.2635, -123.0965, 0.06, 2.0),
    HomeAnchor("East Vancouver", 49.2524, -123.0450, 0.09, 3.0),
    HomeAnchor("South Vancouver", 49.2190, -123.1000, 0.07, 3.0),
    HomeAnchor("Burnaby Metrotown", 49.2276, -123.0076, 0.07, 3.0),
    HomeAnchor("Brentwood", 49.2664, -123.0010, 0.04, 2.5),
    HomeAnchor("Richmond", 49.1666, -123.1336, 0.09, 4.0),
    HomeAnchor("North Vancouver", 49.3200, -123.0730, 0.06, 3.5),
    HomeAnchor("New Westminster", 49.2057, -122.9110, 0.04, 2.5),
    HomeAnchor("Surrey Central", 49.1898, -122.8490, 0.12, 5.0),
    HomeAnchor("Guildford", 49.1900, -122.8030, 0.05, 3.5),
    HomeAnchor("Coquitlam", 49.2838, -122.7932, 0.07, 4.0),
    HomeAnchor("Port Moody", 49.2820, -122.8290, 0.03, 2.5),
    HomeAnchor("Delta", 49.0847, -123.0587, 0.04, 4.0),
    HomeAnchor("West Vancouver", 49.3286, -123.1602, 0.04, 3.0),
]


def sample_near_anchor(rng: np.random.Generator, anchor: HomeAnchor) -> tuple[float, float]:
    radius = anchor.radius_km * math.sqrt(float(rng.random()))
    theta = float(rng.uniform(0.0, 2.0 * math.pi))
    dlat = (radius * math.cos(theta)) / 111.0
    dlon = (radius * math.sin(theta)) / (111.0 * math.cos(math.radians(anchor.lat)))
    return anchor.lat + dlat, anchor.lon + dlon


def choose_home_anchors(rng: np.random.Generator, count: int) -> list[HomeAnchor]:
    weights = np.array([anchor.weight for anchor in HOME_ANCHORS], dtype=float)
    weights = weights / weights.sum()
    indexes = rng.choice(len(HOME_ANCHORS), size=count, p=weights)
    return [HOME_ANCHORS[int(index)] for index in indexes]
