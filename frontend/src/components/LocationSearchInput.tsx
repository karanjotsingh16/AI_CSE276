import React, { useState, useEffect } from 'react';
import {
  Search,
  Loader2,
  X,
  ChevronRight,
} from 'lucide-react';
import { GeocodedLocationResult } from '../types/geocoding';
import { searchLocations } from '../services/geocodingService';

interface LocationSearchInputProps {
  label: string;
  dotColor: 'emerald' | 'blue';
  selectedLocation: GeocodedLocationResult;
  suggestions: GeocodedLocationResult[];
  onSelectLocation: (loc: GeocodedLocationResult) => void;
}

export const LocationSearchInput: React.FC<LocationSearchInputProps> = ({
  label,
  dotColor,
  selectedLocation,
  suggestions,
  onSelectLocation,
}) => {
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [queryText, setQueryText] = useState<string>('');
  const [searchResults, setSearchResults] = useState<GeocodedLocationResult[]>([]);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState<boolean>(false);

  useEffect(() => {
    if (!isEditing) return;
    const trimmed = queryText.trim();
    if (trimmed.length < 2) {
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      setSearchError(null);
      try {
        const res = await searchLocations(trimmed, 6);
        setSearchResults(res.results);
        setHasSearched(true);
      } catch (err: unknown) {
        setSearchError(
          err instanceof Error ? err.message : 'Location lookup failed.'
        );
        setSearchResults([]);
        setHasSearched(true);
      } finally {
        setIsSearching(false);
      }
    }, 240);

    return () => clearTimeout(timer);
  }, [queryText, isEditing]);

  const handlePickCandidate = (item: GeocodedLocationResult) => {
    onSelectLocation(item);
    setIsEditing(false);
    setQueryText('');
    setSearchResults([]);
    setSearchError(null);
    setHasSearched(false);
  };

  const isRoutable = selectedLocation.coverage.within_loaded_graph;
  const isCatalogExpandable =
    selectedLocation.coverage.status === 'supported_region_not_downloaded';
  const shortName = selectedLocation.name.split(' (')[0];
  const dotClass =
    dotColor === 'emerald' ? 'bg-emerald-400' : 'bg-blue-400';

  const installedSuggestions = suggestions.filter(
    (s) => s.coverage.within_loaded_graph
  );
  const expandableNerSuggestions = suggestions.filter(
    (s) => !s.coverage.within_loaded_graph
  );

  return (
    <div className="bg-zinc-900/90 border border-zinc-800/90 hover:border-zinc-700/90 rounded-2xl p-4 transition-all duration-200">
      {!isEditing ? (
        <button
          type="button"
          onClick={() => {
            setIsEditing(true);
            setQueryText('');
            setSearchResults([]);
            setHasSearched(false);
          }}
          className="w-full text-left flex items-center justify-between gap-3 cursor-pointer group"
        >
          <div className="flex items-center gap-3.5 min-w-0">
            <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${dotClass}`} />
            <div className="min-w-0">
              <span className="text-[11px] font-medium text-zinc-400 block">
                {label}
              </span>
              <div className="text-base font-semibold text-white truncate mt-0.5">
                {shortName}
              </div>
              <div className="text-xs text-zinc-500 truncate mt-0.5">
                {selectedLocation.state} · {selectedLocation.lat.toFixed(4)}°N,{' '}
                {selectedLocation.lng.toFixed(4)}°E
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            <span
              className={`px-2.5 py-1 rounded-full text-[11px] font-medium ${
                isRoutable
                  ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
                  : isCatalogExpandable
                    ? 'bg-amber-500/10 text-amber-300 border border-amber-500/20'
                    : 'bg-rose-500/10 text-rose-300 border border-rose-500/20'
              }`}
            >
              {isRoutable
                ? 'In loaded graph'
                : isCatalogExpandable
                  ? 'Graph not downloaded'
                  : 'Outside coverage'}
            </span>
            <span className="text-xs text-zinc-400 group-hover:text-white transition-colors flex items-center gap-0.5">
              Change
              <ChevronRight className="w-3.5 h-3.5" />
            </span>
          </div>
        </button>
      ) : (
        <div className="space-y-3 animate-step-enter">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-zinc-400">{label}</span>
            <button
              type="button"
              onClick={() => {
                setIsEditing(false);
                setSearchError(null);
              }}
              className="text-xs text-zinc-400 hover:text-white flex items-center gap-1 cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
              Close
            </button>
          </div>

          <div className="relative">
            <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={queryText}
              onChange={(e) => {
                const v = e.target.value;
                setQueryText(v);
                if (v.trim().length < 2) {
                  setSearchResults([]);
                  setHasSearched(false);
                  setSearchError(null);
                }
              }}
              placeholder="Search NER city, district, or coordinates (25.5788, 91.8933)..."
              autoFocus
              className="w-full bg-zinc-950 border border-zinc-800 focus:border-zinc-600 rounded-xl pl-10 pr-9 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none transition-colors"
            />
            {isSearching && (
              <Loader2 className="w-4 h-4 text-zinc-400 animate-spin absolute right-3.5 top-1/2 -translate-y-1/2" />
            )}
          </div>

          {/* Quick-pick pills when input is empty */}
          {queryText.trim().length < 2 && installedSuggestions.length > 0 && (
            <div className="space-y-2 pt-0.5">
              <div className="text-[11px] text-zinc-500">
                Installed graph hubs (Meghalaya — ready to route)
              </div>
              <div className="flex flex-wrap gap-1.5">
                {installedSuggestions.slice(0, 8).map((sug) => {
                  const active = selectedLocation.place_id === sug.place_id;
                  return (
                    <button
                      key={sug.place_id}
                      type="button"
                      onClick={() => handlePickCandidate(sug)}
                      className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer flex items-center gap-1.5 ${
                        active
                          ? 'bg-white text-zinc-950'
                          : 'bg-zinc-950 text-zinc-300 hover:bg-zinc-800 border border-zinc-800'
                      }`}
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                      {sug.name.split(' (')[0]}
                    </button>
                  );
                })}
              </div>

              {expandableNerSuggestions.length > 0 && (
                <>
                  <div className="text-[11px] text-zinc-500 pt-1">
                    Expandable NER state corridors (require graph acquisition)
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {expandableNerSuggestions.slice(0, 8).map((sug) => {
                      const active = selectedLocation.place_id === sug.place_id;
                      return (
                        <button
                          key={sug.place_id}
                          type="button"
                          onClick={() => handlePickCandidate(sug)}
                          className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer flex items-center gap-1.5 ${
                            active
                              ? 'bg-white text-zinc-950'
                              : 'bg-zinc-950 text-zinc-400 hover:bg-zinc-800 border border-zinc-800/80'
                          }`}
                        >
                          <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                          {sug.name.split(' (')[0]}
                        </button>
                      );
                    })}
                  </div>
                </>
              )}
            </div>
          )}

          {searchError && (
            <div className="text-xs text-rose-400 px-1">{searchError}</div>
          )}

          {hasSearched && !isSearching && searchResults.length === 0 && !searchError && (
            <div className="text-xs text-zinc-400 px-1 py-1">
              No places found for "{queryText}". Try Shillong, Sohra, Mairang, Dawki, Guwahati, Imphal, or Gangtok.
            </div>
          )}

          {searchResults.length > 0 && (
            <div className="divide-y divide-zinc-800/60 border border-zinc-800 rounded-xl bg-zinc-950 overflow-hidden max-h-60 overflow-y-auto">
              {searchResults.map((cand) => {
                const ok = cand.coverage.within_loaded_graph;
                const expandable =
                  cand.coverage.status === 'supported_region_not_downloaded';
                return (
                  <button
                    key={`${cand.place_id}_${cand.lat}_${cand.lng}`}
                    type="button"
                    onClick={() => handlePickCandidate(cand)}
                    className="w-full text-left px-3.5 py-2.5 hover:bg-zinc-900 transition-colors cursor-pointer flex items-center justify-between gap-3"
                  >
                    <div className="min-w-0">
                      <div className="text-xs font-medium text-white truncate">
                        {cand.name.split(' (')[0]}
                      </div>
                      <div className="text-[11px] text-zinc-500 truncate">
                        {cand.state} · {cand.lat.toFixed(4)}°N, {cand.lng.toFixed(4)}°E
                      </div>
                    </div>
                    <span
                      className={`shrink-0 text-[10px] font-medium px-2 py-0.5 rounded-full ${
                        ok
                          ? 'bg-emerald-500/10 text-emerald-300'
                          : expandable
                            ? 'bg-amber-500/10 text-amber-300'
                            : 'bg-rose-500/10 text-rose-300'
                      }`}
                    >
                      {ok
                        ? 'In loaded graph'
                        : expandable
                          ? 'Expandable NER region'
                          : 'Outside coverage'}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
