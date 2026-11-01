import React from 'react';
import { Play, Pause, Eye, EyeOff, Radio, SkipBack, SkipForward, AlertCircle } from 'lucide-react';
import { RadarState } from '../../types/radar';
import { formatTimestamp } from '../../logic/formatters';

interface RadarControlProps {
  radar: RadarState;
  onToggleActive: () => void;
  onTogglePlay: () => void;
  onStepFrame: (direction: 'next' | 'prev') => void;
  onRetry: () => void;
}

export const RadarControl: React.FC<RadarControlProps> = ({
  radar,
  onToggleActive,
  onTogglePlay,
  onStepFrame,
  onRetry
}) => {
  const currentFrame = radar.frames[radar.currentFrameIndex];
  const frameTimeStr = currentFrame ? formatTimestamp(new Date(currentFrame.time * 1000).toISOString()) : 'Syncing...';
  const totalFrames = radar.frames.length;

  return (
    <div className="absolute bottom-5 left-5 z-[1000] glass-panel rounded-2xl border border-slate-200/90 shadow-xl text-slate-800 text-xs w-72 overflow-hidden select-none">
      {/* Top Bar with Radar Pulse */}
      <div className="px-3.5 py-2.5 bg-slate-900 text-white flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="relative w-4 h-4 flex items-center justify-center">
            {radar.isActive && radar.isPlaying ? (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
            ) : null}
            <Radio className={`w-3.5 h-3.5 ${radar.isActive ? 'text-sky-400' : 'text-slate-500'}`} />
          </div>
          <div>
            <h3 className="font-extrabold text-[11px] tracking-wide leading-none text-white">LIVE PRECIPITATION RADAR</h3>
            <span className="text-[9px] text-slate-400 font-medium">Observed RainViewer Stream</span>
          </div>
        </div>

        <button
          onClick={onToggleActive}
          className={`px-2 py-0.5 rounded-full text-[10px] font-black tracking-wider uppercase transition-all cursor-pointer ${
            radar.isActive
              ? 'bg-sky-500 text-white shadow-xs'
              : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
          }`}
        >
          {radar.isActive ? 'ON' : 'OFF'}
        </button>
      </div>

      <div className="p-3 space-y-2">
        {radar.error ? (
          <div className="p-2 bg-red-50 rounded-xl border border-red-200 text-red-700 text-[10px] flex items-center justify-between">
            <span className="truncate">{radar.error}</span>
            <button onClick={onRetry} className="text-red-900 font-bold underline cursor-pointer">Retry</button>
          </div>
        ) : (
          <>
            {/* Timestamp & Frame indicator */}
            <div className="flex items-center justify-between text-[11px] bg-slate-50 px-2.5 py-1.5 rounded-xl border border-slate-100">
              <span className="font-semibold text-slate-700 text-[10px] truncate">{frameTimeStr}</span>
              <span className="font-mono text-[9px] font-bold text-slate-400">
                {totalFrames > 0 ? `${radar.currentFrameIndex + 1}/${totalFrames}` : '0/0'}
              </span>
            </div>

            {/* Playback Controls */}
            <div className="flex items-center gap-1.5 pt-0.5">
              <button
                onClick={() => onStepFrame('prev')}
                disabled={!radar.isActive || totalFrames <= 1}
                className="p-2 rounded-xl border border-slate-200 hover:bg-slate-100 disabled:opacity-40 text-slate-700 transition-colors cursor-pointer"
                title="Previous Frame"
              >
                <SkipBack className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={onTogglePlay}
                disabled={!radar.isActive || totalFrames <= 1}
                className={`flex-1 py-1.5 px-3 rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 transition-all cursor-pointer shadow-sm ${
                  radar.isPlaying
                    ? 'bg-amber-500 hover:bg-amber-600 text-white shadow-amber-500/20'
                    : 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-500/20'
                } disabled:opacity-40`}
              >
                {radar.isPlaying ? (
                  <>
                    <Pause className="w-3.5 h-3.5" />
                    <span>Pause</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>Play Radar Loop</span>
                  </>
                )}
              </button>

              <button
                onClick={() => onStepFrame('next')}
                disabled={!radar.isActive || totalFrames <= 1}
                className="p-2 rounded-xl border border-slate-200 hover:bg-slate-100 disabled:opacity-40 text-slate-700 transition-colors cursor-pointer"
                title="Next Frame"
              >
                <SkipForward className="w-3.5 h-3.5" />
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
