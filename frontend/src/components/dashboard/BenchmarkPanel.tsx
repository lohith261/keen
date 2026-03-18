import { useState } from 'react';
import {
  AlertTriangle, BarChart2, CheckCircle2, Info, Loader2,
  TrendingDown, TrendingUp, XCircle,
} from 'lucide-react';

/**
 * Deal Benchmarking Panel
 *
 * Displays comparable transaction data and benchmarks the target company's
 * metrics (ARR growth, NRR, gross margin, EV/Rev multiple) against deal comps
 * sourced from PitchBook (via TinyFish) and Crunchbase.
 *
 * The panel receives benchmark data from the Analysis Agent's
 * benchmark_metrics finding (finding_type === 'benchmark_comparison').
 * If no benchmark finding exists yet, it shows a placeholder state.
 */

interface BenchmarkStats {
  median: number | null;
  mean: number | null;
  p25: number | null;
  p75: number | null;
  sample: number;
}

interface Comp {
  target: string;
  acquirer: string | null;
  deal_date: string | null;
  deal_value_m: number | null;
  ev_revenue: number | null;
  growth_pct: number | null;
}

interface BenchmarkData {
  sample_size: number;
  sector: string;
  ev_revenue: BenchmarkStats;
  ev_arr: BenchmarkStats;
  revenue_growth_pct: BenchmarkStats;
  gross_margin_pct: BenchmarkStats;
  nrr_pct: BenchmarkStats;
  comps: Comp[];
}

interface Comparison {
  metric: string;
  key: string;
  target_value: number;
  benchmark_median: number;
  benchmark_p25: number | null;
  benchmark_p75: number | null;
  delta_vs_median: number;
  flag: 'below_p25' | 'in_range' | 'above_p75';
}

interface Props {
  /** benchmark_data field from the benchmark_comparison finding, if present */
  benchmarkData?: BenchmarkData | null;
  /** comparisons array from the finding */
  comparisons?: Comparison[];
  companyName: string;
}

function fmt(val: number | null | undefined, decimals = 1, suffix = '') {
  if (val == null) return '—';
  return `${val.toFixed(decimals)}${suffix}`;
}

function StatBox({
  label,
  stats,
  unit = 'x',
}: {
  label: string;
  stats: BenchmarkStats | undefined;
  unit?: string;
}) {
  if (!stats || stats.median == null) {
    return (
      <div className="border border-theme-border rounded-xl p-4 space-y-2">
        <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider">{label}</p>
        <p className="text-xl font-bold text-theme-text-muted">—</p>
      </div>
    );
  }

  return (
    <div className="border border-theme-border rounded-xl p-4 space-y-2">
      <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider">{label}</p>
      <p className="text-xl font-bold">{fmt(stats.median)}{unit}</p>
      <div className="flex items-center gap-3 text-[10px] font-mono text-theme-text-muted">
        <span>P25 {fmt(stats.p25)}{unit}</span>
        <span>P75 {fmt(stats.p75)}{unit}</span>
        {stats.sample && <span className="ml-auto">n={stats.sample}</span>}
      </div>
    </div>
  );
}

