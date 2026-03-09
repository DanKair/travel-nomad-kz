from sqladmin import ModelView
from app.models import (
    Region, 
    TouristPointCategory, 
    Node, 
    TransportSegment, 
    TouristPoint, 
    PointNode
)

class RegionAdmin(ModelView, model=Region):
    name = "Region"
    name_plural = "Regions"
    column_list = ["id", "name"]
    column_searchable_list = ["name"]
    icon = "fa-solid fa-map"

class CategoryAdmin(ModelView, model=TouristPointCategory):
    name = "Category"
    name_plural = "Categories"
    column_list = ["id", "name", "parent_id"]
    column_searchable_list = ["name"]
    icon = "fa-solid fa-layer-group"

class NodeAdmin(ModelView, model=Node):
    name = "Node"
    name_plural = "Nodes"
    column_list = ["id", "name", "node_type", "latitude", "longitude"]
    column_searchable_list = ["name", "slug"]
    icon = "fa-solid fa-location-dot"

class TransportSegmentAdmin(ModelView, model=TransportSegment):
    name = "Transport Segment"
    name_plural = "Transport Segments"
    column_list = [
        "id", 
        "from_node", 
        "to_node", 
        "transport_mode",
        "cost",
        "time_minutes"
    ]
    column_select_related_list = ["from_node", "to_node"]
    icon = "fa-solid fa-bus"

class TouristPointAdmin(ModelView, model=TouristPoint):
    name = "Tourist Point"
    name_plural = "Tourist Points"
    column_list = ["id", "name", "region", "category"]
    column_select_related_list = ["region", "category"]
    column_searchable_list = ["name", "slug"]
    icon = "fa-solid fa-camera"

class PointNodeAdmin(ModelView, model=PointNode):
    name = "Point Node"
    name_plural = "Point Nodes"
    column_list = ["id", "tourist_point", "node", "access_type"]
    column_select_related_list = ["tourist_point", "node"]
    icon = "fa-solid fa-person-walking"

# List of all admin views to be registered
admin_views = [
    RegionAdmin,
    CategoryAdmin,
    NodeAdmin,
    TransportSegmentAdmin,
    TouristPointAdmin,
    PointNodeAdmin
]
