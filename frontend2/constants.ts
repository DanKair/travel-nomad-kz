
export const API_BASE_URL = 'http://localhost:8000';

export const TRANSPORT_COLORS: Record<string, string> = {
  PLANE: '#FF6B6B',     // Red
  TRAIN: '#4ECDC4',     // Teal
  BUS: '#95E1D3',       // Light Green
  TAXI: '#FFD93D',      // Yellow
  MARSHRUTKA: '#FFA07A', // Light Salmon
  WALK: '#6C5CE7'       // Purple
};

export const ACCESS_COLORS: Record<string, string> = {
  WALK: '#6C5CE7',      // Purple
  TAXI: '#FFD93D',      // Yellow
  BUS: '#95E1D3',       // Light Green
  SHUTTLE: '#A8E6CF',   // Mint
  CAR: '#2D3748'        // Dark Gray
};

export const REGIONS_COORDINATES = {
  ALMATY: [43.2220, 76.8512],
  CENTER: [43.2, 71.0],
  TURKESTAN: [43.2973, 68.2710],
  SHYMKENT: [42.3249, 69.5973]
};
