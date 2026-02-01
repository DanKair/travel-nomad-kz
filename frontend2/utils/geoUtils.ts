
const OSRM_BASE = 'https://router.project-osrm.org/route/v1/driving';

export const getRouteGeometry = async (
  from: [number, number],
  to: [number, number]
): Promise<[number, number][]> => {
  try {
    const url = `${OSRM_BASE}/${from[1]},${from[0]};${to[1]},${to[0]}?geometries=geojson&overview=full`;
    const response = await fetch(url);
    const data = await response.json();
    
    if (data.routes && data.routes[0]) {
      return data.routes[0].geometry.coordinates.map(
        ([lon, lat]: [number, number]) => [lat, lon]
      );
    }
  } catch (error) {
    console.error('OSRM Fetch Error:', error);
  }
  return [from, to];
};
