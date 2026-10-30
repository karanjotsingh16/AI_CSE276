export type WeatherState = 'loading' | 'success' | 'stale' | 'unavailable' | 'invalid_coords';
export type RiskClassification = 'LOW' | 'MODERATE' | 'HIGH' | 'SEVERE' | 'UNAVAILABLE';

export interface HourlyForecast {
  hour: string;
  prob: number;      // 0-100%
  rainMm: number;    // precipitation amount in mm
  tempC: number;
}

export interface WeatherData {
  state: WeatherState;
  locationName: string;
  lat: number;
  lng: number;
  currentRainProb: number | null;
  hourlyRainProb: HourlyForecast[];
  windSpeedKmh: number | null;
  temperatureC: number | null;
  weatherRiskScore: number | null;
  riskClassification: RiskClassification;
  explanation: string;
  source: string;
  lastUpdated: string | null;
  errorDetails?: string;
}
