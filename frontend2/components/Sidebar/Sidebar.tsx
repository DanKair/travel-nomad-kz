
import React from 'react';
import { Region, TouristPoint } from '../../types';
import { ChevronRight, ArrowLeft, MapPin, Map as MapIcon, Compass } from 'lucide-react';

interface SidebarProps {
  regions: Region[];
  selectedRegion: Region | null;
  points: TouristPoint[];
  selectedPoint: TouristPoint | null;
  onRegionSelect: (region: Region) => void;
  onPointSelect: (point: TouristPoint) => void;
  onBackToRegions: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  regions,
  selectedRegion,
  points,
  selectedPoint,
  onRegionSelect,
  onPointSelect,
  onBackToRegions
}) => {
  return (
    <aside className="w-80 h-full bg-white border-r border-gray-200 shadow-xl flex flex-col z-40 transition-all duration-300">
      <div className="p-6 border-b border-gray-100 bg-gray-50">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-blue-600 rounded-lg shadow-md">
            <Compass className="text-white w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-800">RoutePlanner</h1>
            <p className="text-xs text-gray-500 font-medium">Southern Kazakhstan</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {!selectedRegion ? (
          <div className="py-2">
            <div className="px-6 py-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                <MapIcon className="w-4 h-4" /> Regions
              </h2>
            </div>
            {regions.map((region) => (
              <button
                key={region.id}
                onClick={() => onRegionSelect(region)}
                className="w-full group px-6 py-4 flex items-center justify-between hover:bg-blue-50 transition-colors border-l-4 border-transparent hover:border-blue-500"
              >
                <div className="text-left">
                  <div className="font-semibold text-gray-700 group-hover:text-blue-700 transition-colors">
                    {region.name}
                  </div>
                  <div className="text-xs text-gray-400">
                    {region.tourist_points_count || 0} destinations
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-blue-500" />
              </button>
            ))}
          </div>
        ) : (
          <div>
            <button
              onClick={onBackToRegions}
              className="w-full px-6 py-4 flex items-center gap-3 hover:bg-gray-100 text-gray-500 border-b border-gray-100 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm font-medium">Back to Regions</span>
            </button>
            <div className="px-6 py-5 bg-blue-50/50">
              <h2 className="text-lg font-bold text-gray-800">{selectedRegion.name}</h2>
              <p className="text-xs text-gray-500 mt-1 line-clamp-1">{selectedRegion.description}</p>
            </div>
            <div className="py-2">
              {points.length > 0 ? (
                points.map((point) => (
                  <button
                    key={point.id}
                    onClick={() => onPointSelect(point)}
                    className={`w-full px-4 py-3 flex items-start gap-3 hover:bg-gray-50 border-l-4 transition-all ${
                      selectedPoint?.id === point.id 
                        ? 'bg-blue-50 border-blue-500 shadow-sm' 
                        : 'border-transparent'
                    }`}
                  >
                    <div className="relative flex-shrink-0">
                      <img
                        src={point.image_url || `https://picsum.photos/seed/${point.id}/100/100`}
                        alt={point.name}
                        className="w-16 h-16 rounded-lg object-cover shadow-sm"
                      />
                      <div className="absolute -bottom-1 -right-1 bg-white p-1 rounded-full shadow-sm">
                        <MapPin className="w-3 h-3 text-red-500" />
                      </div>
                    </div>
                    <div className="text-left">
                      <div className={`font-bold text-sm ${selectedPoint?.id === point.id ? 'text-blue-700' : 'text-gray-800'}`}>
                        {point.name}
                      </div>
                      <div className="text-[10px] text-gray-400 font-medium uppercase mt-0.5 tracking-tight">
                        {point.category.name}
                      </div>
                      <p className="text-[11px] text-gray-500 mt-1 line-clamp-2 leading-tight">
                        {point.description}
                      </p>
                    </div>
                  </button>
                ))
              ) : (
                <div className="p-10 text-center text-gray-400 text-sm">
                  No points found in this region.
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="p-4 border-t border-gray-100 bg-gray-50">
        <div className="text-[10px] text-gray-400 text-center uppercase tracking-widest font-bold">
          Powered by OSRM & Leaflet
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
