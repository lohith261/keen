import { useEffect, useRef, useState } from 'react';
import {
  Search, BarChart3, FileText, CheckCircle2, Clock, XCircle,
  AlertTriangle, Info, Loader2, PauseCircle, Terminal, KeyRound,
} from 'lucide-react';
import { connectAgentStatus, engagementsApi, type Engagement } from '../../lib/apiClient';
import CredentialsModal from './CredentialsModal';

interface AgentState {
  status: string;
  progress_pct: number;
  current_step_name: string;
  activity: string;          // human-readable current activity
  step_log: LogEntry[];
}

interface LogEntry {
  id: string;
  type: 'init' | 'step_start' | 'step_done' | 'finding' | 'agent_start' | 'agent_done' | 'error';
  message: string;
  timestamp: string;
  agent?: string;
}

interface Finding {
  id: string;
  title: string;
  severity: 'info' | 'warning' | 'critical';
  source_system: string;
  timestamp: string;
}

interface Props {
  engagement: Engagement;
  onEngagementUpdate: (e: Engagement) => void;
}

const AGENT_META = [
  { type: 'research', label: 'Research Agent', Icon: Search, color: 'blue',
    description: 'Extracting data from CRM, ERP, market and document sources' },
  { type: 'analysis', label: 'Analysis Agent', Icon: BarChart3, color: 'purple',
    description: 'Cross-referencing sources & scoring findings' },
  { type: 'delivery', label: 'Delivery Agent', Icon: FileText, color: 'green',
    description: 'Generating board-ready due diligence report' },
];

