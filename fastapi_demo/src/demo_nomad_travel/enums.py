# 1. ENUMS (The Fixed Choices)
from enum import Enum


class TransportMode(str, Enum):
    PLANE = "plane"
    TRAIN = "train"
    BUS = "bus"
    TAXI = "taxi"
    MARSHRUTKA = "marshrutka"

class NodeType(str, Enum):
    HUB = "hub"  # Airport, Station
    TOURIST_POINT = "tourist_point"