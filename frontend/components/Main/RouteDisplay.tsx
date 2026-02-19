
import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap, ZoomControl } from 'react-leaflet';
import L from 'leaflet';
import { RouteResponse, RouteSegmentStep, FilterType, TransportMode, LastMileAccess } from '../../types';
import { TRANSPORT_COLORS, ACCESS_COLORS } from '../../constants';
import FilterToggles from './FilterToggles';
import RouteDetailPanel from './RouteDetailPanel';
import { getRouteGeometry, getBatchRouteGeometries } from '../../utils/geoUtils';
import { Clock, Banknote, Map as MapIcon, Shield, Leaf, Info, Navigation, List } from 'lucide-react';
// Fix Leaflet default marker icons
import 'leaflet/dist/leaflet.css';

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const RouteUpdater: React.FC<{ segments: RouteSegmentStep[], lastMile?: LastMileAccess }> = ({ segments, lastMile }) => {
  const map = useMap();
  useEffect(() => {
    if (segments.length > 0) {
      const points = segments.map(s => [s.from_node_lat || 43.2, s.from_node_lon || 76.9] as [number, number]);
      if (lastMile?.to_point_lat) {
        points.push([lastMile.to_point_lat, lastMile.to_point_lon!]);
      }
      const bounds = L.latLngBounds(points);
      map.fitBounds(bounds, { padding: [80, 80] });
    }
  }, [segments, lastMile, map]);
  return null;
};

const getModeIcon = (mode: string) => {
  const m = mode.toUpperCase(); // normalize — API returns lowercase ("plane", "bus", etc)
  const color = TRANSPORT_COLORS[m] || ACCESS_COLORS[m] || '#3b82f6';

  const SVGS: Record<string, string> = {
    PLANE: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/></svg>',
    TRAIN: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="16" height="16" x="4" y="3" rx="2"/><path d="M4 11h16M12 3v8M8 19l-2 3M16 19l2 3"/></svg>',
    BUS: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 17h2a1 1 0 0 0 1-1V7a2 2 0 0 0-2-2H3a2 2 0 0 0-2 2v9a1 1 0 0 0 1 1h2"/><circle cx="7" cy="17" r="2"/><path d="M9 17h6"/><circle cx="17" cy="17" r="2"/></svg>',
    TAXI: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 17H3a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h1l2-3h8l2 3h1a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2h-2"/><circle cx="7" cy="17" r="2"/><path d="M9 17h6"/><circle cx="17" cy="17" r="2"/><path d="M7 9h10"/></svg>',
    MARSHRUTKA: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="13" rx="2"/><path d="M1 9h22M8 4v13M16 4v13"/><circle cx="5" cy="20" r="2"/><circle cx="19" cy="20" r="2"/></svg>',
    WALK: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="4" r="1.5"/><path d="m9 20 1-5-2-3 3-3 2 3h4M9 8l-1 4 3 1"/></svg>',
  };

  const svg = SVGS[m] || SVGS.BUS; // fallback to bus

  const iconHtml = `
    <div style="background-color: white; border: 2px solid ${color}; border-radius: 50%; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
      <div style="color: ${color}; width: 16px; height: 16px;">${svg}</div>
    </div>`;

  return L.divIcon({
    className: 'custom-div-icon',
    html: iconHtml,
    iconSize: [28, 28],
    iconAnchor: [14, 14]
  });
};

interface RouteDisplayProps {
  route: RouteResponse;
  onFilterChange: (filter: FilterType) => void;
  activeFilter: FilterType;
  isLoading: boolean;
}

