import { FlaskConical, Radio } from 'lucide-react';
import { useDemoMode } from '../context/DemoModeContext';

export default function DemoModeToggle() {
  const { mode, toggleMode } = useDemoMode();
  const isDemo = mode === 'demo';

  return (
    <button
      onClick={toggleMode}
      aria-label={`Switch to ${isDemo ? 'live' : 'demo'} data mode`}
      title={isDemo ? 'Running on demo data — click to switch to live' : 'Running on live data — click to switch to demo'}
      className={`
        flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[10px] font-mono font-semibold
        backdrop-blur-sm transition-all duration-300 tracking-wider
        ${isDemo
          ? 'border-amber-500/40 bg-amber-500/10 text-amber-400 hover:border-amber-500/70 hover:bg-amber-500/20'
          : 'border-green-500/40 bg-green-500/10 text-green-400 hover:border-green-500/70 hover:bg-green-500/20'
        }
      `}
    >
      {isDemo ? (
        <FlaskConical className="w-3 h-3 flex-shrink-0" />
      ) : (
        <Radio className="w-3 h-3 flex-shrink-0 animate-pulse" />
      )}
      <span>{isDemo ? 'DEMO' : 'LIVE'}</span>
    </button>
  );
}
