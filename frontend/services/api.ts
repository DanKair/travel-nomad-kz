/**
 * API Service Layer - Enhanced Version
 * 
 * Fetches tourist_points_count dynamically from backend.
 * Falls back to mock data only when backend is unavailable.
 */

import axios from 'axios';

// API Base URL from environment variable
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Types (matching your backend)
export interface Region {
  id: number;
  name: string;
  description?: string;
  tourist_points_count?: number; // Optional - calculated dynamically
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
  description?: string;
  image_url?: string;
  latitude: number;
  longitude: number;
  region_id: number;
  category_id: number;
  region: Region;
  category: Category;
}

export enum TransportMode {
  PLANE = 'PLANE',
  TRAIN = 'TRAIN',
  BUS = 'BUS',
  TAXI = 'TAXI',
  MARSHRUTKA = 'MARSHRUTKA'
}

export type AccessType = 'WALK' | 'TAXI' | 'BUS' | 'SHUTTLE';
export type FilterType = 'fastest' | 'cheapest' | 'optimal' | 'comfort' | 'eco';

export interface RouteSegmentStep {
  from_node_name: string;
  from_node_lat: number;
  from_node_lon: number;
  to_node_name: string;
  to_node_lat: number;
  to_node_lon: number;
  transport_mode: TransportMode;
  distance_km: number;
  time_minutes: number;
  cost: number;
  comfort_score: number;
  co2_kg: number;
}

export interface LastMileAccess {
  from_node_name: string;
  from_node_lat: number;
  from_node_lon: number;
  to_point_lat: number;
  to_point_lon: number;
  access_type: AccessType;
  distance_km: number;
  time_minutes: number;
  cost: number;
  description?: string;
}

export interface RouteResponse {
  from_node: string;
  to_tourist_point: string;
  total_distance_km: number;
  total_time_minutes: number;
  total_cost: number;
  total_co2_kg: number;
  average_comfort: number;
  optimization_score: number;
  route_steps: RouteSegmentStep[];
  last_mile_access: LastMileAccess;
}

// ============================================================================
// MOCK DATA (Fallback only)
// ============================================================================

const MOCK_REGIONS: Region[] = [
  { id: 1, name: 'Almaty Region', description: 'Emerald lakes and high mountains.' },
  { id: 2, name: 'Turkestan Region', description: 'The spiritual heart of the Silk Road.' },
  { id: 3, name: 'Zhambyl Region', description: 'Ancient cities and historical mausoleums.' },
  { id: 4, name: 'Kyzylorda Region', description: 'Space gateways and the Aral Sea legacy.' },
];

const MOCK_POINTS: Record<number, TouristPoint[]> = {
  1: [
    {
      id: 101,
      name: 'Charyn Canyon',
      slug: 'charyn-canyon',
      description: 'A stunning 154km canyon along the Charyn River, often called Kazakhstan\'s Grand Canyon.',
      image_url: 'https://images.unsplash.com/photo-1580501170888-806608a0d3be?auto=format&fit=crop&w=800&q=80',
      latitude: 43.3569,
      longitude: 79.0844,
      region_id: 1,
      category_id: 1,
      region: MOCK_REGIONS[0],
      category: { id: 1, name: 'Canyon' }
    },
    {
      id: 102,
      name: 'Big Almaty Lake',
      slug: 'big-almaty-lake',
      description: 'A natural alpine reservoir located at 2,511 meters above sea level.',
      image_url: 'https://images.unsplash.com/photo-1548186105-0219602330a0?auto=format&fit=crop&w=800&q=80',
      latitude: 43.0506,
      longitude: 76.9850,
      region_id: 1,
      category_id: 2,
      region: MOCK_REGIONS[0],
      category: { id: 2, name: 'Lake' }
    }
  ],
  2: [
    {
      id: 201,
      name: 'Mausoleum of Khoja Ahmed Yasawi',
      slug: 'yasawi-mausoleum',
      description: 'An unfinished mausoleum in Turkestan, UNESCO World Heritage site.',
      image_url: 'https://images.unsplash.com/photo-1628153097241-7669d0382343?auto=format&fit=crop&w=800&q=80',
      latitude: 43.2973,
      longitude: 68.2710,
      region_id: 2,
      category_id: 3,
      region: MOCK_REGIONS[1],
      category: { id: 3, name: 'Historical' }
    }
  ]
};

// ============================================================================
// HELPER: Calculate tourist_points_count dynamically
// ============================================================================

