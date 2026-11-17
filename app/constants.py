"""
Transport Constants - CO2 Emission Factors & Comfort Scores

These constants are used to AUTO-CALCULATE co2_kg and comfort_score
on TransportSegment when the user does not supply them manually.

--- CO2 FORMULA ---
    co2_kg = CO2_PER_KM[transport_mode] * distance_km

--- SOURCES ---
    CO2 figures: IPCC AR6 (2022), EEA Report No 16/2023,
                 Our World in Data "Travel carbon footprint" (2023)
    Comfort scores: Rome2Rio tier model, adapted for Central Asia context

--- DESIGN DECISION ---
    Constants live in Python, NOT in the database.
    - Easy to update when IPCC revises emission factors
    - No DB migration needed
    - Calculated values ARE persisted per-segment, so historical
      data stays accurate even if constants change later.
"""

from app.enums import TransportMode, AccessType


# =============================================================================
# CO2 EMISSION FACTORS  (kg of CO2 per passenger per km)
# =============================================================================
# Why train < bus < car?
#   Trains carry 300-700 passengers and often run on electricity → tiny share
#   per person. Cars average ~1.5 occupants → almost all emissions per person.

CO2_PER_KM: dict[TransportMode, float] = {
    TransportMode.PLANE:       0.255,  # Short-haul economy: large fuel burn + altitude factor
    TransportMode.TAXI:        0.171,  # Private car, often driven empty between trips
    TransportMode.CAR:         0.120,  # Private car with average occupancy (~1.5 pax)
    TransportMode.MARSHRUTKA:  0.105,  # Older diesel minibus, lower occupancy than bus
    TransportMode.BUS:         0.089,  # Diesel coach, 50-60 seats, good occupancy
    TransportMode.TRAIN:       0.041,  # Electric/diesel, 300-700 seats, most efficient
    TransportMode.CABLE_CAR:   0.008,  # Electric motor, very high capacity/km, near-zero
}

# CO2 for last-mile access types (used in routing service _calculate_last_mile_score)
CO2_PER_KM_ACCESS: dict[AccessType, float] = {
    AccessType.CAR:     0.120,
    AccessType.TAXI:    0.171,
    AccessType.BUS:     0.089,
    AccessType.SHUTTLE: 0.075,  # Usually newer, optimised vehicles
    AccessType.WALK:    0.000,  # Zero emissions
}


# =============================================================================
# COMFORT SCORES  (1–10 scale, higher = more comfortable)
# =============================================================================
# Criteria: seat space, climate control, schedule flexibility,
#           boarding experience, onboard amenities

COMFORT_SCORE: dict[TransportMode, float] = {
    TransportMode.TAXI:        9.0,  # Door-to-door, fully private, on-demand
    TransportMode.CABLE_CAR:   7.0,  # Smooth, scenic, no traffic, modern cabins
    TransportMode.PLANE:       8.0,  # Fast journey, A/C, reclining seat, meals
    TransportMode.TRAIN:       7.0,  # Spacious, walk around, scenic, reliable
    TransportMode.CAR:         6.0,  # Private, but you must drive; no rest
    TransportMode.BUS:         5.5,  # Fixed schedule, less legroom, stops often
    TransportMode.MARSHRUTKA:  4.0,  # Cramped, waits to fill, no A/C in older fleet
}

# Comfort for last-mile access types
COMFORT_SCORE_ACCESS: dict[AccessType, float] = {
    AccessType.TAXI:    9.0,
    AccessType.CAR:     6.0,
    AccessType.SHUTTLE: 6.5,
    AccessType.BUS:     5.0,
    AccessType.WALK:    7.0,  # Pleasant when short, healthy, no waiting
}


# =============================================================================
# TARIFFS  (cost estimation in KZT)
# =============================================================================
# Formula:  cost = base_fare + per_km * distance_km   (rounded to 50 KZT)
#
#   base_fare → what you pay before moving a metre (ticket booking fee,
#               taxi pick-up charge, airport taxes)
#   per_km    → the marginal price of one more kilometre
#
# ⚠️  These are ESTIMATES, fitted to the hand-entered prices in
#     scripts/seed_data.py — they are not a live price feed. Treat the
#     output as a sensible default and a sanity check, and re-tune the
#     numbers here when real prices drift (fuel price, new fares).
#     Values are (base_fare, per_km).

TARIFF_KZT: dict[TransportMode, tuple[float, float]] = {
    TransportMode.PLANE:      (15000.0,   8.0),
    TransportMode.TRAIN:      (800.0,     5.0),
    TransportMode.BUS:        (500.0,     5.5),
    TransportMode.MARSHRUTKA: (300.0,     5.5),
    TransportMode.TAXI:       (1000.0,  125.0),
    TransportMode.CAR:        (0.0,      30.0),  # fuel + wear, no driver
    TransportMode.CABLE_CAR:  (2500.0,    0.0),  # flat ticket
}

TARIFF_KZT_ACCESS: dict[AccessType, tuple[float, float]] = {
    AccessType.WALK:    (0.0,      0.0),
    AccessType.TAXI:    (1000.0, 125.0),
    AccessType.CAR:     (0.0,     30.0),
    AccessType.BUS:     (120.0,    5.0),   # city / suburban bus
    AccessType.SHUTTLE: (500.0,   15.0),
}

# Estimated prices are rounded to this step so they look like real fares.
COST_ROUNDING_KZT = 50


# =============================================================================
# TRAVEL TIME ESTIMATION
# =============================================================================
# Road modes: when OSRM answers we take ITS driving duration and stretch it by
# ROAD_TIME_FACTOR (a bus stops and is slower than a private car).
# When OSRM is unavailable, or for non-road modes, we fall back to
#     time = overhead_minutes + distance_km / speed_kmh * 60
# Values are (speed_kmh, overhead_minutes).

SPEED_PROFILE: dict[TransportMode, tuple[float, float]] = {
    TransportMode.PLANE:      (650.0, 40.0),  # taxiing, climb, descent
    TransportMode.TRAIN:      (75.0,   0.0),
    TransportMode.BUS:        (55.0,   0.0),
    TransportMode.MARSHRUTKA: (60.0,   0.0),
    TransportMode.TAXI:       (70.0,   0.0),
    TransportMode.CAR:        (70.0,   0.0),
    TransportMode.CABLE_CAR:  (18.0,   5.0),
}

SPEED_PROFILE_ACCESS: dict[AccessType, tuple[float, float]] = {
    AccessType.WALK:    (5.0,  0.0),
    AccessType.TAXI:    (50.0, 0.0),
    AccessType.CAR:     (50.0, 0.0),
    AccessType.BUS:     (30.0, 5.0),
    AccessType.SHUTTLE: (40.0, 5.0),
}

ROAD_TIME_FACTOR: dict[TransportMode, float] = {
    TransportMode.TAXI:       1.00,
    TransportMode.CAR:        1.00,
    TransportMode.MARSHRUTKA: 1.15,
    TransportMode.BUS:        1.25,
}

ROAD_TIME_FACTOR_ACCESS: dict[AccessType, float] = {
    AccessType.TAXI:    1.00,
    AccessType.CAR:     1.00,
    AccessType.SHUTTLE: 1.15,
    AccessType.BUS:     1.30,
}
