"""
Routing Service - Multi-Criteria Dijkstra Algorithm with Pareto Weights

ALGORITHM EXPLANATION (for Junior Developers):

1. WHAT IS DIJKSTRA'S ALGORITHM?
   Dijkstra's algorithm finds the shortest path in a graph. Think of it like 
   finding the best route on a map - but instead of just distance, we can 
   consider multiple factors.

2. WHAT IS MULTI-CRITERIA OPTIMIZATION?
   Instead of minimizing just ONE thing (like time), we balance MULTIPLE criteria:
   - Time: How long does it take?
   - Cost: How much does it cost?
   - Comfort: How comfortable is the journey?
   - CO2: What's the environmental impact?

3. WHAT ARE PARETO WEIGHTS?
   Pareto weights are percentages that determine how important each criterion is.
   Example: time_weight=0.4 means "time is 40% of the total score"
   All weights must add up to 1.0 (100%)

4. HOW THE ALGORITHM WORKS:
   a. Build a graph from TransportSegments (Node A → Node B connections)
   b. Start from the origin node
   c. Explore all neighbors, calculating a "cost" for each criterion
   d. Combine costs using Pareto weights into a single score
   e. Always pick the lowest-score path to explore next
   f. Continue until we reach the destination
   g. Reconstruct the path by backtracking

5. NORMALIZATION:
   Since criteria have different units (minutes, KZT, kg), we "normalize" them
   to a 0-1 scale so they can be fairly combined. This prevents one criterion
   from dominating just because its numbers are bigger.

ARCHITECTURE NOTES:
- This service operates ONLY on Node + TransportSegment
- TouristPoint is NOT part of the graph
- PointNode (last-mile) is added AFTER routing
"""

from typing import Dict, List, Tuple, Optional
import heapq
import logging
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Node, TransportSegment, TouristPoint, PointNode
from app.schemas import (
    RouteResponse,
    RouteSegmentStep,
    LastMileAccess,
    RouteAlternative,
    RouteAlternativesResponse,
)
from app.core.config import settings
from app.constants import CO2_PER_KM_ACCESS, COMFORT_SCORE_ACCESS

logger = logging.getLogger(__name__)

Graph = Dict[int, List[Tuple[int, TransportSegment]]]


class RouteNotFoundError(ValueError):
    """A node / tourist point does not exist, or no path connects them (HTTP 404)."""



