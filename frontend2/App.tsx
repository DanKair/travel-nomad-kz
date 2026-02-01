
import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar/Sidebar';
import MainMap from './components/Map/MainMap';
import TouristPointCard from './components/Main/TouristPointCard';
import RouteDisplay from './components/Main/RouteDisplay';
import { Region, TouristPoint, RouteResponse, FilterType } from './types';
import { api } from './services/api';

const App: React.FC = () => {
  const [regions, setRegions] = useState<Region[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null);
  const [points, setPoints] = useState<TouristPoint[]>([]);
  const [selectedPoint, setSelectedPoint] = useState<TouristPoint | null>(null);
  const [route, setRoute] = useState<RouteResponse | null>(null);
  const [activeFilter, setActiveFilter] = useState<FilterType>('optimal');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const regionsData = await api.getRegions();
        setRegions(regionsData);
        if (regionsData.length === 0) {
           setError('No regions found in the database.');
        }
      } catch (err) {
        console.error('Initial Load Error:', err);
        setError('Backend unreachable. Running in "Demo Mode" with local data.');
        // Clear error after 5 seconds to not obstruct the view
        setTimeout(() => setError(null), 5000);
      }
    };
    fetchData();
  }, []);

  const handleRegionSelect = async (region: Region) => {
    setSelectedRegion(region);
    setSelectedPoint(null);
    setRoute(null);
    try {
      const pointsData = await api.getTouristPoints(region.id);
      setPoints(pointsData);
    } catch (err) {
      setError('Failed to load tourist points.');
    }
  };

  const handlePointSelect = (point: TouristPoint) => {
    setSelectedPoint(point);
    setRoute(null);
  };

  const handleBuildRoute = async (filter: FilterType = 'optimal') => {
    if (!selectedPoint) return;
    setLoading(true);
    setError(null);
    setActiveFilter(filter);
    try {
      const routeData = await api.calculateRoute('almaty', selectedPoint.slug, filter);
      setRoute(routeData);
    } catch (err) {
      setError('Route calculation failed. Check if Almaty node exists in your DB.');
      setTimeout(() => setError(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-gray-50">
      {/* Sidebar */}
      <Sidebar 
        regions={regions} 
        selectedRegion={selectedRegion}
        points={points}
        selectedPoint={selectedPoint}
        onRegionSelect={handleRegionSelect}
        onPointSelect={handlePointSelect}
        onBackToRegions={() => setSelectedRegion(null)}
      />

      {/* Main Content Area */}
      <main className="relative flex-1 h-full">
        {/* Map View */}
        <div className="absolute inset-0 z-0">
          {route ? (
            <RouteDisplay 
              route={route} 
              onFilterChange={handleBuildRoute}
              activeFilter={activeFilter}
              isLoading={loading}
            />
          ) : (
            <MainMap 
              points={points} 
              selectedPoint={selectedPoint} 
              onPointSelect={handlePointSelect}
              selectedRegion={selectedRegion}
            />
          )}
        </div>

        {/* Floating Point Card Overlay */}
        {selectedPoint && !route && (
          <div className="absolute inset-0 z-10 flex items-center justify-center p-4 bg-black/20 backdrop-blur-sm pointer-events-none">
            <div className="pointer-events-auto">
              <TouristPointCard 
                point={selectedPoint} 
                onClose={() => setSelectedPoint(null)}
                onBuildRoute={() => handleBuildRoute()}
              />
            </div>
          </div>
        )}

        {/* Error Notification */}
        {error && (
          <div className="absolute bottom-6 right-6 z-50 bg-white border-l-4 border-amber-500 p-4 rounded-xl shadow-2xl max-w-sm animate-in fade-in slide-in-from-bottom-4 duration-300">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-amber-800 font-bold text-xs uppercase tracking-widest">Notice</p>
                <p className="text-gray-600 text-sm mt-1">{error}</p>
              </div>
              <button onClick={() => setError(null)} className="ml-4 text-gray-400 hover:text-gray-600">×</button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
