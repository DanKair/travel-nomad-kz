"""
Domain Enumerations

IMPORTANT: These enums have strict separation by purpose:
- TransportMode: Used ONLY for TransportSegment (routing graph edges)
- AccessType: Used ONLY for PointNode (last-mile access)
- NodeType: Used ONLY for Node (routing graph vertices)

DO NOT mix these enums - they serve different domain purposes!
"""

from enum import Enum


class TransportMode(str, Enum):
    """
    Transportation modes for TransportSegment (graph edges).
    
    These are the modes used for traveling BETWEEN cities/nodes.
    Used exclusively in the routing algorithm.
    """
    PLANE = "plane"
    TRAIN = "train"
    BUS = "bus"
    TAXI = "taxi"
    MARSHRUTKA = "marshrutka"  # Shared minibus, common in Central Asia


class NodeType(str, Enum):
    """
    Types of transportation nodes (graph vertices).
    
    Nodes are physical locations where you can board/exit transportation.
    """
    CITY = "city"              # General city/town
    AIRPORT = "airport"        # Airport (for plane transport)
    STATION = "station"        # Railway station (for train transport)
    BUS_STOP = "bus_stop"      # Bus terminal/stop


class AccessType(str, Enum):
    """
    Last-mile access types for PointNode ONLY.
    
    These describe how to reach a TouristPoint from a nearby Node
    AFTER the main route has been calculated.
    
    NOTE: This is separate from TransportMode! AccessType is NOT part
    of the routing graph - it's applied after routing is complete.
    """
    WALK = "walk"              # Walking distance
    TAXI = "taxi"              # Taxi from node to tourist point
    BUS = "bus"                # Local bus
    SHUTTLE = "shuttle"        # Tourist shuttle service
    CAR = "car"                # Private car/rental
