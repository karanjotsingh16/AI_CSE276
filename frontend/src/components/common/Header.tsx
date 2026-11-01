import React from 'react';
import { RotateCcw, Sparkles } from 'lucide-react';

interface HeaderProps {
  corridorSummary?: string;
  onResetWizard?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  corridorSummary,
  onResetWizard
}) => {
  return (
    <header className="h-[64px] bg-slate-950/95 backdrop-blur-md border-b border-slate-800/80 text-white px-5 flex items-center justify-between z-30 shrink-0 select-none">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl overflow-hidden flex items-center justify-center shadow-md shadow-blue-500/20 transition-transform hover:scale-105">
          <img src="/favicon.svg" alt="NER SmartRoute" className="w-9 h-9 object-contain" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-extrabold tracking-tight text-white m-0">
              NER SmartRoute
            </h1>
            <span className="hidden sm:inline-flex items-center gap-1 text-[10px] font-semibold bg-blue-500/15 text-blue-300 border border-blue-400/25 px-2 py-0.5 rounded-full">
              <Sparkles className="w-2.5 h-2.5 text-blue-400" /> SIH 26002
            </span>
          </div>
          <p className="text-[11px] text-slate-400 m-0 leading-tight">
            {corridorSummary || 'AI Logistics & Accessibility Intelligence · Meghalaya Pilot'}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2.5">
        {onResetWizard && (
          <button
            type="button"
            onClick={onResetWizard}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-blue-600/20 hover:bg-blue-600/30 border border-blue-400/40 text-blue-200 hover:text-white text-xs font-bold transition-all hover:scale-105 active:scale-95 cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>New Journey</span>
          </button>
        )}

        <div className="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-700/80 text-slate-300 text-[11px] font-semibold">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
          </span>
          <span>OSMnx Engine Ready</span>
        </div>
      </div>
    </header>
  );
};
