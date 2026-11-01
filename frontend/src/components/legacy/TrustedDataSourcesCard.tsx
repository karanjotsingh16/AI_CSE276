import React from 'react';
import { ExternalLink } from 'lucide-react';
import { TrustedDataSource } from '../../types/sources';

interface TrustedDataSourcesCardProps {
  sources: TrustedDataSource[];
}

export const TrustedDataSourcesCard: React.FC<TrustedDataSourcesCardProps> = ({ sources }) => {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm hover:shadow-md transition-all duration-300 p-4 text-slate-800">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-700 flex items-center justify-center font-bold text-base shadow-2xs">
            🔎
          </div>
          <div>
            <h2 className="text-[14px] font-bold text-slate-900 leading-none">Trusted Data Sources</h2>
            <p className="text-[11px] text-slate-500 mt-0.5 font-medium">Verified Geospatial Provenance</p>
          </div>
        </div>
        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
          {sources.length} Verified
        </span>
      </div>

      <div className="space-y-1.5">
        {sources.map(src => (
          <div
            key={src.id}
            className="p-2.5 rounded-xl border border-slate-100 bg-slate-50/60 hover:bg-white hover:border-slate-300 transition-all text-left text-xs flex items-center justify-between group"
          >
            <div className="pr-2">
              <a
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-bold text-slate-900 group-hover:text-blue-600 transition-colors flex items-center gap-1 text-[11px]"
              >
                <span>{src.name}</span>
                <ExternalLink className="w-2.5 h-2.5 text-slate-400 group-hover:text-blue-600" />
              </a>
              <span className="text-[10px] text-slate-400 block mt-0.5">{src.provider}</span>
            </div>

            <span
              className={`text-[9px] font-extrabold px-2 py-0.5 rounded-full uppercase tracking-wider shrink-0 ${
                src.status === 'Live Connected'
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-slate-200 text-slate-700'
              }`}
            >
              {src.status === 'Live Connected' ? '● LIVE' : src.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
