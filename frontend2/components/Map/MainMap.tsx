
import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, ZoomControl } from 'react-leaflet';
import L from 'leaflet';
import { TouristPoint, Region } from '../../types';
import { REGIONS_COORDINATES } from '../../constants';

const customMarkerIcon = (color: string = '#ef4444') => L.divIcon({
  className: 'custom-div-icon',
  html: `<div style="background-color: white; border: 2px solid ${color}; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 6px rgba(0,0,0,0.2);"><div style="background-color: ${color}; width: 10px; height: 10px; border-radius: 50%;"></div></div>`,
  iconSize: [24, 24],
  iconAnchor: [12, 12]
});

const ChangeView: React.FC<{ center: [number, number], zoom: number }> = ({ center, zoom }) => {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
  return null;
};

interface MainMapProps {
  points: TouristPoint[];
  selectedPoint: TouristPoint | null;
  onPointSelect: (point: TouristPoint) => void;
  selectedRegion: Region | null;
}

const MainMap: React.FC<MainMapProps> = ({ points, selectedPoint, onPointSelect, selectedRegion }) => {
  const defaultCenter: [number, number] = REGIONS_COORDINATES.CENTER as [number, number];
  
  return (
    <MapContainer center={defaultCenter} zoom={7} zoomControl={false} className="w-full h-full">
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; OpenStreetMap' />
      <ZoomControl position="bottomright" />
      
      {selectedRegion && !selectedPoint && <ChangeView center={defaultCenter} zoom={7} />}

      {points.map((point) => (
        <Marker 
          key={point.id} 
          position={[point.latitude, point.longitude]}
          icon={selectedPoint?.id === point.id ? customMarkerIcon('#2563eb') : customMarkerIcon('#ef4444')}
          eventHandlers={{ click: () => onPointSelect(point) }}
        >
          <Popup className="custom-popup">
            <div className="p-1 min-w-[120px]">
              <h3 className="font-bold text-gray-800 text-sm">{point.name}</h3>
              <p className="text-[10px] text-gray-500 font-semibold uppercase">{point.category.name}</p>
              <img src={point.image_url} alt={point.name} className="w-full h-24 object-cover mt-2 rounded shadow-sm" />
            </div>
          </Popup>
        </Marker>
      ))}

      {selectedPoint && <ChangeView center={[selectedPoint.latitude, selectedPoint.longitude]} zoom={11} />}
    </MapContainer>
  );
};

export default MainMap;
