
import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar/Sidebar';
import MainMap from './components/Map/MainMap';
import TouristPointCard from './components/Main/TouristPointCard';
import RouteDisplay from './components/Main/RouteDisplay';
import { Region, TouristPoint, RouteAlternative, FilterType } from './types';
import { api } from './services/api';

const App: React.FC = () => {
  const [regions, setRegions] = useState<Region[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null);
  const [points, setPoints] = useState<TouristPoint[]>([]);
  const [selectedPoint, setSelectedPoint] = useState<TouristPoint | null>(null);
  // All profile alternatives loaded in a single fetch
  const [alternatives, setAlternatives] = useState<RouteAlternative[]>([]);
  const [activeFilter, setActiveFilter] = useState<FilterType>('optimal');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Derived: the route currently on display (matches active filter profile)
  const activeRoute = alternatives.find((a) => a.profile === activeFilter) ?? alternatives[0] ?? null;

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
    setAlternatives([]);
    try {
      const pointsData = await api.getTouristPoints(region.id);
      setPoints(pointsData);
    } catch (err) {
      setError('Failed to load tourist points.');
    }
  };

  const handlePointSelect = (point: TouristPoint) => {
    setSelectedPoint(point);
    setAlternatives([]);
  };

  /**
   * Fetch all route alternatives in one request, then set Optimal as active.
   * Subsequent filter clicks only change activeFilter — no new network call.
   */
  const handleBuildRoute = async () => {
    if (!selectedPoint) return;
    setLoading(true);
    setError(null);
    setActiveFilter('optimal'); // Reset to recommended profile on new fetch
    try {
      const data = await api.calculateAllRoutes('almaty', selectedPoint.slug);
      setAlternatives(data.alternatives);
    } catch (err: any) {
      console.error('❌ Route build failed:', err);

      let errorMessage = 'Unable to build route';
      if (err.message.includes('not found') || err.message.includes('Route not found')) {
        errorMessage =
          `❌ No route from Almaty to ${selectedPoint.name}\n\n` +
          `Possible causes:\n` +
          `• Missing transport segments\n` +
          `• No access point configured\n\n` +
          `Run: python scripts/check_routes.py`;
      } else if (err.message.includes('Cannot connect')) {
        errorMessage = '🔌 Backend not responding\nMake sure it\'s running on port 8000';
      } else {
        errorMessage = err.message;
      }

      setError(errorMessage);
      setTimeout(() => setError(null), 10000);
    } finally {
      setLoading(false);
    }
  };

  /** Pure view switch — no network request */
  const handleFilterChange = (filter: FilterType) => {
    setActiveFilter(filter);
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
          {activeRoute ? (
            <RouteDisplay
              route={activeRoute!}
              alternatives={alternatives}
              onFilterChange={handleFilterChange}
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
        {selectedPoint && !activeRoute && (
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
          <div className="absolute bottom-6 right-6 z-50 bg-white border-l-4 border-red-500 p-5 rounded-xl shadow-2xl max-w-md animate-in fade-in slide-in-from-bottom-4 duration-300">
            <div className="flex justify-between items-start gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  <p className="text-red-800 font-bold text-sm uppercase tracking-wide">Route Error</p>
                </div>
                <p className="text-gray-700 text-sm whitespace-pre-line leading-relaxed">{error}</p>
              </div>
              <button
                onClick={() => setError(null)}
                className="ml-2 text-gray-400 hover:text-gray-600 transition-colors text-2xl leading-none"
                aria-label="Close"
              >
                ×
              </button>
            </div>
          </div>
        )}

      </main>
    </div>
  );
};

export default App;
