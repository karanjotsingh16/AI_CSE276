import React from 'react';
import { CloudRain, Wind, RefreshCw, AlertCircle, Thermometer, Compass } from 'lucide-react';
import { WeatherData } from '../types/weather';
import { formatTimestamp } from '../logic/formatters';

interface WeatherIntelligenceCardProps {
  weather: WeatherData;
  onRefresh: () => void;
  isLoading?: boolean;
}

export const WeatherIntelligenceCard: React.FC<WeatherIntelligenceCardProps> = ({
  weather,
  onRefresh,
  isLoading
}) => {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm hover:shadow-md transition-all duration-300 p-4 text-slate-800">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center font-bold text-base shadow-2xs">
            🌧️
          </div>
          <div>
            <h2 className="text-[14px] font-bold text-slate-900 leading-none">Weather Intelligence</h2>
            <p className="text-[11px] text-slate-500 mt-0.5 font-medium">Live Open-Meteo Radar Feed</p>
          </div>
        </div>
        <button
          onClick={onRefresh}
          disabled={isLoading || weather.state === 'loading'}
          title="Refresh forecast"
          className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 transition-colors cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading || weather.state === 'loading' ? 'animate-spin text-blue-600' : ''}`} />
        </button>
      </div>

      {weather.state === 'loading' ? (
        <div className="py-8 flex flex-col items-center justify-center text-center">
          <div className="w-6 h-6 border-2 border-sky-500 border-t-transparent rounded-full animate-spin mb-2"></div>
          <p className="text-xs text-slate-500 font-medium">Querying atmospheric grid...</p>
        </div>
      ) : weather.state === 'unavailable' ? (
        <div className="p-3 bg-red-50 rounded-xl border border-red-200 text-center">
          <AlertCircle className="w-5 h-5 text-red-500 mx-auto mb-1" />
          <h4 className="text-xs font-bold text-red-800">Weather feed temporarily unavailable</h4>
          <button
            onClick={onRefresh}
            className="mt-2 px-3 py-1 bg-red-600 text-white text-xs font-bold rounded-lg cursor-pointer"
          >
            Retry Sync
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Main Weather HUD Strip */}
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="p-2.5 bg-gradient-to-br from-blue-50/60 to-indigo-50/40 rounded-xl border border-blue-100">
              <div className="flex items-center justify-center gap-1 text-blue-600 mb-0.5">
                <CloudRain className="w-3.5 h-3.5" />
                <span className="text-[10px] font-bold uppercase">Precip</span>
              </div>
              <span className="text-xl font-black text-slate-900">
                {weather.currentRainProb !== null ? `${weather.currentRainProb}%` : 'N/A'}
              </span>
            </div>

            <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
              <div className="flex items-center justify-center gap-1 text-slate-500 mb-0.5">
                <Wind className="w-3.5 h-3.5" />
                <span className="text-[10px] font-bold uppercase">Wind</span>
              </div>
              <span className="text-xl font-black text-slate-900">
                {weather.windSpeedKmh !== null ? `${weather.windSpeedKmh}k` : 'N/A'}
              </span>
            </div>

            <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
              <div className="flex items-center justify-center gap-1 text-amber-500 mb-0.5">
                <Thermometer className="w-3.5 h-3.5" />
                <span className="text-[10px] font-bold uppercase">Temp</span>
              </div>
              <span className="text-xl font-black text-slate-900">
                {weather.temperatureC !== null ? `${weather.temperatureC}°` : 'N/A'}
              </span>
            </div>
          </div>

          {/* 6-Hour Precipitation Probability Timeline */}
          {weather.hourlyRainProb && weather.hourlyRainProb.length > 0 && (
            <div className="bg-slate-50/80 p-2.5 rounded-xl border border-slate-200/80">
              <div className="flex items-center justify-between text-[11px] font-bold text-slate-700 mb-2">
                <span>Rainfall Risk Over Next 6 Hours</span>
                <span className="text-[9px] font-semibold text-slate-400">HOURLY FORECAST</span>
              </div>
              <div className="grid grid-cols-6 gap-1.5 text-center">
                {weather.hourlyRainProb.map((h, i) => (
                  <div key={i} className="flex flex-col items-center">
                    <span className="text-[9px] text-slate-400 font-bold mb-1">{h.hour}</span>
                    <div className="w-full bg-slate-200/80 h-9 rounded-md flex items-end p-0.5 overflow-hidden">
                      <div
                        className="w-full rounded-xs transition-all duration-300"
                        style={{
                          height: `${Math.max(14, h.prob)}%`,
                          backgroundColor: h.prob > 60 ? '#ef4444' : h.prob > 30 ? '#f59e0b' : '#3b82f6'
                        }}
                      />
                    </div>
                    <span className="text-[10px] font-extrabold text-slate-800 mt-1">{h.prob}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Status Verdict */}
          <div className="flex items-center justify-between px-3 py-2 bg-slate-50 rounded-xl border border-slate-100 text-xs">
            <span className="font-semibold text-slate-600">Weather Risk Score:</span>
            <div className="flex items-center gap-1.5">
              <span className="font-black text-slate-900">{weather.weatherRiskScore ?? 'N/A'}/100</span>
              <span className={`text-[9px] font-extrabold px-2 py-0.5 rounded-full uppercase ${
                weather.riskClassification === 'LOW'
                  ? 'bg-emerald-100 text-emerald-800'
                  : weather.riskClassification === 'MODERATE'
                  ? 'bg-amber-100 text-amber-800'
                  : 'bg-red-100 text-red-800'
              }`}>
                {weather.riskClassification}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
