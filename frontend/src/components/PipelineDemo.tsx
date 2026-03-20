/**
 * PipelineDemo — animated pipeline log widget for the landing page.
 *
 * Shows a looping mock of a live due-diligence run: agent phases light up
 * as log lines appear one by one, then the whole thing resets and replays.
 * No backend needed — purely frontend animation.
 */

import { useEffect, useRef, useState } from 'react';

// ── Log line data ────────────────────────────────────────────────────────────

type Phase = 'RESEARCH' | 'ANALYSIS' | 'DELIVERY';
type LineType = 'connecting' | 'success' | 'warning' | 'info';

interface LogLine {
  phase: Phase;
  type: LineType;
  message: string;
  delay?: number; // extra ms before this line appears (default 0)
}

const LOG_LINES: LogLine[] = [
  { phase: 'RESEARCH',  type: 'connecting', message: 'Connecting to Salesforce CRM via OAuth 2.0...' },
  { phase: 'RESEARCH',  type: 'success',    message: 'Salesforce: 47 open opportunities, 12 closed deals — 284 records' },
  { phase: 'RESEARCH',  type: 'connecting', message: 'LinkedIn Sales Navigator via TinyFish browser session...' },
  { phase: 'RESEARCH',  type: 'success',    message: 'Sales Navigator: 14 decision makers found (C-suite, VPs, Directors)' },
  { phase: 'RESEARCH',  type: 'connecting', message: 'SEC EDGAR: fetching 10-K annual filing...' },
  { phase: 'RESEARCH',  type: 'success',    message: 'EDGAR: FY2024 10-K extracted — 3 material risk factors noted' },
  { phase: 'RESEARCH',  type: 'connecting', message: 'Crunchbase: funding history & acquisitions...' },
  { phase: 'RESEARCH',  type: 'success',    message: 'Crunchbase: $47M raised across 3 rounds — Series A lead: Accel' },
  { phase: 'RESEARCH',  type: 'connecting', message: 'SAP Fiori: financial statements via TinyFish browser session...' },
  { phase: 'RESEARCH',  type: 'success',    message: 'SAP: FY2024 income statement & balance sheet — 847 GL entries', delay: 800 },

  { phase: 'ANALYSIS',  type: 'connecting', message: 'Cross-referencing Salesforce vs NetSuite revenue data...' },
  { phase: 'ANALYSIS',  type: 'warning',    message: 'Finding: $2.3M revenue variance — CRM vs ERP mismatch  [HIGH]' },
  { phase: 'ANALYSIS',  type: 'connecting', message: 'Checking Sales Navigator leadership vs org chart...' },
  { phase: 'ANALYSIS',  type: 'warning',    message: 'Finding: VP Engineering absent from LinkedIn  [Key Person Risk]' },
  { phase: 'ANALYSIS',  type: 'connecting', message: 'Validating SAP headcount vs ZoomInfo employee data...' },
  { phase: 'ANALYSIS',  type: 'success',    message: 'Headcount verified: 127 employees, 18% YoY growth — no anomaly' },
  { phase: 'ANALYSIS',  type: 'connecting', message: 'Scoring 4 findings by confidence and severity...' },
  { phase: 'ANALYSIS',  type: 'info',       message: 'Analysis complete — 4 findings flagged (2 high, 2 medium)', delay: 400 },

  { phase: 'DELIVERY',  type: 'connecting', message: 'Generating executive PDF summary...' },
  { phase: 'DELIVERY',  type: 'connecting', message: 'Running PII compliance sweep across extracted data...' },
  { phase: 'DELIVERY',  type: 'success',    message: 'PII sweep clean — no sensitive identifiers detected' },
  { phase: 'DELIVERY',  type: 'connecting', message: 'Delivering to Slack #deals and Google Drive...' },
  { phase: 'DELIVERY',  type: 'success',    message: 'Pipeline complete — report delivered in 3h 47m', delay: 600 },
];

const LINE_INTERVAL = 520; // ms between lines
const RESET_PAUSE  = 3200; // ms to show completed state before looping

// ── Helpers ──────────────────────────────────────────────────────────────────

const PHASE_ORDER: Phase[] = ['RESEARCH', 'ANALYSIS', 'DELIVERY'];

const phaseLabel: Record<Phase, string> = {
  RESEARCH: 'Research Agent',
  ANALYSIS: 'Analysis Agent',
  DELIVERY: 'Delivery Agent',
};

function lineColor(type: LineType): string {
  switch (type) {
    case 'success':    return 'text-green-400';
    case 'warning':    return 'text-yellow-400';
    case 'info':       return 'text-cyan-400';
    case 'connecting': return 'text-neutral-400';
  }
}

function linePrefix(type: LineType): string {
  switch (type) {
    case 'success':    return '✓';
    case 'warning':    return '⚠';
    case 'info':       return '●';
    case 'connecting': return '→';
  }
}

function phaseColor(phase: Phase, activePhase: Phase | null, done: boolean): string {
  const phaseIdx   = PHASE_ORDER.indexOf(phase);
  const activeIdx  = activePhase ? PHASE_ORDER.indexOf(activePhase) : -1;
  if (done || phaseIdx < activeIdx) return 'text-green-400 border-green-400/40 bg-green-400/5';
  if (phase === activePhase)        return 'text-orange-400 border-orange-400/50 bg-orange-400/8 animate-pulse';
  return 'text-neutral-600 border-neutral-700 bg-transparent';
}

// ── Component ────────────────────────────────────────────────────────────────

