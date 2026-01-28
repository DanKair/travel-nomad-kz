import { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import axios from 'axios';
import 'leaflet/dist/leaflet.css';
import './App.css';

// Fix Leaflet default marker icon issue with Vite
import L from 'leaflet';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
});

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [regions, setRegions] = useState([]);
  const [selectedRegion, setSelectedRegion] = useState(null);
  const [touristPoints, setTouristPoints] = useState([]);
  const [selectedPoint, setSelectedPoint] = useState(null);
  const [route, setRoute] = useState(null);
  const [loading, setLoading] = useState(false);

  // Route optimization criteria
  const [criteriaMode, setCriteriaMode] = useState('balanced');

  // Fetch regions on mount
  useEffect(() => {
    fetchRegions();
  }, []);

  const fetchRegions = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/regions`);
      setRegions(response.data);
    } catch (error) {
      console.error('Error fetching regions:', error);
    }
  };

  const handleRegionClick = async (region) => {
    setSelectedRegion(region);
    setSelectedPoint(null);
    setRoute(null);

    try {
      const response = await axios.get(
        `${API_BASE_URL}/tourist-points?region_id=${region.id}`
      );
      setTouristPoints(response.data);
    } catch (error) {
      console.error('Error fetching tourist points:', error);
    }
  };

  const handlePointClick = (point) => {
    setSelectedPoint(point);
    setRoute(null);
  };

  // Get weights based on selected criteria mode
  const getWeights = () => {
    const presets = {
      balanced: { time: 0.4, cost: 0.3, comfort: 0.2, co2: 0.1 },
      fastest: { time: 0.7, cost: 0.1, comfort: 0.1, co2: 0.1 },
      cheapest: { time: 0.1, cost: 0.7, comfort: 0.1, co2: 0.1 },
      comfortable: { time: 0.2, cost: 0.2, comfort: 0.5, co2: 0.1 },
      eco: { time: 0.2, cost: 0.2, comfort: 0.1, co2: 0.5 }
    };

    return presets[criteriaMode];
  };

  const calculateRoute = async () => {
    if (!selectedPoint) return;

    setLoading(true);
    const weights = getWeights();

    try {
      const response = await axios.get(
        `${API_BASE_URL}/routes`,
        {
          params: {
            from_node: 'almaty',
            to_tourist_point: selectedPoint.slug,
            time_weight: weights.time,
            cost_weight: weights.cost,
            comfort_weight: weights.comfort,
            co2_weight: weights.co2
          }
        }
      );
      setRoute(response.data);
    } catch (error) {
      console.error('Error calculating route:', error);
      alert('Failed to calculate route. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getCriteriaLabel = () => {
    const labels = {
      balanced: 'Balanced',
      fastest: 'Fastest Route',
      cheapest: 'Cheapest Route',
      comfortable: 'Most Comfortable',
      eco: 'Eco-Friendly'
    };
    return labels[criteriaMode] || 'Balanced';
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <h1>🗺️ Kazakhstan Tourism Routes</h1>
        <p>Explore Southern Kazakhstan from Almaty</p>
      </header>

      <div className="main-container">
        {/* Sidebar */}
        <aside className="sidebar">
          {/* Regions Section */}
          <section className="sidebar-section">
            <h2>Regions</h2>
            <div className="regions-list">
              {regions.map((region) => (
                <div
                  key={region.id}
                  className={`region-card ${selectedRegion?.id === region.id ? 'active' : ''
                    }`}
                  onClick={() => handleRegionClick(region)}
                >
                  <h3>{region.name}</h3>
                  <p>{region.description}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Tourist Points Section */}
          {selectedRegion && touristPoints.length > 0 && (
            <section className="sidebar-section">
              <h2>Tourist Points in {selectedRegion.name}</h2>
              <div className="tourist-points-list">
                {touristPoints.map((point) => (
                  <div
                    key={point.id}
                    className={`tourist-point-item ${selectedPoint?.id === point.id ? 'active' : ''
                      }`}
                    onClick={() => handlePointClick(point)}
                  >
                    <h4>{point.name}</h4>
                    <span className="category-badge">{point.category.name}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </aside>

        {/* Main Content */}
        <div className="main-content">
          {/* Map */}
          <div className="map-container">
            <MapContainer
              center={[43.2220, 76.8512]} // Almaty coordinates
              zoom={6}
              style={{ height: '100%', width: '100%' }}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              {/* Almaty marker (starting point) */}
              <Marker position={[43.2220, 76.8512]}>
                <Popup>
                  <strong>Almaty</strong><br />
                  Starting Point
                </Popup>
              </Marker>

              {/* Tourist points markers */}
              {touristPoints.map((point) => (
                <Marker
                  key={point.id}
                  position={[point.latitude, point.longitude]}
                  eventHandlers={{
                    click: () => handlePointClick(point),
                  }}
                >
                  <Popup>
                    <strong>{point.name}</strong><br />
                    {point.category.name}
                  </Popup>
                </Marker>
              ))}

              {/* Route polyline */}
              {route && selectedPoint && (
                <Polyline
                  positions={[
                    [43.2220, 76.8512], // Almaty
                    [selectedPoint.latitude, selectedPoint.longitude]
                  ]}
                  color="blue"
                  weight={3}
                  opacity={0.7}
                />
              )}
            </MapContainer>
          </div>

          {/* Tourist Point Detail Card */}
          {selectedPoint && (
            <div className="detail-card">
              <div className="detail-card-header">
                <h2>{selectedPoint.name}</h2>
                <span className="category-badge large">
                  {selectedPoint.category.name}
                </span>
              </div>

              <div className="detail-card-content">
                {/* Tourist Point Image */}
                {selectedPoint.image_url && (
                  <div className="detail-image">
                    <img
                      src={selectedPoint.image_url}
                      alt={selectedPoint.name}
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                  </div>
                )}

                <div className="detail-section">
                  <h3>📍 Location</h3>
                  <p>{selectedPoint.region.name}</p>
                  <p className="coordinates">
                    {selectedPoint.latitude.toFixed(4)}°N, {selectedPoint.longitude.toFixed(4)}°E
                  </p>
                </div>

                <div className="detail-section">
                  <h3>ℹ️ About</h3>
                  <p>{selectedPoint.description}</p>
                </div>

                {/* Route Criteria Selection */}
                {!route && (
                  <div className="detail-section criteria-section">
                    <h3>🎯 Route Optimization</h3>
                    <p className="criteria-subtitle">Choose your priority for route calculation:</p>

                    <div className="criteria-buttons">
                      <button
                        className={`criteria-btn ${criteriaMode === 'balanced' ? 'active' : ''}`}
                        onClick={() => setCriteriaMode('balanced')}
                      >
                        ⚖️ Balanced
                      </button>
                      <button
                        className={`criteria-btn ${criteriaMode === 'fastest' ? 'active' : ''}`}
                        onClick={() => setCriteriaMode('fastest')}
                      >
                        ⚡ Fastest
                      </button>
                      <button
                        className={`criteria-btn ${criteriaMode === 'cheapest' ? 'active' : ''}`}
                        onClick={() => setCriteriaMode('cheapest')}
                      >
                        💰 Cheapest
                      </button>
                      <button
                        className={`criteria-btn ${criteriaMode === 'comfortable' ? 'active' : ''}`}
                        onClick={() => setCriteriaMode('comfortable')}
                      >
                        🛋️ Comfortable
                      </button>
                      <button
                        className={`criteria-btn ${criteriaMode === 'eco' ? 'active' : ''}`}
                        onClick={() => setCriteriaMode('eco')}
                      >
                        🌱 Eco
                      </button>
                    </div>

                    <div className="criteria-info">
                      {criteriaMode === 'balanced' && <p>Equal balance of time, cost, comfort, and environmental impact</p>}
                      {criteriaMode === 'fastest' && <p>Prioritizes shortest travel time (70% weight on time)</p>}
                      {criteriaMode === 'cheapest' && <p>Prioritizes lowest cost (70% weight on price)</p>}
                      {criteriaMode === 'comfortable' && <p>Prioritizes comfort and convenience (50% weight on comfort)</p>}
                      {criteriaMode === 'eco' && <p>Prioritizes environmental sustainability (50% weight on CO2)</p>}
                    </div>
                  </div>
                )}

                {/* Route Information */}
                {route && (
                  <div className="detail-section route-info">
                    <h3>🚌 Route from Almaty <span className="criteria-label">({getCriteriaLabel()})</span></h3>

                    {route.route_steps.length > 0 ? (
                      <div className="route-steps">
                        {route.route_steps.map((step, index) => (
                          <div key={index} className="route-step">
                            <div className="route-step-header">
                              <span className="transport-mode">{step.transport_mode}</span>
                              <span className="route-arrow">→</span>
                              <span>{step.from_node_name} to {step.to_node_name}</span>
                            </div>
                            <div className="route-step-details">
                              <span>⏱️ {Math.floor(step.time_minutes / 60)}h {step.time_minutes % 60}m</span>
                              <span>💰 {step.cost} KZT</span>
                              <span>📏 {step.distance_km} km</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p>Direct access from Almaty</p>
                    )}

                    {/* Last Mile Access */}
                    <div className="last-mile">
                      <h4>Last Mile ({route.last_mile_access.access_type})</h4>
                      <p>{route.last_mile_access.description}</p>
                      <div className="route-step-details">
                        <span>⏱️ {route.last_mile_access.time_minutes} min</span>
                        <span>💰 {route.last_mile_access.cost} KZT</span>
                        <span>📏 {route.last_mile_access.distance_km} km</span>
                      </div>
                    </div>

                    {/* Total Summary */}
                    <div className="route-summary">
                      <h4>📊 Total</h4>
                      <div className="summary-grid">
                        <div className="summary-item">
                          <span className="label">Time</span>
                          <span className="value">
                            {Math.floor(route.total_time_minutes / 60)}h {route.total_time_minutes % 60}m
                          </span>
                        </div>
                        <div className="summary-item">
                          <span className="label">Cost</span>
                          <span className="value">{route.total_cost} KZT</span>
                        </div>
                        <div className="summary-item">
                          <span className="label">Distance</span>
                          <span className="value">{route.total_distance_km} km</span>
                        </div>
                        <div className="summary-item">
                          <span className="label">Comfort</span>
                          <span className="value">{route.average_comfort.toFixed(1)}/10</span>
                        </div>
                      </div>
                    </div>

                    {/* Try Different Criteria Button */}
                    <button
                      className="recalculate-btn"
                      onClick={() => setRoute(null)}
                    >
                      🔄 Try Different Criteria
                    </button>
                  </div>
                )}

                {/* Calculate Route Button */}
                {!route && (
                  <button
                    className="calculate-route-btn"
                    onClick={calculateRoute}
                    disabled={loading}
                  >
                    {loading ? 'Calculating...' : '🧭 Calculate Route from Almaty'}
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Empty State */}
          {!selectedPoint && (
            <div className="empty-state">
              <h2>👈 Select a region to explore tourist destinations</h2>
              <p>Click on a region in the sidebar to see available tourist points</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
