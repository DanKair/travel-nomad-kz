const OSRM_BASE = 'https://router.project-osrm.org/route/v1/driving';
const routeCache = new Map<string, [number, number][]>();
const MAX_CACHE_SIZE = 100;

const calculateHaversineDistance = (
  from: [number, number],
  to: [number, number]
): number => {
  const R = 6371e3; // Earth radius in meters
  const φ1 = (from[0] * Math.PI) / 180;
  const φ2 = (to[0] * Math.PI) / 180;
  const Δφ = ((to[0] - from[0]) * Math.PI) / 180;
  const Δλ = ((to[1] - from[1]) * Math.PI) / 180;

  const a =
    Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
    Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c;
};

/** Generate a curved path for flight arcs */
const generateArcPoints = (
  from: [number, number],
  to: [number, number],
  pointsCount: number = 30
): [number, number][] => {
  const points: [number, number][] = [];
  const [lat1, lon1] = from;
  const [lat2, lon2] = to;

  // Calculate distance to scale the arc height
  const dist = Math.sqrt(Math.pow(lat2 - lat1, 2) + Math.pow(lon2 - lon1, 2));
  const arcHeight = dist * 0.15; // 15% of distance as arc height

  for (let i = 0; i <= pointsCount; i++) {
    const t = i / pointsCount;
    // Linear interpolation for basic path
    let lat = lat1 + (lat2 - lat1) * t;
    let lon = lon1 + (lon2 - lon1) * t;

    // Quadratic lift (sin wave or parabola)
    const lift = Math.sin(Math.PI * t) * arcHeight;

    // In a real map, "up" is usually positive latitude, 
    // but for very vertical paths we might need to adjust.
    // For now, we'll lift latitude.
    points.push([lat + lift, lon]);
  }
  return points;
};

export const getRouteGeometry = async (
  from: [number, number],
  to: [number, number],
  mode: string = 'CAR'
): Promise<[number, number][]> => {
  const modeKey = mode.toUpperCase().replace('TRANSPORTMODE.', '');
  const cacheKey = `${modeKey}-${from[0].toFixed(4)},${from[1].toFixed(4)}-${to[0].toFixed(4)},${to[1].toFixed(4)}`;

  if (routeCache.has(cacheKey)) {
    return routeCache.get(cacheKey)!;
  }

  const directDistance = calculateHaversineDistance(from, to);

  // LOGIC: Select drawing method based on transport mode
  // 1. Arc for planes
  if (modeKey === 'PLANE') {
    const arc = generateArcPoints(from, to);
    routeCache.set(cacheKey, arc);
    return arc;
  }

  // 2. Straight line for cable cars / specific modes if specified
  if (modeKey === 'CABLE_CAR') {
    return [from, to];
  }

  // 3. OSRM for others (Cars, Buses, Taxis)
  try {
    const url = `${OSRM_BASE}/${from[1]},${from[0]};${to[1]},${to[0]}?geometries=geojson&overview=full`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4000); // 4s timeout

    const response = await fetch(url, {
      signal: controller.signal,
      mode: 'cors'
    });

    clearTimeout(timeoutId);

    if (response.ok) {
      const data = await response.json();
      if (data.routes && data.routes[0]) {
        const osrmDistance = data.routes[0].distance;
        const detourFactor = osrmDistance / directDistance;

        // DETOUR PROTECTION: 
        // If OSRM propose a detour > 3x, it's likely a border or mapping issue.
        if (detourFactor > 3 && directDistance > 1000) {
          console.warn(`🚨 Path Detour detected (${detourFactor.toFixed(1)}x for ${modeKey}). Snapping to direct line.`);
          return [from, to];
        }

        const geometry = data.routes[0].geometry.coordinates.map(
          ([lon, lat]: [number, number]) => [lat, lon] as [number, number]
        );

        if (routeCache.size >= MAX_CACHE_SIZE) {
          const firstKey = routeCache.keys().next().value;
          routeCache.delete(firstKey);
        }
        routeCache.set(cacheKey, geometry);
        return geometry;
      }
    }
  } catch (error) {
    console.warn(`⚠️ OSRM failed for ${modeKey}, using direct line`, error);
  }

  return [from, to];
};

export const getBatchRouteGeometries = async (
  segments: Array<{ from: [number, number]; to: [number, number]; mode: string }>
): Promise<[number, number][][]> => {
  console.log(`🚀 Batch fetching ${segments.length} geometries...`);

  const results = await Promise.all(
    segments.map(seg => getRouteGeometry(seg.from, seg.to, seg.mode))
  );

  return results;
};