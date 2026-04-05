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
        """
        Initialize routing service with database session.

        Args:
            db: SQLAlchemy database session for querying nodes and segments
        """
        self.db = db
    
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
        
        FLOW:
        1. Resolve starting node by slug
        2. Resolve destination tourist point by slug
        3. Get all PointNodes for the tourist point (multiple access options)
        4. For each PointNode, calculate route to its connected node
        5. Pick the best overall route
        6. Append last-mile access information
        
        Args:
            from_node_slug: Slug of starting node (e.g., "almaty")
            to_tourist_point_slug: Slug of destination tourist point
            time_weight: Optional custom weight for time criterion
            cost_weight: Optional custom weight for cost criterion
            comfort_weight: Optional custom weight for comfort criterion
            co2_weight: Optional custom weight for CO2 criterion
        
        Returns:
            RouteResponse with complete route details
        
        Raises:
            ValueError: If nodes/points not found or no valid route exists
        """
        
        # Set default weights if not provided
        weights = self._get_weights(time_weight, cost_weight, comfort_weight, co2_weight)
        
        # 1. Resolve starting node
        result = await self.db.execute(select(Node).filter(Node.slug == from_node_slug))
        start_node = result.scalars().first()
        if not start_node:
            raise ValueError(f"Starting node '{from_node_slug}' not found")
        
        # 2. Resolve destination tourist point
        result = await self.db.execute(
            select(TouristPoint).filter(TouristPoint.slug == to_tourist_point_slug)
        )
        tourist_point = result.scalars().first()
        if not tourist_point:
            raise ValueError(f"Tourist point '{to_tourist_point_slug}' not found")
        
        # 3. Get all PointNodes (last-mile access options) for this tourist point
        result = await self.db.execute(
            select(PointNode)
            .options(joinedload(PointNode.node), joinedload(PointNode.tourist_point))
            .filter(PointNode.tourist_point_id == tourist_point.id)
        )
        point_nodes = result.scalars().all()
        
        if not point_nodes:
            raise ValueError(
                f"No access points configured for tourist point '{to_tourist_point_slug}'"
            )
        
        # 4. Try routing to each PointNode and pick the best
        best_route = None
        best_score = float('inf')
        import logging
        logger = logging.getLogger(__name__)

        # Build graph once (shared across all PointNode attempts for this call)
        graph = await self._build_graph()

        for point_node in point_nodes:
            try:
                logger.info(f"Routing from {start_node.id} to PointNode.node_id {point_node.node_id}")
                # Calculate route from start to the node connected to this PointNode
                route = await self._dijkstra_multi_criteria(
                    start_node.id,
                    point_node.node_id,
                    weights,
                    graph=graph,
                )

                if route:
                    # Calculate total score including last-mile access
                    total_score = route['optimization_score']

                    # Add last-mile cost to score (weighted)
                    last_mile_score = self._calculate_last_mile_score(point_node, weights)
                    total_score += last_mile_score

                    logger.info(f"Route found to point_node {point_node.id}, score: {total_score}")

                    if total_score < best_score:
                        best_score = total_score
                        best_route = (route, point_node)
                else:
                    logger.warning(f"No path found to point_node {point_node.id} (node {point_node.node_id})")

            except Exception as e:
                logger.error(f"Error routing to point_node {point_node.id}: {str(e)}", exc_info=True)
                # If routing to this PointNode fails, try the next one
                continue

        if not best_route:
            raise ValueError(
                f"No valid route found from '{from_node_slug}' to '{to_tourist_point_slug}'"
            )

        # 5. Build the response with the best route + last-mile access
        route_data, point_node = best_route
        return self._build_route_response(
            from_node_slug,
            to_tourist_point_slug,
            route_data,
            point_node,
            best_score
        )

    async def calculate_all_alternatives(
        self,
        from_node_slug: str,
        to_tourist_point_slug: str,
    ) -> RouteAlternativesResponse:
        """
        Calculate all profile alternatives in a single call — Rome2Rio style.

        FLOW:
        1. Resolve nodes / tourist point / PointNodes (same as calculate_route)
        2. Build the transport graph ONCE (expensive DB query, shared across all profiles)
        3. For each profile in PROFILES, run Dijkstra with that profile's weights
           and pick the best PointNode access option
        4. Deduplicate: if two profiles produce the same path (identical segment IDs),
           merge their labels into `tags` on the winning entry
        5. Order results: Optimal first, then fastest/cheapest/comfort/eco
        6. Return RouteAlternativesResponse with all unique alternatives

        Args:
            from_node_slug: Starting node slug (e.g., "almaty")
            to_tourist_point_slug: Destination tourist point slug

        Returns:
            RouteAlternativesResponse with deduplicated profile alternatives
        """
        import logging
        logger = logging.getLogger(__name__)

        # --- Resolve nodes and access points (same as calculate_route) ---
        result = await self.db.execute(select(Node).filter(Node.slug == from_node_slug))
        start_node = result.scalars().first()
        if not start_node:
            raise ValueError(f"Starting node '{from_node_slug}' not found")

        result = await self.db.execute(
            select(TouristPoint).filter(TouristPoint.slug == to_tourist_point_slug)
        )
        tourist_point = result.scalars().first()
        if not tourist_point:
            raise ValueError(f"Tourist point '{to_tourist_point_slug}' not found")

        result = await self.db.execute(
            select(PointNode)
            .options(joinedload(PointNode.node), joinedload(PointNode.tourist_point))
            .filter(PointNode.tourist_point_id == tourist_point.id)
        )
        point_nodes = result.scalars().all()

        if not point_nodes:
            raise ValueError(
                f"No access points configured for tourist point '{to_tourist_point_slug}'"
            )

        # --- Build graph ONCE, reuse for all profiles ---
        graph = await self._build_graph()

        # --- Run each profile ---
        # Path signature: tuple of segment IDs in order, uniquely identifies a path.
        # Used for deduplication — same signature = same physical route.
        seen: Dict[tuple, RouteAlternative] = {}  # signature → RouteAlternative

        for profile_name in self.PROFILE_ORDER:
            weights = self.PROFILES[profile_name]
            best_route = None
            best_score = float('inf')

            for point_node in point_nodes:
                try:
                    route = await self._dijkstra_multi_criteria(
                        start_node.id,
                        point_node.node_id,
                        weights,
                        graph=graph,
                    )
                    if route:
                        total_score = route['optimization_score']
                        total_score += self._calculate_last_mile_score(point_node, weights)
                        if total_score < best_score:
                            best_score = total_score
                            best_route = (route, point_node)
                except Exception as e:
                    logger.error(f"[{profile_name}] Error routing to point_node {point_node.id}: {e}")
                    continue

            if not best_route:
                logger.warning(f"Profile '{profile_name}' found no valid route — skipping")
                continue

            route_data, point_node = best_route

            # Build path signature from the segment IDs
            path_signature = tuple(seg.id for seg in route_data['path'])
            # Include the point_node id so different access options are distinct
            full_signature = path_signature + (point_node.id,)

            if full_signature in seen:
                # Duplicate path — merge label as extra tag on the existing entry
                existing = seen[full_signature]
                existing.tags.append(f"Also {self.PROFILE_LABELS[profile_name]}")
                logger.info(
                    f"Profile '{profile_name}' is duplicate of '{existing.profile}' — merged as tag"
                )
            else:
                # Build a full RouteResponse for this profile.
                # Labels are intentionally left empty here — they will be
                # assigned post-hoc by _assign_labels() based on actual
                # metric performance, NOT by which profile discovered the path.
                base_response = self._build_route_response(
                    from_node_slug,
                    to_tourist_point_slug,
                    route_data,
                    point_node,
                    best_score,
                )
                alternative = RouteAlternative(
                    **base_response.model_dump(),
                    profile=profile_name,
                    label="",           # assigned post-hoc
                    is_recommended=False,
                    tags=[],
                )
                seen[full_signature] = alternative

        if not seen:
            raise ValueError(
                f"No valid route found from '{from_node_slug}' to '{to_tourist_point_slug}'"
            )

        ordered = list(seen.values())  # Already in PROFILE_ORDER insertion sequence

        # Assign labels based on what each route actually wins, not which
        # profile discovered it. Routes that don't win any criterion are unlabeled.
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
        Get Pareto weights for multi-criteria optimization.
        
        Uses provided weights or defaults from config.
        Validates that weights sum to 1.0.
        
        Returns:
            Dictionary with normalized weights
        """
        weights = {
            'time': time_weight or settings.default_time_weight,
            'cost': cost_weight or settings.default_cost_weight,
            'comfort': comfort_weight or settings.default_comfort_weight,
            'co2': co2_weight or settings.default_co2_weight
        }
        
        # Validate weights sum to approximately 1.0
        total = sum(weights.values())
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        
        return weights
    
    async def _dijkstra_multi_criteria(
        self,
        start_node_id: int,
        end_node_id: int,
        weights: Dict[str, float],
        graph: Optional[Dict[int, List[Tuple[int, TransportSegment]]]] = None,
    ) -> Optional[Dict]:
        """
        Multi-Criteria Dijkstra Algorithm with Pareto Weights.
        
        DETAILED STEP-BY-STEP EXPLANATION:
        
        1. BUILD THE GRAPH:
           - Query all TransportSegments from database
           - Create an adjacency list: {node_id: [(neighbor_id, segment), ...]}
           - This represents all possible connections in the transport network
        
        2. INITIALIZE DATA STRUCTURES:
           - distances: Stores the best cumulative metrics to reach each node
           - previous: Stores the path (which node we came from)
           - priority_queue: Min-heap to always process the lowest-cost node next
        
        3. ALGORITHM LOOP:
           - Start at the origin node with zero cost
           - While queue is not empty:
             a. Pop the node with lowest combined score
             b. If it's the destination, we're done!
             c. Otherwise, check all its neighbors
             d. For each neighbor, calculate new cumulative costs
             e. If this path is better, update and add to queue
        
        4. SCORING:
           - For each segment, we calculate 4 normalized scores (time, cost, comfort, CO2)
           - Combine them using Pareto weights: 
             total_score = (time × time_weight) + (cost × cost_weight) + ...
           - This gives a single number we can minimize
        
        5. PATH RECONSTRUCTION:
           - Once we reach the destination, backtrack using 'previous'
           - This gives us the sequence of nodes and segments
        
        Args:
            start_node_id: Starting node ID
            end_node_id: Destination node ID
            weights: Pareto weights for each criterion
        
        Returns:
            Dictionary with route details or None if no path exists
        """
        
        # Step 1: Build graph (adjacency list) from TransportSegments
        # Accept a pre-built graph to avoid redundant DB queries when called
        # multiple times in a single request (e.g., calculate_all_alternatives).
        if graph is None:
            graph = await self._build_graph()

        if start_node_id not in graph:
            return None
        
        # Step 2: Initialize data structures
        
        # distances: {node_id: {'time': X, 'cost': Y, 'comfort': Z, 'co2': W, 'score': S}}
        # This stores the best cumulative metrics we've found to reach each node
        distances: Dict[int, Dict[str, float]] = {}
        
        # previous: {node_id: (previous_node_id, segment)}
        # This allows us to reconstruct the path
        previous: Dict[int, Tuple[int, TransportSegment]] = {}
        
        # Priority queue: (combined_score, node_id)
        # Python's heapq is a min-heap, so smallest score is always popped first
        priority_queue: List[Tuple[float, int]] = []
        
        # Initialize start node with zero metrics
        distances[start_node_id] = {
            'time': 0,
            'cost': 0,
            'comfort': 0,
            'co2': 0,
            'score': 0,
            'distance': 0
        }
        heapq.heappush(priority_queue, (0, start_node_id))
        
        # Track visited nodes to avoid reprocessing
        visited = set()
        
        # Step 3: Main Dijkstra loop
        while priority_queue:
            # Pop node with smallest combined score
            current_score, current_node = heapq.heappop(priority_queue)
            
            # If we've reached the destination, we're done!
            if current_node == end_node_id:
                break
            
            # Skip if already visited (we found a better path earlier)
            if current_node in visited:
                continue
            
            visited.add(current_node)
            
            # Check all neighbors of current node
            if current_node not in graph:
                continue
            
            for neighbor_id, segment in graph[current_node]:
                # Skip if already visited
                if neighbor_id in visited:
                    continue
                
                # Calculate cumulative raw metrics (used in final response totals)
                new_time = distances[current_node]['time'] + segment.time_minutes
                new_cost = distances[current_node]['cost'] + float(segment.cost)
                new_distance = distances[current_node]['distance'] + segment.distance_km
                new_co2 = distances[current_node]['co2'] + segment.co2_kg
                
                # For comfort: we want HIGHER comfort to be BETTER
                # So we treat it as a penalty: (10 - comfort_score)
                comfort_penalty = (10 - segment.comfort_score)
                new_comfort = distances[current_node]['comfort'] + comfort_penalty
                
                # KEY FIX: Normalize and weight THIS SEGMENT individually, then
                # accumulate into the running score.
                # Previously: we accumulated raw totals and normalized once at the end
                #   → clamping to 1.0 destroyed weight differentiation for multi-hop routes
                # Now: each segment's score contribution is correctly bounded before summing
                seg_score = self._calculate_segment_score(segment, weights)
                new_score = distances[current_node]['score'] + seg_score
                
                # If this is the first time visiting neighbor, or if we found a better path
                if neighbor_id not in distances or new_score < distances[neighbor_id]['score']:
                    # Update the best metrics for this neighbor
                    distances[neighbor_id] = {
                        'time': new_time,
                        'cost': new_cost,
                        'comfort': new_comfort,
                        'co2': new_co2,
                        'distance': new_distance,
                        'score': new_score
                    }
                    
                    # Remember how we got here (for path reconstruction)
                    previous[neighbor_id] = (current_node, segment)
                    
                    # Add to queue for processing
                    heapq.heappush(priority_queue, (new_score, neighbor_id))
        
        # Step 4: Check if we found a path
        if end_node_id not in distances:
            return None  # No path exists
        
        # Step 5: Reconstruct path by backtracking
        path = self._reconstruct_path(start_node_id, end_node_id, previous)
        
        # Step 6: Calculate aggregated metrics
        total_metrics = distances[end_node_id]
        
        # Calculate average comfort (convert penalty back to score)
        num_segments = len(path)
        avg_comfort = 10 - (total_metrics['comfort'] / num_segments) if num_segments > 0 else 0
        
        return {
            'path': path,
            'total_time': total_metrics['time'],
            'total_cost': total_metrics['cost'],
            'total_distance': total_metrics['distance'],
            'total_co2': total_metrics['co2'],
            'average_comfort': avg_comfort,
            'optimization_score': total_metrics['score']
        }
    
    async def _build_graph(self) -> Dict[int, List[Tuple[int, TransportSegment]]]:
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
        graph: Dict[int, List[Tuple[int, TransportSegment]]] = {}
        
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
    
    # Normalization bounds per single segment
    # These represent the upper bound for a SINGLE segment's metric value.
    # Using per-segment bounds prevents clamping on multi-hop routes.
    _MAX_SEG_TIME    = 480   # 8 hours (longest single segment, e.g. long train/flight)
    _MAX_SEG_COST    = 30000 # 30,000 KZT (most expensive single ticket)
    _MAX_SEG_COMFORT = 10    # Comfort penalty per segment: (10 - comfort_score), range 0-10
    _MAX_SEG_CO2     = 100   # ~100 kg CO2 for a single long-haul flight

    def _calculate_segment_score(
        self,
        segment: TransportSegment,
        weights: Dict[str, float]
    ) -> float:
        """
        Calculate the weighted score contribution of a SINGLE segment.

        WHY PER-SEGMENT NORMALIZATION?
        The old approach accumulated raw totals (time, cost, …) across all
        segments, then normalized the cumulative total at the end.
        Problem: with MAX_COMFORT = 10 but a 3-hop trip producing comfort
        penalty = 15, the min() clamp made every multi-hop route score
        identically on comfort — completely erasing the effect of comfort_weight.

        By normalizing each segment independently, each hop's contribution is
        always within [0, weight_i], so the final accumulated score correctly
        reflects the chosen filter (fastest / cheapest / comfort / eco).

        Args:
            segment: A single TransportSegment
            weights: Pareto weights for each criterion

        Returns:
            Weighted normalized score for this one segment (lower is better)
        """
        norm_time    = min(segment.time_minutes         / self._MAX_SEG_TIME,    1.0)
        norm_cost    = min(float(segment.cost)          / self._MAX_SEG_COST,    1.0)
        norm_comfort = min((10 - segment.comfort_score) / self._MAX_SEG_COMFORT, 1.0)
        norm_co2     = min(segment.co2_kg               / self._MAX_SEG_CO2,     1.0)

        return (
            weights['time']    * norm_time    +
            weights['cost']    * norm_cost    +
            weights['comfort'] * norm_comfort +
            weights['co2']     * norm_co2
        )
    
    def _reconstruct_path(
        self,
        start_node_id: int,
        end_node_id: int,
        previous: Dict[int, Tuple[int, TransportSegment]]
    ) -> List[TransportSegment]:
        """
        Reconstruct the path from start to end by backtracking.
        
        EXPLANATION:
        During Dijkstra, we stored in 'previous' how we got to each node.
        Now we work backwards from the destination to the start,
        collecting all the segments we used.
        
        Example:
        If previous = {4: (2, seg_2_4), 2: (1, seg_1_2)}
        And we want path from 1 to 4:
        - Start at 4
        - 4 came from 2 via seg_2_4
        - 2 came from 1 via seg_1_2
        - Reverse the list: [seg_1_2, seg_2_4]
        
        Args:
            start_node_id: Starting node
            end_node_id: Ending node
            previous: Dictionary mapping node to (previous_node, segment)
        
        Returns:
            List of TransportSegments in order from start to end
        """
        path = []
        current = end_node_id
        
        # Backtrack from end to start
        while current != start_node_id:
            if current not in previous:
                # This shouldn't happen if algorithm worked correctly
                raise ValueError("Path reconstruction failed - broken chain")
            
            prev_node, segment = previous[current]
            path.append(segment)
            current = prev_node
        
        # Reverse to get start → end order
        path.reverse()
        return path
    
    def _calculate_last_mile_score(
        self,
        point_node: PointNode,
        weights: Dict[str, float]
    ) -> float:
        """
        Calculate normalized score for last-mile access.
        
        This uses the same normalization and weighting as the main route,
        so we can fairly compare different PointNode options.
        
        Args:
            point_node: PointNode entity with last-mile metrics
            weights: Pareto weights
        
        Returns:
            Normalized score for last-mile access
        """
        # Use metrics from model if they are non-zero (meaning they were manually set)
        # Otherwise fallback to distance-based calculation from constants
        if point_node.co2_kg > 0:
            co2 = point_node.co2_kg
        else:
            co2_per_km = CO2_PER_KM_ACCESS.get(point_node.access_type, 0.1)
            co2 = round(co2_per_km * point_node.distance_km, 3)

        # For comfort, if it's the default 5.0 and our constants have a different value,
        # we fallback to the constant.
        constant_comfort = COMFORT_SCORE_ACCESS.get(point_node.access_type, 5.0)
        if point_node.comfort_score == 5.0 and constant_comfort != 5.0:
            comfort_val = constant_comfort
        else:
            comfort_val = point_node.comfort_score

        # Use the same per-segment normalization bounds for a fair comparison
        norm_time    = min(point_node.time_minutes / self._MAX_SEG_TIME,    1.0)
        norm_cost    = min(float(point_node.cost)  / self._MAX_SEG_COST,    1.0)
        norm_comfort = min((10 - comfort_val)       / self._MAX_SEG_COMFORT, 1.0)
        norm_co2     = min(co2                      / self._MAX_SEG_CO2,     1.0)

        return (
            weights['time']    * norm_time    +
            weights['cost']    * norm_cost    +
            weights['comfort'] * norm_comfort +
            weights['co2']     * norm_co2
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