const SEVERITY_CONFIG = {
  info:     { Icon: Info,          color: 'text-blue-400',  bg: 'bg-blue-500/10 border-blue-500/20' },
  warning:  { Icon: AlertTriangle, color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20' },
  critical: { Icon: XCircle,       color: 'text-red-400',   bg: 'bg-red-500/10 border-red-500/20' },
};

const STATUS_ICONS: Record<string, JSX.Element> = {
  running:   <Loader2    className="w-3.5 h-3.5 animate-spin text-blue-400" />,
  completed: <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />,
  failed:    <XCircle    className="w-3.5 h-3.5 text-red-400" />,
  paused:    <PauseCircle className="w-3.5 h-3.5 text-amber-400" />,
  queued:    <Clock      className="w-3.5 h-3.5 text-theme-text-muted" />,
};

const AGENT_COLORS: Record<string, { bar: string; ring: string; text: string }> = {
  blue:   { bar: 'bg-blue-500',   ring: 'border-blue-500/40',   text: 'text-blue-400' },
  purple: { bar: 'bg-purple-500', ring: 'border-purple-500/40', text: 'text-purple-400' },
  green:  { bar: 'bg-green-500',  ring: 'border-green-500/40',  text: 'text-green-400' },
};

/** Map raw snake_case step names to human-readable activity strings */
function stepToActivity(step: string, agent: string): string {
  if (!step) return '';
  const s = step.toLowerCase();

  // Research steps
  if (s === 'plan_extraction') return 'Planning extraction strategy with LLM...';
  if (s.startsWith('authenticate_')) {
    const src = s.replace('authenticate_', '').replace(/_/g, ' ');
    return `Authenticating to ${src}...`;
  }
  if (s.startsWith('extract_')) {
    const src = s.replace('extract_', '').replace(/_/g, ' ');
    return `Extracting data from ${src}...`;
  }
  if (s === 'validate_extractions') return 'Validating extracted data across all sources...';
  if (s === 'compile_results') return 'Compiling research output...';

  // Analysis steps
  if (s === 'load_research_data') return 'Loading research data into analysis engine...';
  if (s === 'cross_reference_sources') return 'Cross-referencing data across all sources with LLM...';
  if (s === 'detect_variances') return 'Detecting revenue, cost, and headcount variances...';
  if (s === 'score_findings') return 'Scoring findings by severity and confidence...';
  if (s === 'route_exceptions') return 'Routing critical findings for human review...';
  if (s === 'compile_analysis') return 'Compiling analysis report...';

  // Delivery steps
  if (s === 'load_analysis') return 'Loading analysis findings...';
  if (s === 'generate_executive_summary') return 'Generating executive summary with LLM...';
  if (s === 'generate_detailed_report') return 'Generating full 9-section due diligence report...';
  if (s === 'format_output') return 'Formatting board-ready output...';
  if (s === 'distribute') return 'Distributing report via configured channels...';
  if (s === 'create_audit_trail') return 'Creating compliance audit trail...';

  // Fallback
  return step.replace(/_/g, ' ');
}

/** Startup log entries shown immediately when pipeline begins */
const STARTUP_LOG: LogEntry[] = [
  { id: 'init-0', type: 'init', message: 'Initialising KEEN pipeline...', timestamp: '' },
  { id: 'init-1', type: 'init', message: 'Connecting to backend orchestrator', timestamp: '' },
  { id: 'init-2', type: 'init', message: 'Loading engagement configuration', timestamp: '' },
  { id: 'init-3', type: 'init', message: 'Preparing Research → Analysis → Delivery chain', timestamp: '' },
  { id: 'init-4', type: 'init', message: 'WebSocket live feed connected', timestamp: '' },
];

function now(): string {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function logColor(type: LogEntry['type']): string {
  switch (type) {
    case 'init':        return 'text-theme-text-muted';
    case 'agent_start': return 'text-blue-400';
    case 'agent_done':  return 'text-green-400';
    case 'step_start':  return 'text-theme-text-muted';
    case 'step_done':   return 'text-green-400';
    case 'finding':     return 'text-amber-400';
    case 'error':       return 'text-red-400';
    default:            return 'text-theme-text-muted';
  }
}

function logPrefix(type: LogEntry['type']): string {
  switch (type) {
    case 'init':        return '›';
    case 'agent_start': return '▶';
    case 'agent_done':  return '✓';
    case 'step_start':  return '  ·';
    case 'step_done':   return '  ✓';
    case 'finding':     return '  ⚑';
    case 'error':       return '  ✗';
    default:            return '›';
  }
}

export default function PipelineView({ engagement, onEngagementUpdate }: Props) {
  const [agents, setAgents] = useState<Record<string, AgentState>>({
    research: { status: 'queued', progress_pct: 0, current_step_name: '', activity: '', step_log: [] },
    analysis: { status: 'queued', progress_pct: 0, current_step_name: '', activity: '', step_log: [] },
    delivery: { status: 'queued', progress_pct: 0, current_step_name: '', activity: '', step_log: [] },
  });
  const [globalLog, setGlobalLog] = useState<LogEntry[]>(() =>
    STARTUP_LOG.map((e) => ({ ...e, timestamp: now() }))
  );
  const [findings, setFindings] = useState<Finding[]>([]);
  const [overallStatus, setOverallStatus] = useState(engagement.status);
  const [wsOnline, setWsOnline] = useState(true);
  const wsRef = useRef<WebSocket | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);
  const findingsEndRef = useRef<HTMLDivElement>(null);

  const appendLog = (entry: Omit<LogEntry, 'id' | 'timestamp'>) => {
    setGlobalLog((prev) => [
      ...prev,
      { ...entry, id: `${Date.now()}-${Math.random()}`, timestamp: now() },
    ]);
  };

  // Seed initial state from engagement.agent_runs
  useEffect(() => {
    if (engagement.agent_runs?.length) {
      setAgents((prev) => {
        const next = { ...prev };
        for (const run of engagement.agent_runs!) {
          if (next[run.agent_type]) {
            next[run.agent_type] = {
              ...next[run.agent_type],
              status: run.status,
              progress_pct: run.progress_pct ?? 0,
            };
          }
        }
        return next;
      });
    }
    setOverallStatus(engagement.status);
  }, [engagement.id]);

  // WebSocket connection
  useEffect(() => {
    const ws = connectAgentStatus(engagement.id, (msg) => {
      const { event, data } = msg as { event: string; data: Record<string, unknown> };

      if (event === 'progress') {
        const agentType = data.agent_type as string;
        const stepName  = (data.step_name as string) ?? '';
        const pct       = (data.progress_pct as number) ?? 0;
        const stage     = data.stage as string;
        const activity  = stepToActivity(stepName, agentType);

        setAgents((prev) => {
          if (!prev[agentType]) return prev;
          const prevAgent = prev[agentType];
          return {
            ...prev,
            [agentType]: {
              ...prevAgent,
              progress_pct: pct,
              current_step_name: stepName,
              activity: stage === 'executing' ? activity : prevAgent.activity,
            },
          };
        });

        if (stage === 'executing' && stepName) {
          appendLog({ type: 'step_start', message: stepToActivity(stepName, agentType), agent: agentType });
        }
        if (stage === 'completed' && stepName) {
          appendLog({ type: 'step_done', message: stepToActivity(stepName, agentType).replace(/\.\.\.$/, ' — done'), agent: agentType });
        }
      }

      if (event === 'agent_status') {
        const agentType = data.agent_type as string;
        const status    = data.status as string;
        const pct       = (data.progress_pct as number) ?? undefined;
        const meta      = AGENT_META.find((m) => m.type === agentType);

        setAgents((prev) => {
          if (!prev[agentType]) return prev;
          return {
            ...prev,
            [agentType]: {
              ...prev[agentType],
              status,
              activity: status === 'completed' ? 'All steps complete' :
                        status === 'failed'    ? 'Agent encountered an error' :
                        prev[agentType].activity,
              ...(pct !== undefined ? { progress_pct: pct } : {}),
            },
          };
        });

        if (status === 'running' && meta) {
          appendLog({ type: 'agent_start', message: `${meta.label} started`, agent: agentType });
        }
        if (status === 'completed' && meta) {
          appendLog({ type: 'agent_done', message: `${meta.label} completed`, agent: agentType });
        }
        if (status === 'failed' && meta) {
          appendLog({ type: 'error', message: `${meta.label} failed`, agent: agentType });
        }
      }

      if (event === 'finding') {
        const title  = (data.title as string) ?? 'Finding';
        const source = (data.source_system as string) ?? '';
        setFindings((prev) => [
          {
            id: (data.finding_id as string) ?? String(Date.now()),
            title,
            severity: (data.severity as Finding['severity']) ?? 'info',
            source_system: source,
            timestamp: now(),
          },
          ...prev,
        ]);
        appendLog({ type: 'finding', message: `Finding: ${title}${source ? ` [${source}]` : ''}` });
      }

      if (event === 'orchestrator') {
        const status = data.status as string;
        if (status === 'started') {
          appendLog({ type: 'agent_start', message: 'Orchestrator pipeline started' });
        }
        if (['completed', 'failed', 'paused'].includes(status)) {
          appendLog({
            type: status === 'completed' ? 'agent_done' : status === 'failed' ? 'error' : 'init',
            message: `Pipeline ${status}`,
          });
          setOverallStatus(status);
          onEngagementUpdate({ ...engagement, status });
          engagementsApi.get(engagement.id).then(onEngagementUpdate).catch(() => {});
        }
      }
    });

    ws.onopen  = () => setWsOnline(true);
    ws.onclose = () => setWsOnline(false);
    ws.onerror = () => setWsOnline(false);

    wsRef.current = ws;
    return () => ws.close();
  }, [engagement.id]);

  // Auto-scroll log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [globalLog]);

  const handlePause = async () => { try { await engagementsApi.pause(engagement.id); } catch {} };
  const handleResume = async () => {
    try { await engagementsApi.resume(engagement.id); setOverallStatus('running'); } catch {}
  };

  const [showCredentials, setShowCredentials] = useState(false);

  const isActive = overallStatus === 'running';
  const isDone   = overallStatus === 'completed';
  const isFailed = overallStatus === 'failed';
  const isPaused = overallStatus === 'paused';

  return (
    <div className="space-y-4">
      {showCredentials && (
        <CredentialsModal
          engagementId={engagement.id}
          onClose={() => setShowCredentials(false)}
        />
      )}

      {/* WebSocket offline banner */}
      {!wsOnline && isActive && (
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-amber-500/30
                        bg-amber-500/8 text-amber-400 text-[11px] font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse flex-shrink-0" />
          Live feed disconnected — reconnecting…
          <span className="ml-auto text-amber-400/60">pipeline continues server-side</span>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold">{engagement.company_name}</h2>
          <p className="text-[11px] font-mono text-theme-text-muted mt-0.5">
            {String(engagement.config?.engagement_type ?? 'full_diligence').replace(/_/g, ' ').toUpperCase()}
            {' · '}
            {isDone   && <span className="text-green-400">COMPLETED</span>}
            {isFailed && <span className="text-red-400">FAILED</span>}
            {isActive && <span className="text-blue-400">RUNNING</span>}
            {isPaused && <span className="text-amber-400">PAUSED</span>}
            {!isDone && !isFailed && !isActive && !isPaused && <span>DRAFT</span>}
          </p>
        </div>
        <div className="flex gap-2">
          {/* Configure Credentials — always visible so users can set up before starting */}
          <button
            onClick={() => setShowCredentials(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-mono
                       border border-white/15 text-white/50 rounded-lg
                       hover:bg-white/5 hover:text-white/80 transition-colors"
          >
            <KeyRound className="w-3 h-3" />
            CREDENTIALS
          </button>

          {isActive && (
            <button onClick={handlePause}
              className="px-3 py-1.5 text-[10px] font-mono border border-amber-500/40 text-amber-400
                         rounded-lg hover:bg-amber-500/10 transition-colors">
              PAUSE
            </button>
          )}
          {isPaused && (
            <button onClick={handleResume}
              className="px-3 py-1.5 text-[10px] font-mono border border-green-500/40 text-green-400
                         rounded-lg hover:bg-green-500/10 transition-colors">
              RESUME
            </button>
          )}
        </div>
      </div>

      {/* Agent cards */}
      <div className="grid grid-cols-3 gap-3">
        {AGENT_META.map(({ type, label, Icon, color, description }) => {
          const agent = agents[type];
          const pct   = Math.round(agent.progress_pct);
          const clr   = AGENT_COLORS[color];
          const isRunning = agent.status === 'running';

          return (
            <div
              key={type}
              className={`border rounded-xl p-4 space-y-3 bg-theme-bg/50 transition-colors ${
                isRunning ? clr.ring : 'border-theme-border'
              }`}
            >
              {/* Header row */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon className={`w-4 h-4 ${isRunning ? clr.text : 'text-theme-text-muted'}`} />
                  <span className="text-xs font-semibold tracking-wide">{label.toUpperCase()}</span>
                </div>
                {STATUS_ICONS[agent.status] ?? <Clock className="w-3.5 h-3.5 text-theme-text-muted" />}
              </div>

              {/* Progress bar */}
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className={`text-[10px] font-mono capitalize ${isRunning ? clr.text : 'text-theme-text-muted'}`}>
                    {agent.status}
                  </span>
                  <span className="text-[10px] font-mono text-theme-text-muted">{pct}%</span>
                </div>
                <div className="h-1.5 bg-theme-border rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${
                      pct > 0 ? clr.bar : 'bg-theme-border'
                    }`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>

              {/* Activity line — what's happening NOW */}
              <div className="min-h-[2.5rem]">
                {isRunning && agent.activity ? (
                  <p className="text-[10px] font-mono text-theme-text leading-relaxed">
                    <span className={`${clr.text} mr-1`}>›</span>
                    {agent.activity}
                  </p>
                ) : agent.status === 'queued' ? (
                  <p className="text-[10px] font-mono text-theme-text-muted/50">{description}</p>
                ) : agent.status === 'completed' ? (
                  <p className="text-[10px] font-mono text-green-400">All steps complete</p>
                ) : agent.status === 'failed' ? (
                  <p className="text-[10px] font-mono text-red-400">Agent failed</p>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>

      {/* Lower panel: pipeline log + findings */}
      <div className="grid grid-cols-2 gap-3">
        {/* Pipeline log — terminal style */}
        <div className="border border-theme-border rounded-xl overflow-hidden">
          <div className="px-4 py-2.5 border-b border-theme-border bg-theme-bg/60 flex items-center gap-2">
            <Terminal className="w-3.5 h-3.5 text-theme-text-muted" />
            <span className="text-[10px] font-mono font-semibold text-theme-text-muted tracking-widest">
              PIPELINE LOG
            </span>
            {isActive && (
              <span className="ml-auto flex items-center gap-1 text-[9px] font-mono text-blue-400">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                LIVE
              </span>
            )}
          </div>
          <div className="h-72 overflow-y-auto p-3 space-y-0.5 font-mono text-[11px] bg-black/20">
            {globalLog.map((entry) => (
              <div key={entry.id} className={`flex items-start gap-2 ${logColor(entry.type)}`}>
                <span className="flex-shrink-0 w-16 text-theme-text-muted/40 text-[10px]">
                  {entry.timestamp}
                </span>
                <span className="flex-shrink-0">{logPrefix(entry.type)}</span>
                <span className="leading-relaxed">{entry.message}</span>
              </div>
            ))}
            {isActive && (
              <div className="flex items-center gap-2 text-blue-400 mt-1">
                <span className="w-16 text-theme-text-muted/40 text-[10px]">{now()}</span>
                <Loader2 className="w-3 h-3 animate-spin flex-shrink-0" />
                <span className="animate-pulse">
                  {Object.values(agents).find((a) => a.status === 'running')?.activity ?? 'Processing...'}
                </span>
              </div>
            )}
            <div ref={logEndRef} />
          </div>
        </div>

        {/* Live findings */}
        <div className="border border-theme-border rounded-xl overflow-hidden">
          <div className="px-4 py-2.5 border-b border-theme-border bg-theme-bg/60 flex items-center justify-between">
            <span className="text-[10px] font-mono font-semibold text-theme-text-muted tracking-widest">
              LIVE FINDINGS
            </span>
            {findings.length > 0 && (
              <span className="text-[10px] font-mono text-theme-text-muted">{findings.length} found</span>
            )}
          </div>
          <div className="h-72 overflow-y-auto p-3 space-y-2">
            {findings.length === 0 && (
              <p className="text-[11px] font-mono text-theme-text-muted/50 py-4 text-center">
                Findings will appear here as the pipeline runs...
              </p>
            )}
            {findings.map((f) => {
              const cfg = SEVERITY_CONFIG[f.severity] ?? SEVERITY_CONFIG.info;
              return (
                <div
                  key={f.id}
                  className={`flex gap-2.5 items-start p-2.5 rounded-lg border text-[11px] ${cfg.bg}`}
                >
                  <cfg.Icon className={`w-3.5 h-3.5 flex-shrink-0 mt-0.5 ${cfg.color}`} />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{f.title}</p>
                    <p className="font-mono text-theme-text-muted mt-0.5 truncate">
                      {f.source_system && `${f.source_system} · `}{f.timestamp}
                    </p>
                  </div>
                </div>
              );
            })}
            <div ref={findingsEndRef} />
          </div>
        </div>
      </div>
    </div>
  );
}
