import React from 'react';
import { ExternalLink, Clock, Tag, RefreshCw, AlertCircle, Newspaper } from 'lucide-react';
import { DisasterNewsItem, NewsSourceState } from '../../types/news';
import { formatTimestamp } from '../../logic/formatters';

interface DisasterNewsCardProps {
  news: DisasterNewsItem[];
  state: NewsSourceState;
  statusMessage: string;
  onRefresh?: () => void;
  isLoading?: boolean;
}

export const DisasterNewsCard: React.FC<DisasterNewsCardProps> = ({
  news,
  state,
  statusMessage,
  onRefresh,
  isLoading
}) => {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm hover:shadow-md transition-all duration-300 p-4 text-slate-800">
      {/* Header with mandatory Title & Subtitle */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center font-bold text-base shadow-2xs">
            🧠
          </div>
          <div>
            <h2 className="text-[14px] font-bold text-slate-900 leading-none">
              AI Disaster News Intelligence
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5 font-medium">
              External News Intelligence — Not Official Government Alerts
            </p>
          </div>
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isLoading || state === 'loading'}
            title="Refresh news feed"
            className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading || state === 'loading' ? 'animate-spin text-blue-600' : ''}`} />
          </button>
        )}
      </div>

      {/* State Handlers */}
      {state === 'loading' || isLoading ? (
        <div className="py-6 flex flex-col items-center justify-center text-center">
          <div className="w-5 h-5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mb-2"></div>
          <p className="text-xs text-slate-500 font-medium">Scanning regional disaster news feeds...</p>
        </div>
      ) : state === 'unavailable' ? (
        <div className="py-4 px-3 bg-slate-50 rounded-xl border border-slate-200 text-center text-slate-600 text-xs">
          <AlertCircle className="w-5 h-5 text-slate-400 mx-auto mb-1.5" />
          <p className="font-bold text-slate-800">External news feed unavailable.</p>
          <p className="text-[11px] text-slate-500 mt-1">Connect a supported source to enable this section.</p>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="mt-2.5 px-3 py-1 bg-blue-600 text-white font-semibold rounded-lg text-xs hover:bg-blue-700 transition-colors cursor-pointer"
            >
              Retry Connection
            </button>
          )}
        </div>
      ) : news.length === 0 ? (
        <div className="py-4 text-center bg-slate-50 rounded-xl border border-slate-100 text-slate-500 text-xs">
          No relevant recent news articles were found matching this corridor.
        </div>
      ) : (
        <div className="space-y-2.5">
          {news.map((item) => (
            <div
              key={item.id}
              className="p-3 rounded-xl border border-slate-200/80 hover:border-blue-300 hover:bg-slate-50/50 transition-all text-left text-xs space-y-1.5"
            >
              {/* Headline & Relevance Badge */}
              <div className="flex items-start justify-between gap-1.5">
                <a
                  href={item.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-bold text-slate-900 hover:text-blue-600 transition-colors leading-snug line-clamp-2"
                >
                  {item.headline}
                </a>
                <span className={`text-[9px] font-black px-1.5 py-0.5 rounded-full shrink-0 uppercase tracking-wide ${
                  item.relevanceTag === 'High'
                    ? 'bg-red-50 text-red-700 border border-red-200'
                    : 'bg-blue-50 text-blue-700 border border-blue-200'
                }`}>
                  {item.relevanceTag}
                </span>
              </div>

              {/* Publisher & Published Date */}
              <div className="flex items-center gap-2 text-[10px] text-slate-400 font-medium">
                <span className="text-slate-700 font-bold">{item.publisher}</span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3 text-slate-400" />
                  {formatTimestamp(item.publishedTime)}
                </span>
                <span>•</span>
                <span className="text-slate-600">{item.locationMentioned}</span>
              </div>

              {/* Concise Summary */}
              <p className="text-[11px] text-slate-600 leading-snug font-normal line-clamp-2">
                {item.summary}
              </p>

              {/* Source Link & Topic */}
              <div className="flex items-center justify-between pt-1 border-t border-slate-100 text-[10px]">
                <span className="text-slate-400 font-medium flex items-center gap-1">
                  <Tag className="w-3 h-3" />
                  Topic: {item.category}
                </span>
                <a
                  href={item.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 font-bold flex items-center gap-0.5"
                >
                  Read Source Article <ExternalLink className="w-2.5 h-2.5" />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
