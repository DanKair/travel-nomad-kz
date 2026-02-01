
import axios from 'axios';
import { API_BASE_URL } from '../constants';
import { Region, TouristPoint, RouteResponse, FilterType, TransportMode } from '../types';

const MOCK_REGIONS: Region[] = [
  { id: 1, name: 'Almaty Region', description: 'Emerald lakes and high mountains.', tourist_points_count: 23 },
  { id: 2, name: 'Turkestan Region', description: 'The spiritual heart of the Silk Road.', tourist_points_count: 15 },
  { id: 3, name: 'Zhambyl Region', description: 'Ancient cities and historical mausoleums.', tourist_points_count: 12 },
  { id: 4, name: 'Kyzylorda Region', description: 'Space gateways and the Aral Sea legacy.', tourist_points_count: 8 },
];

const MOCK_POINTS: Record<number, TouristPoint[]> = {
  1: [
    {
      id: 101,
      name: 'Charyn Canyon',
      slug: 'charyn-canyon',
      description: 'A stunning 154km canyon along the Charyn River, often called Kazakhstans Grand Canyon. Formed about 12 million years ago, it features unique "Castle Valley" formations.',
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
      description: 'A natural alpine reservoir located at 2,511 meters above sea level in the Trans-Ili Alatau mountains. Known for its changing turquoise color depending on the season.',
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
      description: 'An unfinished mausoleum in the city of Turkestan. Built in the 14th century, it is one of the best-preserved Timurid structures and a UNESCO World Heritage site.',
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

export const api = {
  getRegions: async (): Promise<Region[]> => {
    try {
      const response = await axios.get(`${API_BASE_URL}/regions`);
      return response.data;
    } catch (err) {
      return MOCK_REGIONS;
    }
  },

  getTouristPoints: async (regionId?: number): Promise<TouristPoint[]> => {
    try {
      const params = regionId ? { region_id: regionId } : {};
      const response = await axios.get(`${API_BASE_URL}/tourist-points`, { params });
      return response.data;
    } catch (err) {
      if (regionId && MOCK_POINTS[regionId]) {
        return MOCK_POINTS[regionId];
      }
      return Object.values(MOCK_POINTS).flat();
    }
  },

  getTouristPoint: async (id: number): Promise<TouristPoint> => {
    try {
      const response = await axios.get(`${API_BASE_URL}/tourist-points/${id}`);
      return response.data;
    } catch (err) {
      const allPoints = Object.values(MOCK_POINTS).flat();
      const point = allPoints.find(p => p.id === id);
      if (point) return point;
      throw err;
    }
  },

  calculateRoute: async (
    from: string,
    to: string,
    filter: FilterType
  ): Promise<RouteResponse> => {
    try {
      const weights: Record<FilterType, any> = {
        fastest: { time_weight: 0.8, cost_weight: 0.1, comfort_weight: 0.05, co2_weight: 0.05 },
        cheapest: { time_weight: 0.1, cost_weight: 0.8, comfort_weight: 0.05, co2_weight: 0.05 },
        optimal: { time_weight: 0.4, cost_weight: 0.3, comfort_weight: 0.2, co2_weight: 0.1 }
      };
      const response = await axios.get(`${API_BASE_URL}/routes`, { params: { from_node: from, to_tourist_point: to, ...weights[filter] } });
      return response.data;
    } catch (err) {
      const allPoints = Object.values(MOCK_POINTS).flat();
      const targetPoint = allPoints.find(p => p.slug === to) || allPoints[0];

      // Logic: If destination is in Almaty Region (Region ID 1), build a direct road route
      if (targetPoint.region_id === 1) {
        return {
          from_node: 'Almaty City Center',
          to_tourist_point: to,
          total_distance_km: 215,
          total_time_minutes: 180,
          total_cost: 8500,
          total_co2_kg: 25,
          average_comfort: 7.0,
          optimization_score: 0.95,
          route_steps: [
            {
              from_node_name: 'Almaty City Center', from_node_lat: 43.2566, from_node_lon: 76.9286,
              to_node_name: `${targetPoint.name} Entrance Node`, to_node_lat: targetPoint.latitude - 0.02, to_node_lon: targetPoint.longitude - 0.02,
              transport_mode: TransportMode.TAXI, distance_km: 210, time_minutes: 170, cost: 8000, comfort_score: 7, co2_kg: 24,
            }
          ],
          last_mile_access: {
            from_node_name: 'Park Entrance', from_node_lat: targetPoint.latitude - 0.02, from_node_lon: targetPoint.longitude - 0.02,
            to_point_lat: targetPoint.latitude, to_point_lon: targetPoint.longitude,
            access_type: 'WALK', distance_km: 5, time_minutes: 10, cost: 500, description: 'Final approach to the landmark.'
          }
        };
      }

      // Logic: If destination is in Turkestan Region (Region ID 2), use long-distance transport
      if (filter === 'fastest') {
        return {
          from_node: 'Almaty City Center',
          to_tourist_point: to,
          total_distance_km: 885,
          total_time_minutes: 145,
          total_cost: 32500,
          total_co2_kg: 120,
          average_comfort: 8.5,
          optimization_score: 0.942,
          route_steps: [
            {
              from_node_name: 'Almaty City Center', from_node_lat: 43.2566, from_node_lon: 76.9286,
              to_node_name: 'Almaty Airport (ALA)', to_node_lat: 43.3522, to_node_lon: 77.0405,
              transport_mode: TransportMode.TAXI, distance_km: 18.5, time_minutes: 30, cost: 3500, comfort_score: 8, co2_kg: 5,
            },
            {
              from_node_name: 'Almaty Airport (ALA)', from_node_lat: 43.3522, from_node_lon: 77.0405,
              to_node_name: 'Turkestan Airport (HSA)', to_node_lat: 43.3072, to_node_lon: 68.2140,
              transport_mode: TransportMode.PLANE, distance_km: 850, time_minutes: 85, cost: 28000, comfort_score: 9, co2_kg: 110,
            }
          ],
          last_mile_access: {
            from_node_name: 'Turkestan Airport', from_node_lat: 43.3072, from_node_lon: 68.2140,
            to_point_lat: targetPoint.latitude, to_point_lon: targetPoint.longitude,
            access_type: 'TAXI', distance_km: 12, time_minutes: 20, cost: 1500, description: 'Direct taxi to destination.'
          }
        };
      }

      // Default: Long distance Optimal path (Bus/Train)
      return {
        from_node: 'Almaty City Center',
        to_tourist_point: to,
        total_distance_km: 855,
        total_time_minutes: 600,
        total_cost: 12500,
        total_co2_kg: 65,
        average_comfort: 6.5,
        optimization_score: 0.910,
        route_steps: [
          {
            from_node_name: 'Almaty City Center', from_node_lat: 43.2566, from_node_lon: 76.9286,
            to_node_name: 'Sayran Bus Station', to_node_lat: 43.2389, to_node_lon: 76.8552,
            transport_mode: TransportMode.TAXI, distance_km: 8.5, time_minutes: 20, cost: 1500, comfort_score: 8, co2_kg: 3,
          },
          {
            from_node_name: 'Sayran Bus Station', from_node_lat: 43.2389, from_node_lon: 76.8552,
            to_node_name: 'Turkestan Bus Station', to_node_lat: 43.3105, to_node_lon: 68.2450,
            transport_mode: TransportMode.BUS, distance_km: 840, time_minutes: 540, cost: 6000, comfort_score: 5, co2_kg: 58,
          }
        ],
        last_mile_access: {
          from_node_name: 'Arrival Point', from_node_lat: 43.3105, from_node_lon: 68.2450,
          to_point_lat: targetPoint.latitude, to_point_lon: targetPoint.longitude,
          access_type: 'SHUTTLE', distance_km: 6.2, time_minutes: 25, cost: 500, description: 'Local shuttle service.'
        }
      };
    }
  }
};
