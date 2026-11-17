"""
Pricing & Metrics Estimation Service

Turns "a mode + a distance" into the numbers a segment needs:

    cost          = base_fare + per_km × distance      (TARIFF_KZT)
    time_minutes  = OSRM driving time × mode factor     (road modes, OSRM ok)
                  = overhead + distance ÷ speed         (everything else)
    co2_kg        = CO2_PER_KM × distance
    comfort_score = COMFORT_SCORE[mode]

Everything here is a PURE function of its inputs — no database, no network.
That is deliberate: the tariff logic can be unit-tested in microseconds and
reused by create / estimate / price-check without duplicating formulas.

The tariff table is a model, not a price feed (see app/constants.py).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Union

from app.constants import (
    CO2_PER_KM, CO2_PER_KM_ACCESS,
    COMFORT_SCORE, COMFORT_SCORE_ACCESS,
    TARIFF_KZT, TARIFF_KZT_ACCESS,
    SPEED_PROFILE, SPEED_PROFILE_ACCESS,
    ROAD_TIME_FACTOR, ROAD_TIME_FACTOR_ACCESS,
    COST_ROUNDING_KZT,
)
from app.enums import TransportMode, AccessType
from app.services.distance import TravelEstimate

Mode = Union[TransportMode, AccessType]


@dataclass(frozen=True)
class EstimatedMetrics:
    distance_km: float
    time_minutes: int
    cost: Decimal
    co2_kg: float
    comfort_score: float
    distance_strategy: str
    time_strategy: str  # "osrm_duration" | "speed_model"


def _tables(mode: Mode):
    """Pick the constant tables matching the enum type of `mode`."""
    if isinstance(mode, AccessType):
        return (TARIFF_KZT_ACCESS, SPEED_PROFILE_ACCESS, ROAD_TIME_FACTOR_ACCESS,
                CO2_PER_KM_ACCESS, COMFORT_SCORE_ACCESS)
    return TARIFF_KZT, SPEED_PROFILE, ROAD_TIME_FACTOR, CO2_PER_KM, COMFORT_SCORE


def estimate_cost(mode: Mode, distance_km: float) -> Decimal:
    """Tariff-model price in KZT, rounded to COST_ROUNDING_KZT."""
    base, per_km = _tables(mode)[0][mode]
    raw = base + per_km * max(distance_km, 0.0)
    step = COST_ROUNDING_KZT
    return Decimal(int(round(raw / step)) * step)


def estimate_time_minutes(
    mode: Mode,
    distance_km: float,
    driving_minutes: Optional[float] = None,
) -> tuple[int, str]:
    """
    Travel time in whole minutes (never less than 1) and the strategy used.

    `driving_minutes` is OSRM's private-car duration; it is only meaningful
    for road modes, where it is stretched by the mode's ROAD_TIME_FACTOR.
    """
    _, speeds, road_factors, _, _ = _tables(mode)
    if driving_minutes is not None and mode in road_factors:
        return max(1, round(driving_minutes * road_factors[mode])), "osrm_duration"

    speed_kmh, overhead_min = speeds[mode]
    minutes = overhead_min + (distance_km / speed_kmh) * 60
    return max(1, round(minutes)), "speed_model"


def estimate_co2(mode: Mode, distance_km: float) -> float:
    return round(_tables(mode)[3][mode] * distance_km, 3)


def default_comfort(mode: Mode) -> float:
    return _tables(mode)[4][mode]


def estimate_metrics(mode: Mode, travel: TravelEstimate) -> EstimatedMetrics:
    """All auto-calculable fields for one edge, from a distance lookup."""
    minutes, time_strategy = estimate_time_minutes(mode, travel.distance_km, travel.driving_minutes)
    return EstimatedMetrics(
        distance_km=travel.distance_km,
        time_minutes=minutes,
        cost=estimate_cost(mode, travel.distance_km),
        co2_kg=estimate_co2(mode, travel.distance_km),
        comfort_score=default_comfort(mode),
        distance_strategy=travel.strategy,
        time_strategy=time_strategy,
    )


def price_deviation_pct(stored: Decimal, estimated: Decimal) -> Optional[float]:
    """
    How far the stored price is from the tariff model, in percent.
    +50 → stored is 50% ABOVE the model, -30 → 30% below.
    None when the model price is 0 (walking), where a percentage is undefined.
    """
    if estimated == 0:
        return None
    return round(float((Decimal(stored) - estimated) / estimated * 100), 1)