export function PipelineDemo() {
  const [visibleLines, setVisibleLines] = useState<LogLine[]>([]);
  const [activePhase, setActivePhase] = useState<Phase | null>('RESEARCH');
  const [done, setDone]               = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const timerRef  = useRef<ReturnType<typeof setTimeout> | null>(null);

  const reset = () => {
    setVisibleLines([]);
    setActivePhase('RESEARCH');
    setDone(false);
  };

  useEffect(() => {
    let idx = 0;

    const addLine = () => {
      if (idx >= LOG_LINES.length) {
        setDone(true);
        timerRef.current = setTimeout(reset, RESET_PAUSE);
        return;
      }

      const line = LOG_LINES[idx];
      const extra = line.delay ?? 0;

      timerRef.current = setTimeout(() => {
        setVisibleLines(prev => [...prev, line]);
        setActivePhase(line.phase);
        // scroll to bottom
        requestAnimationFrame(() => {
          if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
          }
        });
        idx++;
        addLine();
      }, (idx === 0 ? 400 : LINE_INTERVAL) + extra);
    };

    addLine();
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [done]); // restart effect when `done` resets back to false after reset()

  return (
    <section className="relative py-12 md:py-20 px-4 md:px-6">
      <div className="max-w-5xl mx-auto">

        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div>
            <p className="text-xs font-mono text-orange-600 tracking-widest mb-1">LIVE PIPELINE</p>
            <h3 className="text-xl md:text-2xl font-bold">Watch it run</h3>
            <p className="text-sm text-neutral-500 mt-1">
              A real due-diligence pipeline, animated in real time.
            </p>
          </div>

          {/* Company badge */}
          <div className="flex items-center gap-2 px-3 py-1.5 border border-neutral-700 rounded-full bg-neutral-900/60 w-fit">
            <span className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-pulse flex-shrink-0" />
            <span className="text-[11px] font-mono text-neutral-300">Acme Corp — Series B Due Diligence</span>
          </div>
        </div>

        {/* Agent phase bar */}
        <div className="flex gap-2 mb-3">
          {PHASE_ORDER.map(phase => (
            <div
              key={phase}
              className={`flex-1 px-3 py-2 rounded border text-[10px] font-mono font-semibold transition-all duration-500 text-center ${phaseColor(phase, activePhase, done)}`}
            >
              {phaseLabel[phase]}
              {(done || (activePhase && PHASE_ORDER.indexOf(phase) < PHASE_ORDER.indexOf(activePhase))) && (
                <span className="ml-1 text-green-400">✓</span>
              )}
            </div>
          ))}
        </div>

        {/* Log panel */}
        <div
          className="relative rounded-xl border border-neutral-800 bg-neutral-950/80 backdrop-blur-sm overflow-hidden"
          style={{ boxShadow: '0 0 40px rgba(234,88,12,0.06)' }}
        >
          {/* Panel header bar */}
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-neutral-800 bg-neutral-900/60">
            <div className="flex gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500/50" />
              <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/50" />
              <span className="w-2.5 h-2.5 rounded-full bg-green-500/50" />
            </div>
            <span className="text-[10px] font-mono text-neutral-500">keen · pipeline.log</span>
            <div className="flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full ${done ? 'bg-green-500' : 'bg-orange-500 animate-pulse'}`} />
              <span className="text-[10px] font-mono text-neutral-500">{done ? 'COMPLETE' : 'RUNNING'}</span>
            </div>
          </div>

          {/* Log lines */}
          <div
            ref={scrollRef}
            className="p-4 md:p-5 h-72 overflow-y-auto font-mono text-[11px] md:text-xs space-y-1.5 scrollbar-thin"
            style={{ scrollBehavior: 'smooth' }}
          >
            {visibleLines.map((line, i) => (
              <div
                key={i}
                className="flex items-start gap-2.5 leading-relaxed animate-fadeIn"
              >
                {/* Phase tag */}
                <span
                  className={`flex-shrink-0 text-[9px] font-bold px-1.5 py-0.5 rounded border mt-0.5 ${
                    line.phase === 'RESEARCH'
                      ? 'text-blue-400 border-blue-400/20 bg-blue-400/5'
                      : line.phase === 'ANALYSIS'
                      ? 'text-purple-400 border-purple-400/20 bg-purple-400/5'
                      : 'text-orange-400 border-orange-400/20 bg-orange-400/5'
                  }`}
                >
                  {line.phase.slice(0, 3)}
                </span>

                {/* Prefix icon */}
                <span className={`flex-shrink-0 ${lineColor(line.type)}`}>
                  {linePrefix(line.type)}
                </span>

                {/* Message */}
                <span className={lineColor(line.type)}>{line.message}</span>
              </div>
            ))}

            {/* Blinking cursor at end */}
            {!done && visibleLines.length > 0 && (
              <div className="flex items-center gap-2.5">
                <span className="flex-shrink-0 text-[9px] font-bold px-1.5 py-0.5 rounded border border-transparent opacity-0">RES</span>
                <span className="inline-block w-1.5 h-3.5 bg-orange-500 animate-pulse opacity-70" />
              </div>
            )}

            {/* Completion message */}
            {done && (
              <div className="mt-3 pt-3 border-t border-neutral-800 text-center">
                <span className="text-[10px] font-mono text-green-400">
                  ✓ Pipeline complete · 4 findings · report delivered
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Stat row */}
        <div className="mt-4 grid grid-cols-3 gap-3">
          {[
            { value: '15+',    label: 'data sources' },
            { value: '~4 hrs', label: 'vs 3 weeks manual' },
            { value: '3',      label: 'AI agents' },
          ].map(({ value, label }) => (
            <div
              key={label}
              className="text-center px-3 py-3 border border-neutral-800 rounded-lg bg-neutral-900/40"
            >
              <p className="text-lg md:text-xl font-bold text-orange-400">{value}</p>
              <p className="text-[10px] font-mono text-neutral-500 mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
