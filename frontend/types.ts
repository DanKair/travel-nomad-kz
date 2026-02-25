
export enum TransportMode {
  PLANE = 'PLANE',
  TRAIN = 'TRAIN',
  BUS = 'BUS',
  TAXI = 'TAXI',
  MARSHRUTKA = 'MARSHRUTKA',
  CAR = 'CAR',
  CABLE_CAR = 'CABLE_CAR',
  WALK = 'WALK'
}

export interface Region {
  id: number;
  name: string;
  description?: string;
  tourist_points_count?: number;
}

export interface Category {
  id: number;
  name: string;
  parent_id?: number;
}

export interface TouristPoint {
  id: number;
  name: string;
  slug: string;
  description: string;
  image_url: string;
  latitude: number;
  longitude: number;
  region_id: number;
  category_id: number;
  region: Region;
  category: Category;

  // Optional metadata fields
  elevation_m?: number | null;
  best_season?: string | null;
  accessibility?: string | null;
}

export interface RouteSegmentStep {
  from_node_name: string;
  from_node_lat?: number;
  from_node_lon?: number;
  to_node_name: string;
  to_node_lat?: number;
  to_node_lon?: number;
  transport_mode: TransportMode;
  distance_km: number;
  time_minutes: number;
  cost: number;
  comfort_score: number;
  co2_kg: number;
  geometry?: [number, number][]; // Polylines for display
}

export interface LastMileAccess {
  from_node_name: string;
  from_node_lat?: number;
  from_node_lon?: number;
  to_point_lat?: number; // Added to map to the actual destination
  to_point_lon?: number; // Added to map to the actual destination
  access_type: string;
  distance_km: number;
  time_minutes: number;
  cost: number;
  description?: string;
  geometry?: [number, number][];
}

export interface RouteResponse {
  from_node: string;
  to_tourist_point: string;
  route_steps: RouteSegmentStep[];
  last_mile_access: LastMileAccess;
  total_distance_km: number;
  total_time_minutes: number;
  total_cost: number;
  total_co2_kg: number;
  average_comfort: number;
  optimization_score: number;
}

export type FilterType = 'fastest' | 'cheapest' | 'optimal' | 'comfort' | 'eco';
