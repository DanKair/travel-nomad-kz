"""Pure-function tests: no database, no HTTP."""
from decimal import Decimal

from app.enums import TransportMode, AccessType
from app.services.distance import TravelEstimate, haversine_km
from app.services.pricing import (
    estimate_cost, estimate_time_minutes, estimate_metrics, price_deviation_pct,
)


def test_haversine_almaty_shymkent_is_about_600km():
    assert 580 < haversine_km(43.2335, 76.9218, 42.3417, 69.5901) < 620


def test_cost_is_base_plus_per_km_rounded_to_50():
    # bus: 500 + 5.5 * 180 = 1490 → 1500
    assert estimate_cost(TransportMode.BUS, 180) == Decimal(1500)
    # taxi: 1000 + 125 * 15 = 2875 → 2900
    assert estimate_cost(TransportMode.TAXI, 15) == Decimal(2900)


def test_walking_is_free_and_same_named_modes_use_their_own_table():
    assert estimate_cost(AccessType.WALK, 2) == Decimal(0)
    # "bus" exists in both enums but a city bus is priced differently from a coach
    assert estimate_cost(AccessType.BUS, 10) != estimate_cost(TransportMode.BUS, 10)


def test_road_time_uses_osrm_duration_stretched_by_mode():
    assert estimate_time_minutes(TransportMode.TAXI, 100, driving_minutes=80) == (80, "osrm_duration")
    assert estimate_time_minutes(TransportMode.BUS, 100, driving_minutes=80) == (100, "osrm_duration")


def test_time_falls_back_to_speed_model_without_osrm():
    assert estimate_time_minutes(TransportMode.TRAIN, 150) == (120, "speed_model")
    # A flight ignores a driving duration even if one is passed in
    minutes, strategy = estimate_time_minutes(TransportMode.PLANE, 650, driving_minutes=999)
    assert (minutes, strategy) == (100, "speed_model")


def test_time_is_never_zero():
    assert estimate_time_minutes(AccessType.WALK, 0.01)[0] == 1


def test_estimate_metrics_bundles_everything():
    m = estimate_metrics(TransportMode.BUS, TravelEstimate(180, "osrm", driving_minutes=120))
    assert (m.distance_km, m.time_minutes, m.cost) == (180, 150, Decimal(1500))
    assert m.co2_kg == round(0.089 * 180, 3)
    assert m.distance_strategy == "osrm" and m.time_strategy == "osrm_duration"


def test_price_deviation():
    assert price_deviation_pct(Decimal(1500), Decimal(1000)) == 50.0
    assert price_deviation_pct(Decimal(700), Decimal(1000)) == -30.0
    assert price_deviation_pct(Decimal(0), Decimal(0)) is None
