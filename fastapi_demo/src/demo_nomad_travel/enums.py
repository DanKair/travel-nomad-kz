# 1. ENUMS (The Fixed Choices)
from enum import Enum


class TransportMode(str, Enum):
    PLANE = "plane"
    TRAIN = "train"
    BUS = "bus"
    TAXI = "taxi"
    MARSHRUTKA = "marshrutka"

class NodeType(str, Enum):
    CITY = "city"
    # TransportHubs (airports, train stations, bus stops)
    AIRPORT = "airport"
    STATION = "station"
    BUS_STOP = "bus_stop"