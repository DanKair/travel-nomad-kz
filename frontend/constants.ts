
export const API_BASE_URL = '/api';

// Backbone transport segment colors (strong, saturated)
export const TRANSPORT_COLORS: Record<string, string> = {
  PLANE: '#E74C3C',       // Bold Red
  TRAIN: '#3498DB',       // Royal Blue
  BUS: '#2ECC71',         // Emerald Green
  TAXI: '#F39C12',        // Amber Orange
  MARSHRUTKA: '#9B59B6',  // Purple
  CAR: '#1ABC9C',         // Teal — private car on road network
  CABLE_CAR: '#87CEEB',    // Sky Blue — aerial, scenic, mountain
};

// Last-mile access colors — deliberately distinct from transport palette
export const ACCESS_COLORS: Record<string, string> = {
  WALK: '#6C5CE7',  // Indigo (walking path)
  TAXI: '#FFD93D',  // Yellow (user requested)
  BUS: '#00CEC9',  // Cyan (local city bus)
  SHUTTLE: '#A8E6CF',  // Mint
  CAR: '#636E72',  // Slate Gray
};

export const REGIONS_COORDINATES = {
  ALMATY: [43.2220, 76.8512],
  CENTER: [43.2, 71.0],
  TURKESTAN: [43.2973, 68.2710],
  SHYMKENT: [42.3249, 69.5973]
};
