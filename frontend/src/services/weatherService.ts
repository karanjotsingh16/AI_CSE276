import { WeatherData, HourlyForecast } from '../types/weather';
import { calculateWeatherRiskScore } from '../logic/weatherRisk';

export async function fetchLiveWeatherData(
  lat: number,
  lng: number,
  locationName: string
): Promise<WeatherData> {
  const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat.toFixed(4)}&longitude=${lng.toFixed(4)}&hourly=precipitation_probability,precipitation,wind_speed_10m,temperature_2m&current_weather=true&forecast_days=2&timezone=auto`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000); // 8 second timeout

    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`Open-Meteo returned HTTP ${response.status}: ${response.statusText}`);
    }

    const json = await response.json();
    const hourly = json.hourly;
    const current = json.current_weather;

    if (!hourly || !hourly.time) {
      throw new Error('Invalid weather payload: missing hourly time array');
    }

    // Determine current hour index
    const nowIso = new Date().toISOString().substring(0, 13); // YYYY-MM-DDTHH
    let startIndex = hourly.time.findIndex((t: string) => t.startsWith(nowIso));
    if (startIndex === -1) startIndex = 0;

    // Collect next 6 hours
    const hourlyForecasts: HourlyForecast[] = [];
    let maxRainProb = 0;
    let maxPrecipMm = 0;

    for (let i = startIndex; i < startIndex + 6 && i < hourly.time.length; i++) {
      const timeStr = hourly.time[i];
      const prob = hourly.precipitation_probability ? (hourly.precipitation_probability[i] ?? 0) : 0;
      const precip = hourly.precipitation ? (hourly.precipitation[i] ?? 0) : 0;
      const temp = hourly.temperature_2m ? (hourly.temperature_2m[i] ?? 18) : 18;

      if (prob > maxRainProb) maxRainProb = prob;
      if (precip > maxPrecipMm) maxPrecipMm = precip;

      const hourLabel = new Date(timeStr).toLocaleTimeString([], { hour: 'numeric', hour12: true });
      hourlyForecasts.push({
        hour: hourLabel,
        prob,
        rainMm: precip,
        tempC: Math.round(temp)
      });
    }

    const currentProb = hourlyForecasts.length > 0 ? hourlyForecasts[0].prob : maxRainProb;
    const windSpeed = current ? Math.round(current.windspeed) : 12;
    const currentTemp = current ? Math.round(current.temperature) : (hourlyForecasts[0]?.tempC ?? 18);

    const riskEvaluation = calculateWeatherRiskScore({
      rainProbMax: maxRainProb,
      windSpeedKmh: windSpeed,
      precipitationMmMax: maxPrecipMm
    });

    return {
      state: 'success',
      locationName,
      lat,
      lng,
      currentRainProb: currentProb,
      hourlyRainProb: hourlyForecasts,
      windSpeedKmh: windSpeed,
      temperatureC: currentTemp,
      weatherRiskScore: riskEvaluation.score,
      riskClassification: riskEvaluation.classification,
      explanation: riskEvaluation.explanation,
      source: 'Open-Meteo Weather API (WMO 0.25° Seamless Numerical Model)',
      lastUpdated: new Date().toISOString()
    };
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : 'Network error';
    return {
      state: 'unavailable',
      locationName,
      lat,
      lng,
      currentRainProb: null,
      hourlyRainProb: [],
      windSpeedKmh: null,
      temperatureC: null,
      weatherRiskScore: null,
      riskClassification: 'UNAVAILABLE',
      explanation: 'Live weather service unreachable. Data could not be retrieved from Open-Meteo.',
      source: 'Open-Meteo Weather API',
      lastUpdated: null,
      errorDetails: errorMsg
    };
  }
}