/**
 * Enriches regions with dynamic tourist_points_count
 * by fetching all tourist points and counting per region.
 */
async function enrichRegionsWithCounts(regions: Region[]): Promise<Region[]> {
  try {
    // Fetch all tourist points from API
    const response = await axios.get(`${API_BASE_URL}/tourist-points`);
    const allPoints: TouristPoint[] = response.data;

    // Count points per region
    const countMap = new Map<number, number>();
    allPoints.forEach(point => {
      const current = countMap.get(point.region_id) || 0;
      countMap.set(point.region_id, current + 1);
    });

    // Add counts to regions
    return regions.map(region => ({
      ...region,
      tourist_points_count: countMap.get(region.id) || 0
    }));
  } catch (error) {
    console.warn('Failed to fetch tourist points for counting, using fallback');

    // Fallback: Calculate from mock data
    const countMap = new Map<number, number>();
    Object.values(MOCK_POINTS).flat().forEach(point => {
      const current = countMap.get(point.region_id) || 0;
      countMap.set(point.region_id, current + 1);
    });

    return regions.map(region => ({
      ...region,
      tourist_points_count: countMap.get(region.id) || 0
    }));
  }
}

// ============================================================================
// API METHODS
// ============================================================================

export const api = {
  /**
   * Get all regions with dynamic tourist_points_count
   */
  getRegions: async (): Promise<Region[]> => {
    try {
      // Fetch regions from backend
      const response = await axios.get(`${API_BASE_URL}/regions`);
      const regions: Region[] = response.data;

      // Enrich with dynamic counts
      return await enrichRegionsWithCounts(regions);
    } catch (error) {
      console.error('Backend unavailable, using mock regions:', error);
      return await enrichRegionsWithCounts(MOCK_REGIONS);
    }
  },

  /**
   * Get tourist points, optionally filtered by region
   */
  getTouristPoints: async (regionId?: number): Promise<TouristPoint[]> => {
    try {
      const params = regionId ? { region_id: regionId } : {};
      const response = await axios.get(`${API_BASE_URL}/tourist-points`, { params });
      return response.data;
    } catch (error) {
      console.error('Backend unavailable, using mock points:', error);

      if (regionId && MOCK_POINTS[regionId]) {
        return MOCK_POINTS[regionId];
      }
      return Object.values(MOCK_POINTS).flat();
    }
  },

  /**
   * Get single tourist point by ID
   */
  getTouristPoint: async (id: number): Promise<TouristPoint> => {
    try {
      const response = await axios.get(`${API_BASE_URL}/tourist-points/${id}`);
      return response.data;
    } catch (error) {
      console.error('Backend unavailable, using mock point:', error);

      const allPoints = Object.values(MOCK_POINTS).flat();
      const point = allPoints.find(p => p.id === id);

      if (point) return point;
      throw new Error(`Tourist point ${id} not found`);
    }
  },

  /**
   * Calculate optimal route
   */
  calculateRoute: async (
    from: string,
    to: string,
    filter: FilterType
  ): Promise<RouteResponse> => {
    try {
      // Build weight parameters based on filter
      const weights: Record<FilterType, any> = {
        fastest: { time_weight: 0.8, cost_weight: 0.1, comfort_weight: 0.05, co2_weight: 0.05 },
        cheapest: { time_weight: 0.1, cost_weight: 0.8, comfort_weight: 0.05, co2_weight: 0.05 },
        optimal: { time_weight: 0.4, cost_weight: 0.3, comfort_weight: 0.2, co2_weight: 0.1 },
        comfort: { time_weight: 0.15, cost_weight: 0.1, comfort_weight: 0.7, co2_weight: 0.05 },
        eco: { time_weight: 0.1, cost_weight: 0.1, comfort_weight: 0.1, co2_weight: 0.7 },
      };

      // Call backend routing API
      const response = await axios.get(`${API_BASE_URL}/routes`, {
        params: {
          from_node: from,
          to_tourist_point: to,
          ...weights[filter]
        }
      });

      return response.data;
    }
    catch (err: any) {
      // ✅ NEW: Throw proper errors instead
      console.error('❌ Route failed:', err.response?.data || err.message);

      if (err.response?.status === 404 || err.response?.status === 400) {
        throw new Error(`Route not found: ${err.response?.data?.detail || 'No valid route exists'}`);
      }

      if (!err.response) {
        throw new Error('Cannot connect to backend. Is it running on port 8000?');
      }

      throw new Error(`Failed to calculate route: ${err.message}`);
    }
  }
};

export default api;