function ComparisonRow({ c }: { c: Comparison }) {
  const isBelowP25 = c.flag === 'below_p25';
  const isAboveP75 = c.flag === 'above_p75';
  const isInRange = c.flag === 'in_range';

  const flagCfg = isBelowP25
    ? { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30', Icon: XCircle, label: 'BELOW P25' }
    : isAboveP75
    ? { color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/30', Icon: CheckCircle2, label: 'ABOVE P75' }
    : { color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/30', Icon: Info, label: 'IN RANGE' };

  return (
    <div className={`flex items-center gap-3 px-3 py-2.5 rounded-xl border ${flagCfg.border} ${flagCfg.bg}`}>
      <flagCfg.Icon className={`w-3.5 h-3.5 flex-shrink-0 ${flagCfg.color}`} />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold">{c.metric}</p>
        <p className="text-[10px] font-mono text-theme-text-muted mt-0.5">
          Target: <span className={flagCfg.color}>{fmt(c.target_value, 1)}</span>
          {' · '}Median: {fmt(c.benchmark_median, 1)}
          {c.benchmark_p25 != null && ` · P25: ${fmt(c.benchmark_p25, 1)}`}
          {c.benchmark_p75 != null && ` · P75: ${fmt(c.benchmark_p75, 1)}`}
        </p>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <span className={`text-[10px] font-mono font-semibold flex items-center gap-0.5 ${c.delta_vs_median >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          {c.delta_vs_median >= 0
            ? <TrendingUp className="w-3 h-3" />
            : <TrendingDown className="w-3 h-3" />
          }
          {c.delta_vs_median >= 0 ? '+' : ''}{fmt(c.delta_vs_median, 1)} vs median
        </span>
        <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${flagCfg.bg} ${flagCfg.border} ${flagCfg.color}`}>
          {flagCfg.label}
        </span>
      </div>
    </div>
  );
}

function CompsTable({ comps }: { comps: Comp[] }) {
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? comps : comps.slice(0, 5);

  return (
    <div className="space-y-2">
      <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider">
        Comparable Transactions ({comps.length})
      </p>
      <div className="border border-theme-border rounded-xl overflow-hidden">
        <table className="w-full text-[10px] font-mono">
          <thead>
            <tr className="border-b border-theme-border bg-theme-bg/60">
              <th className="text-left px-3 py-2 text-theme-text-muted">TARGET</th>
              <th className="text-left px-3 py-2 text-theme-text-muted hidden sm:table-cell">ACQUIRER</th>
              <th className="text-right px-3 py-2 text-theme-text-muted">VALUE ($M)</th>
              <th className="text-right px-3 py-2 text-theme-text-muted">EV/REV</th>
              <th className="text-right px-3 py-2 text-theme-text-muted hidden md:table-cell">GROWTH</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((comp, i) => (
              <tr key={i} className="border-b border-theme-border/50 last:border-0 hover:bg-theme-border/10 transition-colors">
                <td className="px-3 py-2 text-theme-text font-semibold truncate max-w-32">{comp.target ?? '—'}</td>
                <td className="px-3 py-2 text-theme-text-muted truncate max-w-28 hidden sm:table-cell">{comp.acquirer ?? '—'}</td>
                <td className="px-3 py-2 text-right text-theme-text">{comp.deal_value_m != null ? `$${comp.deal_value_m.toFixed(0)}M` : '—'}</td>
                <td className="px-3 py-2 text-right text-theme-text">{comp.ev_revenue != null ? `${comp.ev_revenue.toFixed(1)}x` : '—'}</td>
                <td className="px-3 py-2 text-right hidden md:table-cell">
                  {comp.growth_pct != null ? (
                    <span className={comp.growth_pct >= 0 ? 'text-green-400' : 'text-red-400'}>
                      {comp.growth_pct >= 0 ? '+' : ''}{comp.growth_pct.toFixed(0)}%
                    </span>
                  ) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {comps.length > 5 && (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="w-full py-2 text-[10px] font-mono text-theme-text-muted hover:text-theme-text
                       border-t border-theme-border hover:bg-theme-border/10 transition-colors"
          >
            {expanded ? `Show less` : `Show all ${comps.length} comps`}
          </button>
        )}
      </div>
    </div>
  );
}

export default function BenchmarkPanel({ benchmarkData, comparisons = [], companyName }: Props) {
  if (!benchmarkData) {
    return (
      <div className="space-y-4">
        <div>
          <h3 className="text-sm font-semibold">Deal Benchmarking</h3>
          <p className="text-[11px] font-mono text-theme-text-muted mt-0.5">
            Comparable transaction data and metric benchmarks from PitchBook and Crunchbase
          </p>
        </div>
        <div className="border border-dashed border-theme-border rounded-xl p-10 text-center space-y-3">
          <BarChart2 className="w-7 h-7 text-theme-text-muted mx-auto" />
          <div>
            <p className="text-sm font-semibold">Benchmark data not yet available</p>
            <p className="text-xs text-theme-text-muted font-mono mt-1">
              Benchmark comparables are generated during the Analysis Agent run when PitchBook credentials are configured
            </p>
          </div>
          <div className="border border-theme-border rounded-lg px-4 py-3 text-left max-w-sm mx-auto">
            <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider mb-1.5">To enable benchmarking</p>
            <ol className="space-y-1 text-[11px] text-theme-text-muted list-decimal list-inside">
              <li>Add PitchBook credentials in the Credentials panel</li>
              <li>Re-run or resume the pipeline</li>
              <li>Benchmark findings will appear here after the Analysis Agent completes</li>
            </ol>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold">Deal Benchmarking — {companyName}</h3>
          <p className="text-[11px] font-mono text-theme-text-muted mt-0.5">
            {benchmarkData.sector} · {benchmarkData.sample_size} comparable transactions · PitchBook + Crunchbase
          </p>
        </div>
      </div>

      {/* Metric benchmarks grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatBox label="EV / Revenue" stats={benchmarkData.ev_revenue} unit="x" />
        <StatBox label="EV / ARR" stats={benchmarkData.ev_arr} unit="x" />
        <StatBox label="Revenue Growth" stats={benchmarkData.revenue_growth_pct} unit="%" />
        <StatBox label="NRR" stats={benchmarkData.nrr_pct} unit="%" />
      </div>

      {/* Target comparison */}
      {comparisons.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] font-mono text-theme-text-muted uppercase tracking-wider">
            {companyName} vs Comps
          </p>
          <div className="space-y-2">
            {comparisons.map((c, i) => (
              <ComparisonRow key={i} c={c} />
            ))}
          </div>
        </div>
      )}

      {/* Comps table */}
      {benchmarkData.comps.length > 0 && (
        <CompsTable comps={benchmarkData.comps} />
      )}

      <div className="border border-dashed border-theme-border rounded-xl px-4 py-3">
        <p className="text-[10px] font-mono text-theme-text-muted/60 text-center">
          Source: PitchBook (via TinyFish browser automation) · Crunchbase · Data as of deal analysis date
        </p>
      </div>
    </div>
  );
}
