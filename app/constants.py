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