const RouteDisplay: React.FC<RouteDisplayProps> = ({ route, onFilterChange, activeFilter, isLoading }) => {
  const [segmentsWithGeo, setSegmentsWithGeo] = useState<RouteSegmentStep[]>([]);
  const [lastMileWithGeo, setLastMileWithGeo] = useState<LastMileAccess | null>(null);
  const [selectedSegment, setSelectedSegment] = useState<RouteSegmentStep | LastMileAccess | null>(null);
  const [showDetailPanel, setShowDetailPanel] = useState(false);

  useEffect(() => {
    const fetchGeometries = async () => {
      console.log('🔄 Fetching route geometries...');

      try {
        // Prepare all segment pairs
        const segmentPairs = route.route_steps.map(step => ({
          from: [step.from_node_lat!, step.from_node_lon!] as [number, number],
          to: [step.to_node_lat!, step.to_node_lon!] as [number, number]
        }));

        // Fetch ALL in parallel (much faster!)
        const geometries = await getBatchRouteGeometries(segmentPairs);

        const updatedSteps = route.route_steps.map((step, idx) => ({
          ...step,
          geometry: geometries[idx]
        }));

        setSegmentsWithGeo(updatedSteps);
        console.log('✅ All geometries loaded');

        // Handle last mile
        if (route.last_mile_access) {
          const start: [number, number] = [
            route.last_mile_access.from_node_lat!,
            route.last_mile_access.from_node_lon!
          ];
          const end: [number, number] = [
            route.last_mile_access.to_point_lat!,
            route.last_mile_access.to_point_lon!
          ];
          const geo = await getRouteGeometry(start, end);
          setLastMileWithGeo({ ...route.last_mile_access, geometry: geo });
        }
      } catch (error) {
        console.error('❌ Failed to load geometries:', error);
      }
    };

    fetchGeometries();
  }, [route]);

  const isBackboneStep = (s: any): s is RouteSegmentStep => 'transport_mode' in s;

  return (
    <div className="relative w-full h-full">
      <MapContainer center={[43.2, 71.0]} zoom={7} zoomControl={false} className="w-full h-full">
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; OpenStreetMap' />
        <ZoomControl position="bottomright" />
        <RouteUpdater segments={segmentsWithGeo} lastMile={lastMileWithGeo || undefined} />

        {/* Journey Segments (Transport Nodes) - Solid thick lines */}
        {segmentsWithGeo.map((segment, idx) => {
          // Extract transport mode from enum format (e.g., "TransportMode.PLANE" -> "PLANE")
          const modeKey = segment.transport_mode.toString().split('.').pop() || segment.transport_mode.toString();
          return (
            <Polyline
              key={`step-${idx}`}
              positions={segment.geometry || []}
              pathOptions={{
                color: TRANSPORT_COLORS[modeKey] || '#3388ff',
                weight: 8,
                opacity: 1.0,
                lineCap: 'round',
              }}
              eventHandlers={{ click: () => setSelectedSegment(segment) }}
            />
          );
        })}

        {/* Destination Approach (Last Mile) - Now same thickness/style as main journey */}
        {lastMileWithGeo && (
          <Polyline
            positions={lastMileWithGeo.geometry || []}
            pathOptions={{
              color: ACCESS_COLORS[lastMileWithGeo.access_type.toUpperCase()] || '#6C5CE7',
              weight: 8,
              opacity: 1.0,
              lineCap: 'round',
            }}
            eventHandlers={{ click: () => setSelectedSegment(lastMileWithGeo) }}
          />
        )}

        {/* Mode-specific Markers for transfers */}
        {segmentsWithGeo.map((step, idx) => {
          // Show the icon representing the NEXT segment departing from this node
          // For the last node, show the current segment's mode as it's the arrival
          const nextSegment = segmentsWithGeo[idx + 1];
          const modeKey = nextSegment
            ? (nextSegment.transport_mode.toString().split('.').pop() || nextSegment.transport_mode.toString())
            : (step.transport_mode.toString().split('.').pop() || step.transport_mode.toString());
          return (
            <Marker
              key={`node-${idx}`}
              position={[step.to_node_lat!, step.to_node_lon!]}
              icon={getModeIcon(modeKey)}
            >
              <Popup className="font-semibold text-xs">{step.to_node_name}</Popup>
            </Marker>
          );
        })}

        {/* JOURNEY ORIGIN — falls back to last-mile start when no backbone segments */}
        {(segmentsWithGeo.length > 0 || lastMileWithGeo) && (() => {
          // Prefer the first backbone segment's origin; fall back to last-mile node coords
          const lat = segmentsWithGeo.length > 0
            ? segmentsWithGeo[0].from_node_lat!
            : lastMileWithGeo!.from_node_lat!;
          const lon = segmentsWithGeo.length > 0
            ? segmentsWithGeo[0].from_node_lon!
            : lastMileWithGeo!.from_node_lon!;
          const label = segmentsWithGeo.length > 0
            ? `Start: ${segmentsWithGeo[0].from_node_name}`
            : `Start: ${lastMileWithGeo!.from_node_name}`;
          return (
            <Marker
              position={[lat, lon]}
              icon={L.divIcon({
                className: 'origin-marker',
                html: `<div style="background-color: #3b82f6; border: 3px solid white; border-radius: 50%; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(59, 130, 246, 0.4);"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg></div>`,
                iconSize: [36, 36],
                iconAnchor: [18, 18]
              })}
            >
              <Popup className="font-bold">{label}</Popup>
            </Marker>
          );
        })()}

        {/* JOURNEY GOAL: FINAL DESTINATION */}
        {lastMileWithGeo && (
          <Marker
            position={[lastMileWithGeo.to_point_lat!, lastMileWithGeo.to_point_lon!]}
            icon={L.divIcon({
              className: 'destination-marker',
              html: `<div style="background-color: #ef4444; border: 3px solid white; border-radius: 50%; width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 15px rgba(239, 68, 68, 0.5);"><svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg></div>`,
              iconSize: [48, 48],
              iconAnchor: [24, 48]
            })}
          >
            <Popup className="font-bold">Goal Destination Reached!</Popup>
          </Marker>
        )}

        {selectedSegment && (
          <Popup position={selectedSegment.geometry ? selectedSegment.geometry[Math.floor(selectedSegment.geometry.length / 2)] : [43.2, 76.9]} onClose={() => setSelectedSegment(null)}>
            <div className="p-2 min-w-[200px]">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-3 h-3 rounded-full" style={{
                  backgroundColor: isBackboneStep(selectedSegment)
                    ? TRANSPORT_COLORS[selectedSegment.transport_mode.toString().split('.').pop() || selectedSegment.transport_mode.toString()]
                    : ACCESS_COLORS[selectedSegment.access_type.toUpperCase()]
                }} />
                <span className="font-bold text-gray-800 uppercase text-xs tracking-wider">
                  {isBackboneStep(selectedSegment)
                    ? (selectedSegment.transport_mode.toString().split('.').pop() || selectedSegment.transport_mode.toString())
                    : `Arrival Method: ${selectedSegment.access_type}`}
                </span>
              </div>
              <div className="text-sm font-semibold text-gray-700 mb-2">
                {selectedSegment.from_node_name} → {isBackboneStep(selectedSegment) ? selectedSegment.to_node_name : 'Final Target'}
              </div>
              <div className="grid grid-cols-2 gap-2 border-t pt-2">
                <div className="flex items-center gap-1.5 text-[11px] text-gray-500"><Clock className="w-3 h-3" /> {Math.floor(selectedSegment.time_minutes / 60)}h {selectedSegment.time_minutes % 60}m</div>
                <div className="flex items-center gap-1.5 text-[11px] text-gray-500"><Banknote className="w-3 h-3" /> {selectedSegment.cost.toLocaleString()} KZT</div>
                <div className="flex items-center gap-1.5 text-[11px] text-gray-500"><MapIcon className="w-3 h-3" /> {selectedSegment.distance_km.toFixed(1)} km</div>
              </div>
            </div>
          </Popup>
        )}
      </MapContainer>

      {/* Info Overlay */}
      <div className="absolute top-6 left-6 z-[1000] flex flex-col gap-4">
        <FilterToggles onFilterChange={onFilterChange} activeFilter={activeFilter} isLoading={isLoading} />
        <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-5 w-64 border border-white/50 animate-in slide-in-from-left duration-500">
          <h3 className="text-sm font-bold text-gray-800 mb-4 flex items-center gap-2">
            <Navigation className="w-4 h-4 text-blue-500" /> Almaty → Destination
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center text-xs text-gray-500 font-medium">
              <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" /> Est. Time</span>
              <span className="text-gray-800 font-bold">{Math.floor(route.total_time_minutes / 60)}h {route.total_time_minutes % 60}m</span>
            </div>
            <div className="flex justify-between items-center text-xs text-gray-500 font-medium">
              <span className="flex items-center gap-1"><Banknote className="w-3.5 h-3.5" /> Total Price</span>
              <span className="text-green-600 font-bold">{route.total_cost.toLocaleString()} KZT</span>
            </div>
            <div className="flex justify-between items-center text-xs text-gray-500 font-medium">
              <span className="flex items-center gap-1"><Shield className="w-3.5 h-3.5" /> Comfort</span>
              <span className="text-blue-600 font-bold">{route.average_comfort}/10</span>
            </div>
            <div className="flex justify-between items-center text-xs text-gray-500 font-medium border-t pt-2 mt-2">
              <span className="flex items-center gap-1"><Leaf className="w-3.5 h-3.5" /> CO2 Burden</span>
              <span className="text-gray-800 font-bold">{route.total_co2_kg} kg</span>
            </div>
            <div className="border-t pt-3 mt-1">
              <button
                onClick={() => setShowDetailPanel(true)}
                className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-blue-50 hover:bg-blue-100 text-blue-600 text-xs font-bold transition-colors"
              >
                <List className="w-3.5 h-3.5" />
                Route Steps
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Rome2Rio-style detail panel */}
      {showDetailPanel && (
        <RouteDetailPanel
          route={route}
          onClose={() => setShowDetailPanel(false)}
        />
      )}
    </div>
  );
};

export default RouteDisplay;