class RoutingService:
    """
    Service for calculating optimal routes using multi-criteria Dijkstra.
    """

    # -------------------------------------------------------------------------
    # ROUTE PROFILES
    # Each profile is a set of Pareto weights that biases the Dijkstra search
    # toward a specific optimization goal. All weights must sum to 1.0.
    # -------------------------------------------------------------------------
    PROFILES: Dict[str, Dict[str, float]] = {
        "fastest":  {"time": 0.85, "cost": 0.05, "comfort": 0.05, "co2": 0.05},
        "cheapest": {"time": 0.05, "cost": 0.85, "comfort": 0.05, "co2": 0.05},
        "comfort":  {"time": 0.05, "cost": 0.10, "comfort": 0.80, "co2": 0.05},
        "eco":      {"time": 0.05, "cost": 0.10, "comfort": 0.05, "co2": 0.80},
        "optimal":  {"time": 0.45, "cost": 0.35, "comfort": 0.10, "co2": 0.10},
    }

    PROFILE_LABELS: Dict[str, str] = {
        "fastest":  "Fastest",
        "cheapest": "Cheapest",
        "comfort":  "Comfort",
        "eco":      "Eco",
        "optimal":  "Optimal",
    }

    # Display order for the alternatives list (Optimal card shown first)
    PROFILE_ORDER = ["optimal", "fastest", "cheapest", "comfort", "eco"]

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _resolve(self, from_node_slug: str, to_tourist_point_slug: str):
        """Load the start node and the destination's access options (PointNodes)."""
        result = await self.db.execute(select(Node).filter(Node.slug == from_node_slug))
        start_node = result.scalars().first()
        if not start_node:
            raise RouteNotFoundError(f"Starting node '{from_node_slug}' not found")

        result = await self.db.execute(
            select(TouristPoint).filter(TouristPoint.slug == to_tourist_point_slug)
        )
        tourist_point = result.scalars().first()
        if not tourist_point:
            raise RouteNotFoundError(f"Tourist point '{to_tourist_point_slug}' not found")

        result = await self.db.execute(
            select(PointNode)
            .options(joinedload(PointNode.node), joinedload(PointNode.tourist_point))
            .filter(PointNode.tourist_point_id == tourist_point.id)
        )
        point_nodes = result.scalars().all()
        if not point_nodes:
            raise RouteNotFoundError(
                f"No access points configured for tourist point '{to_tourist_point_slug}'"
            )
        return start_node, point_nodes

    def _best_route(
        self,
        start_node_id: int,
        point_nodes: List[PointNode],
        weights: Dict[str, float],
        graph: Graph,
    ) -> Optional[Tuple[Dict, PointNode, float]]:
        """
        Best (route, access option, total score) for one set of weights.

        Dijkstra already computes the cheapest way to reach EVERY node from the
        start, so we run it ONCE and then just read off the answer for each
        access node — instead of re-running the whole search per PointNode.
        """
        distances, previous = self._dijkstra_multi_criteria(start_node_id, weights, graph)

        best: Optional[Tuple[Dict, PointNode, float]] = None
        for point_node in point_nodes:
            if point_node.node_id not in distances:
                continue  # this access node is unreachable from the start
            route = self._route_to(start_node_id, point_node.node_id, distances, previous)
            total = route['optimization_score'] + self._calculate_last_mile_score(point_node, weights)
            if best is None or total < best[2]:
                best = (route, point_node, total)
        return best

    async def calculate_route(
        self,
        from_node_slug: str,
        to_tourist_point_slug: str,
        time_weight: Optional[float] = None,
        cost_weight: Optional[float] = None,
        comfort_weight: Optional[float] = None,
        co2_weight: Optional[float] = None
    ) -> RouteResponse:
        """
        Calculate the optimal route from a node to a tourist point.

        Raises:
            RouteNotFoundError: node / point missing, or no path exists
            ValueError: invalid weights
        """
        weights = self._get_weights(time_weight, cost_weight, comfort_weight, co2_weight)
        start_node, point_nodes = await self._resolve(from_node_slug, to_tourist_point_slug)
        graph = await self._build_graph()

        best = self._best_route(start_node.id, point_nodes, weights, graph)
        if not best:
            raise RouteNotFoundError(
                f"No valid route found from '{from_node_slug}' to '{to_tourist_point_slug}'"
            )
        route_data, point_node, score = best
        return self._build_route_response(
            from_node_slug, to_tourist_point_slug, route_data, point_node, score
        )

    async def calculate_all_alternatives(
        self,
        from_node_slug: str,
        to_tourist_point_slug: str,
    ) -> RouteAlternativesResponse:
        """
        Calculate all profile alternatives in a single call — Rome2Rio style.

        The graph is loaded once and each profile costs one Dijkstra pass.
        Profiles that pick the same itinerary are merged into one entry.
        """
        start_node, point_nodes = await self._resolve(from_node_slug, to_tourist_point_slug)
        graph = await self._build_graph()

        # signature (segment ids + access option id) → alternative
        seen: Dict[tuple, RouteAlternative] = {}

        for profile_name in self.PROFILE_ORDER:
            best = self._best_route(start_node.id, point_nodes, self.PROFILES[profile_name], graph)
            if not best:
                continue
            route_data, point_node, score = best

            signature = tuple(seg.id for seg in route_data['path']) + (point_node.id,)
            if signature in seen:
                seen[signature].tags.append(f"Also {self.PROFILE_LABELS[profile_name]}")
                continue

            base_response = self._build_route_response(
                from_node_slug, to_tourist_point_slug, route_data, point_node, score
            )
            seen[signature] = RouteAlternative(
                **base_response.model_dump(),
                profile=profile_name,
                label="",           # assigned post-hoc by _assign_labels()
                is_recommended=False,
                tags=[],
            )

        if not seen:
            raise RouteNotFoundError(
                f"No valid route found from '{from_node_slug}' to '{to_tourist_point_slug}'"
            )

        ordered = list(seen.values())  # insertion order == PROFILE_ORDER
        self._assign_labels(ordered)

        return RouteAlternativesResponse(
            from_node=from_node_slug,
            to_tourist_point=to_tourist_point_slug,
            alternatives=ordered,
        )

    def _assign_labels(self, alternatives: List[RouteAlternative]) -> None:
        """
        Assign human-readable labels based on ACTUAL metric performance.

        WHY POST-HOC?
        Dijkstra with comfort_weight=0.8 doesn't guarantee the route with the
        highest average_comfort — other criteria (time, cost) still contribute
        20% of the score. A short cheap route with comfort=5 can beat a long
        expensive one with comfort=8 under that weighting.

        So instead of labeling by "which profile found this route", we compare
        all discovered alternatives directly on each raw metric:
          - Fastest  → lowest total_time_minutes
          - Cheapest → lowest total_cost
          - Comfort  → highest average_comfort
          - Eco      → lowest total_co2_kg
          - Optimal  → the route found by the balanced profile (always present)

        A route that doesn't win any criterion is left unlabeled (label="").
        If the Optimal route also wins a criterion (common when graph is sparse),
        that criterion is added to its tags.

        Mutates the list in-place.
        """
        if not alternatives:
            return

        def assign(winner: RouteAlternative, label: str) -> None:
            if not winner.label:
                winner.label = label
            else:
                # This route already has a label — add this as an extra tag
                winner.tags.append(label)

        # Find the genuine winner for each single-criterion metric
        fastest  = min(alternatives, key=lambda r: r.total_time_minutes)
        cheapest = min(alternatives, key=lambda r: float(r.total_cost))
        most_comfortable = max(alternatives, key=lambda r: r.average_comfort)
        ecofriendly = min(alternatives, key=lambda r: r.total_co2_kg)

        assign(fastest,          "Fastest")
        assign(cheapest,         "Cheapest")
        assign(most_comfortable, "Comfort")
        assign(ecofriendly,      "Eco")

        # The Optimal route is identified by its profile key (it's the one
        # the balanced algorithm chose), not by any single metric win.
        optimal = next((r for r in alternatives if r.profile == "optimal"), None)
        if optimal:
            optimal.is_recommended = True
            if not optimal.label:
                optimal.label = "Optimal"
            else:
                # Optimal route happens to also win a specific criterion —
                # keep that label as primary and append Optimal tag
                optimal.tags.append("Optimal")

    def _get_weights(
        self,
        time_weight: Optional[float],
        cost_weight: Optional[float],
        comfort_weight: Optional[float],
        co2_weight: Optional[float]
    ) -> Dict[str, float]:
        """
        Resolve Pareto weights.

        - Nothing supplied      → defaults from config.
        - Anything supplied     → the criteria you did NOT mention count as 0,
                                  and the result is rescaled to sum to 1.0.

        `is None` (not `or`) matters: 0.0 is a legitimate weight meaning
        "ignore this criterion", and `0.0 or default` would silently discard it.
        """
        supplied = {
            'time': time_weight, 'cost': cost_weight,
            'comfort': comfort_weight, 'co2': co2_weight,
        }
        if all(v is None for v in supplied.values()):
            weights = {
                'time': settings.default_time_weight,
                'cost': settings.default_cost_weight,
                'comfort': settings.default_comfort_weight,
                'co2': settings.default_co2_weight,
            }
        else:
            weights = {k: (v if v is not None else 0.0) for k, v in supplied.items()}

        if any(v < 0 for v in weights.values()):
            raise ValueError("Weights must not be negative")
        total = sum(weights.values())
        if total <= 0:
            raise ValueError("At least one weight must be greater than 0")
        return {k: v / total for k, v in weights.items()}

    def _dijkstra_multi_criteria(
        self,
        start_node_id: int,
        weights: Dict[str, float],
        graph: Graph,
    ) -> Tuple[Dict[int, Dict[str, float]], Dict[int, Tuple[int, TransportSegment]]]:
        """
        Multi-criteria Dijkstra from one start node to ALL reachable nodes.

        Each segment gets a single non-negative score (weighted sum of its
        scaled time / cost / comfort penalty / CO2). Dijkstra then minimises
        the SUM of those scores, which is valid precisely because every edge
        score is >= 0.

        Returns:
            distances: node_id → cumulative metrics on the best path to it
                       (always contains the start node itself, with zeros —
                       so "start == destination" is a valid 0-segment route)
            previous:  node_id → (previous node_id, segment used)
        """
        distances: Dict[int, Dict[str, float]] = {
            start_node_id: {'time': 0, 'cost': 0, 'comfort': 0, 'co2': 0, 'score': 0, 'distance': 0}
        }
        previous: Dict[int, Tuple[int, TransportSegment]] = {}
        # (score, node_id): heapq pops the smallest score first
        priority_queue: List[Tuple[float, int]] = [(0.0, start_node_id)]
        visited = set()

        while priority_queue:
            _, current_node = heapq.heappop(priority_queue)
            if current_node in visited:
                continue  # stale queue entry: a better path was already settled
            visited.add(current_node)
            current = distances[current_node]

            for neighbor_id, segment in graph.get(current_node, ()):
                if neighbor_id in visited:
                    continue

                new_score = current['score'] + self._calculate_segment_score(segment, weights)
                if neighbor_id in distances and new_score >= distances[neighbor_id]['score']:
                    continue

                distances[neighbor_id] = {
                    'time': current['time'] + segment.time_minutes,
                    'cost': current['cost'] + float(segment.cost),
                    # comfort is "higher is better", so accumulate the penalty
                    'comfort': current['comfort'] + (10 - segment.comfort_score),
                    'co2': current['co2'] + segment.co2_kg,
                    'distance': current['distance'] + segment.distance_km,
                    'score': new_score,
                }
                previous[neighbor_id] = (current_node, segment)
                heapq.heappush(priority_queue, (new_score, neighbor_id))

        return distances, previous

    def _route_to(
        self,
        start_node_id: int,
        end_node_id: int,
        distances: Dict[int, Dict[str, float]],
        previous: Dict[int, Tuple[int, TransportSegment]],
    ) -> Dict:
        """Turn Dijkstra's tables into a route dict for one destination node."""
        path = self._reconstruct_path(start_node_id, end_node_id, previous)
        total = distances[end_node_id]
        num_segments = len(path)
        avg_comfort = 10 - (total['comfort'] / num_segments) if num_segments > 0 else 0
        return {
            'path': path,
            'total_time': total['time'],
            'total_cost': total['cost'],
            'total_distance': total['distance'],
            'total_co2': total['co2'],
            'average_comfort': avg_comfort,
            'optimization_score': total['score'],
        }

    async def _build_graph(self) -> Graph:
        """
        Build adjacency list representation of the transport network.
        
        EXPLANATION:
        An adjacency list is a way to represent a graph in code.
        For each node, we store a list of its neighbors and how to reach them.
        
        Example:
        {
            1: [(2, train_segment), (3, bus_segment)],  # From node 1, can go to 2 or 3
            2: [(4, train_segment)],                     # From node 2, can go to 4
            ...
        }
        
        This makes it very fast to look up "what are all the places I can go from here?"
        
        Returns:
            Dictionary mapping node_id to list of (neighbor_id, segment) tuples
        """
        graph: Graph = {}
        
        # Query all transport segments from database
        result = await self.db.execute(
            select(TransportSegment)
            .options(joinedload(TransportSegment.from_node), joinedload(TransportSegment.to_node))
        )
        segments = result.scalars().all()
        
        # Build adjacency list
        for segment in segments:
            if segment.from_node_id not in graph:
                graph[segment.from_node_id] = []
            
            graph[segment.from_node_id].append((segment.to_node_id, segment))
        
        return graph
    
    # Scaling constants: they bring minutes / KZT / kg onto a comparable scale
    # ("one typical long segment" ≈ 1.0) so no criterion dominates merely
    # because its unit produces bigger numbers.
    #
    # They are NOT caps. An earlier version clamped each term with min(x, 1.0);
    # that made a 14-hour train and an 8-hour bus look equally slow (both
    # clamped to 1.0), so "Fastest" could pick the slower one. Scaling must stay
    # linear so that twice the time always costs twice the score.
    _MAX_SEG_TIME    = 480    # minutes
    _MAX_SEG_COST    = 30000  # KZT
    _MAX_SEG_COMFORT = 10     # comfort penalty (10 - comfort_score)
    _MAX_SEG_CO2     = 100    # kg

    def _weighted_score(
        self,
        weights: Dict[str, float],
        time_minutes: float,
        cost: float,
        comfort_score: float,
        co2_kg: float,
    ) -> float:
        """Weighted, scaled score of one leg (lower is better, never negative)."""
        return (
            weights['time']    * (time_minutes / self._MAX_SEG_TIME) +
            weights['cost']    * (cost / self._MAX_SEG_COST) +
            weights['comfort'] * (max(10 - comfort_score, 0) / self._MAX_SEG_COMFORT) +
            weights['co2']     * (co2_kg / self._MAX_SEG_CO2)
        )

    def _calculate_segment_score(
        self,
        segment: TransportSegment,
        weights: Dict[str, float]
    ) -> float:
        """Score contribution of a single TransportSegment."""
        return self._weighted_score(
            weights, segment.time_minutes, float(segment.cost),
            segment.comfort_score, segment.co2_kg,
        )

    def _reconstruct_path(
        self,
        start_node_id: int,
        end_node_id: int,
        previous: Dict[int, Tuple[int, TransportSegment]]
    ) -> List[TransportSegment]:
        """
        Walk backwards from the destination using `previous`, then reverse.

        previous = {4: (2, seg_2_4), 2: (1, seg_1_2)}, path 1→4:
        4 came from 2, 2 came from 1  →  [seg_1_2, seg_2_4]
        """
        path = []
        current = end_node_id
        while current != start_node_id:
            if current not in previous:
                raise ValueError("Path reconstruction failed - broken chain")
            prev_node, segment = previous[current]
            path.append(segment)
            current = prev_node
        path.reverse()
        return path

    def _calculate_last_mile_score(
        self,
        point_node: PointNode,
        weights: Dict[str, float]
    ) -> float:
        """
        Score of the last-mile leg, on the same scale as transport segments so
        different access options can be compared fairly.
        """
        # Rows created before auto-calculation existed may hold the column
        # defaults (co2 = 0, comfort = 5.0); derive sensible values for those.
        if point_node.co2_kg > 0:
            co2 = point_node.co2_kg
        else:
            co2 = CO2_PER_KM_ACCESS.get(point_node.access_type, 0.1) * point_node.distance_km

        constant_comfort = COMFORT_SCORE_ACCESS.get(point_node.access_type, 5.0)
        if point_node.comfort_score == 5.0 and constant_comfort != 5.0:
            comfort_val = constant_comfort
        else:
            comfort_val = point_node.comfort_score

        return self._weighted_score(
            weights, point_node.time_minutes, float(point_node.cost), comfort_val, co2,
        )

    def _build_route_response(
        self,
        from_node_slug: str,
        to_tourist_point_slug: str,
        route_data: Dict,
        point_node: PointNode,
        total_score: float
    ) -> RouteResponse:
        """
        Build the final RouteResponse object.
        
        Combines the main route with last-mile access information.
        
        Args:
            from_node_slug: Starting node slug
            to_tourist_point_slug: Destination tourist point slug
            route_data: Dictionary with route details from Dijkstra
            point_node: PointNode for last-mile access
            total_score: Combined optimization score
        
        Returns:
            RouteResponse object
        """
        # Convert path segments to RouteSegmentStep schemas
        route_steps = []
        for segment in route_data['path']:
            route_steps.append(
                RouteSegmentStep(
                    from_node_name=segment.from_node.name,
                    from_node_lat=segment.from_node.latitude,
                    from_node_lon=segment.from_node.longitude,
                    to_node_name=segment.to_node.name,
                    to_node_lat=segment.to_node.latitude,
                    to_node_lon=segment.to_node.longitude,
                    transport_mode=segment.transport_mode,
                    distance_km=segment.distance_km,
                    time_minutes=segment.time_minutes,
                    cost=segment.cost,
                    comfort_score=segment.comfort_score,
                    co2_kg=segment.co2_kg
                )
            )
        
        # Build last-mile access info
        last_mile = LastMileAccess(
            from_node_name=point_node.node.name,
            from_node_lat=point_node.node.latitude,
            from_node_lon=point_node.node.longitude,
            to_point_lat=point_node.tourist_point.latitude,
            to_point_lon=point_node.tourist_point.longitude,
            access_type=point_node.access_type,
            distance_km=point_node.distance_km,
            time_minutes=point_node.time_minutes,
            cost=point_node.cost,
            comfort_score=point_node.comfort_score,
            co2_kg=point_node.co2_kg,
            description=point_node.description
        )
        
        # Calculate totals (main route + last mile)
        total_distance = route_data['total_distance'] + point_node.distance_km
        total_time = route_data['total_time'] + point_node.time_minutes
        total_cost = route_data['total_cost'] + float(point_node.cost)
        total_co2 = route_data['total_co2'] + point_node.co2_kg
        
        # Recalculate average comfort including last mile
        # (Weight by proportion of segments + 1 for last mile)
        num_steps = len(route_steps)
        total_comfort_weighted = (route_data['average_comfort'] * num_steps) + point_node.comfort_score
        avg_comfort = total_comfort_weighted / (num_steps + 1)
        
        return RouteResponse(
            from_node=from_node_slug,
            to_tourist_point=to_tourist_point_slug,
            route_steps=route_steps,
            last_mile_access=last_mile,
            total_distance_km=round(total_distance, 2),
            total_time_minutes=total_time,
            total_cost=round(total_cost, 2),
            total_co2_kg=round(total_co2, 2),
            average_comfort=round(avg_comfort, 2),
            optimization_score=round(total_score, 4)
        )
