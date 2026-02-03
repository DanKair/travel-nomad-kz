const OSRM_BASE = 'https://router.project-osrm.org/route/v1/driving';
const routeCache = new Map<string, [number, number][]>();
const MAX_CACHE_SIZE = 100;

export const getRouteGeometry = async (
  from: [number, number],
  to: [number, number]
): Promise<[number, number][]> => {
  const cacheKey = `${from[0].toFixed(4)},${from[1].toFixed(4)}-${to[0].toFixed(4)},${to[1].toFixed(4)}`;
  
  if (routeCache.has(cacheKey)) {
    console.log('✅ Cache hit for route');
    return routeCache.get(cacheKey)!;
  }

  try {
    const url = `${OSRM_BASE}/${from[1]},${from[0]};${to[1]},${to[0]}?geometries=geojson&overview=full`;
    console.log('🌐 Fetching route from OSRM...');
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    
    const response = await fetch(url, { 
      signal: controller.signal,
      mode: 'cors'
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      throw new Error(`OSRM HTTP ${response.status}`);
    }
    
    const data = await response.json();
    
    if (data.routes && data.routes[0]) {
      const geometry = data.routes[0].geometry.coordinates.map(
        ([lon, lat]: [number, number]) => [lat, lon] as [number, number]
      );
      
      if (routeCache.size >= MAX_CACHE_SIZE) {
        const firstKey = routeCache.keys().next().value;
        routeCache.delete(firstKey);
      }
      routeCache.set(cacheKey, geometry);
      
      console.log(`✅ Cached route with ${geometry.length} points`);
      return geometry;
    }
  } catch (error) {
    console.warn('⚠️ OSRM error, using straight line:', error);
  }
  
  return [from, to];
};

export const getBatchRouteGeometries = async (
  segments: Array<{ from: [number, number]; to: [number, number] }>
): Promise<[number, number][][]> => {
  console.log(`🚀 Batch fetching ${segments.length} routes in parallel...`);
  const startTime = Date.now();
  
  const results = await Promise.all(
    segments.map(seg => getRouteGeometry(seg.from, seg.to))
  );
  
  const duration = Date.now() - startTime;
  console.log(`✅ Batch complete in ${duration}ms`);
  
  return results;
};