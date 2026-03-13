import { useEffect, useRef, useState } from 'react';
import {
  Search, BarChart3, FileText, CheckCircle2, Clock, XCircle,
  AlertTriangle, Info, Loader2, PauseCircle, ChevronRight,
} from 'lucide-react';
import { connectAgentStatus, engagementsApi, type Engagement } from '../../lib/apiClient';

interface AgentState {
  status: string;
  progress_pct: number;
  current_step_name: string;
  step_log: string[];
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
  { type: 'research', label: 'Research', Icon: Search, color: 'blue' },
  { type: 'analysis', label: 'Analysis', Icon: BarChart3, color: 'purple' },
  { type: 'delivery', label: 'Delivery', Icon: FileText, color: 'green' },
];

const SEVERITY_CONFIG = {
  info: { Icon: Info, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' },
  warning: { Icon: AlertTriangle, color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20' },
  critical: { Icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20' },
};

const STATUS_ICONS: Record<string, JSX.Element> = {
  running: <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />,
  completed: <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />,
  failed: <XCircle className="w-3.5 h-3.5 text-red-400" />,
  paused: <PauseCircle className="w-3.5 h-3.5 text-amber-400" />,
  queued: <Clock className="w-3.5 h-3.5 text-theme-text-muted" />,
};

function agentColor(color: string, progress: number) {
  if (progress === 0) return 'bg-theme-border';
  const map: Record<string, string> = {
    blue: 'bg-blue-500',
    purple: 'bg-purple-500',
    green: 'bg-green-500',
  };
  return map[color] ?? 'bg-theme-text';
}

export default function PipelineView({ engagement, onEngagementUpdate }: Props) {
  const [agents, setAgents] = useState<Record<string, AgentState>>({
    research: { status: 'queued', progress_pct: 0, current_step_name: '', step_log: [] },
    analysis: { status: 'queued', progress_pct: 0, current_step_name: '', step_log: [] },
    delivery: { status: 'queued', progress_pct: 0, current_step_name: '', step_log: [] },
  });
  const [findings, setFindings] = useState<Finding[]>([]);
  const [overallStatus, setOverallStatus] = useState(engagement.status);
  const wsRef = useRef<WebSocket | null>(null);
  const findingsEndRef = useRef<HTMLDivElement>(null);
  const stepLogEndRef = useRef<HTMLDivElement>(null);

  // Seed initial state from engagement.agent_runs if present
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
        const stepName = (data.step_name as string) ?? '';
        const pct = (data.progress_pct as number) ?? 0;
        const stage = data.stage as string;

        setAgents((prev) => {
          if (!prev[agentType]) return prev;
          const prevAgent = prev[agentType];
          const newLog =
            stage === 'completed' && stepName && !prevAgent.step_log.includes(`✓ ${stepName}`)
              ? [...prevAgent.step_log, `✓ ${stepName}`]
              : prevAgent.step_log;
          return {
            ...prev,
            [agentType]: {
              ...prevAgent,
              progress_pct: pct,
              current_step_name: stage === 'executing' ? stepName : prevAgent.current_step_name,
              step_log: newLog,
            },
          };
        });
      }

      if (event === 'agent_status') {
        const agentType = data.agent_type as string;
        const status = data.status as string;
        const pct = (data.progress_pct as number) ?? undefined;
        setAgents((prev) => {
          if (!prev[agentType]) return prev;
          return {
            ...prev,
            [agentType]: {
              ...prev[agentType],
              status,
              ...(pct !== undefined ? { progress_pct: pct } : {}),
            },
          };
        });
      }

      if (event === 'finding') {
        setFindings((prev) => [
          {
            id: (data.finding_id as string) ?? String(Date.now()),
            title: (data.title as string) ?? 'Finding',
            severity: (data.severity as Finding['severity']) ?? 'info',
            source_system: (data.source_system as string) ?? '',
            timestamp: new Date().toLocaleTimeString(),
          },
          ...prev,
        ]);
      }

      if (event === 'orchestrator') {
        const status = data.status as string;
        if (['completed', 'failed', 'paused'].includes(status)) {
          setOverallStatus(status);
          onEngagementUpdate({ ...engagement, status });
          // Fetch fresh engagement data to show results
          engagementsApi.get(engagement.id).then(onEngagementUpdate).catch(() => {});
        }
      }
    });

    wsRef.current = ws;
    return () => ws.close();
  }, [engagement.id]);

  // Auto-scroll findings
  useEffect(() => {
    findingsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [findings]);

  const handlePause = async () => {
    try {
      await engagementsApi.pause(engagement.id);
    } catch {}
  };

  const handleResume = async () => {
    try {
      await engagementsApi.resume(engagement.id);
      setOverallStatus('running');
    } catch {}
  };

  const isActive = overallStatus === 'running';
  const isDone = overallStatus === 'completed';
  const isFailed = overallStatus === 'failed';
  const isPaused = overallStatus === 'paused';

  return (
    <div className="space-y-4">
      {/* Pipeline header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold">{engagement.company_name}</h2>
          <p className="text-[11px] font-mono text-theme-text-muted mt-0.5">
            {String(engagement.config?.engagement_type ?? 'full_diligence').replace(/_/g, ' ').toUpperCase()}
            {' · '}
            {isDone && <span className="text-green-400">COMPLETED</span>}
            {isFailed && <span className="text-red-400">FAILED</span>}
            {isActive && <span className="text-blue-400">RUNNING</span>}
            {isPaused && <span className="text-amber-400">PAUSED</span>}
          </p>
        </div>
        <div className="flex gap-2">
          {isActive && (
            <button
              onClick={handlePause}
              className="px-3 py-1.5 text-[10px] font-mono border border-amber-500/40 text-amber-400
                         rounded-lg hover:bg-amber-500/10 transition-colors"
            >
              PAUSE
            </button>
          )}
          {isPaused && (
            <button
              onClick={handleResume}
              className="px-3 py-1.5 text-[10px] font-mono border border-green-500/40 text-green-400
                         rounded-lg hover:bg-green-500/10 transition-colors"
            >
              RESUME
            </button>
          )}
        </div>
      </div>

      {/* Agent progress cards */}
      <div className="grid grid-cols-3 gap-3">
        {AGENT_META.map(({ type, label, Icon, color }) => {
          const agent = agents[type];
          const pct = Math.round(agent.progress_pct);
          return (
            <div
              key={type}
              className="border border-theme-border rounded-xl p-4 space-y-3 bg-theme-bg/50"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon className="w-4 h-4 text-theme-text-muted" />
                  <span className="text-xs font-semibold tracking-wide">{label.toUpperCase()}</span>
                </div>
                {STATUS_ICONS[agent.status] ?? <Clock className="w-3.5 h-3.5 text-theme-text-muted" />}
              </div>

              {/* Progress bar */}
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-[10px] font-mono text-theme-text-muted capitalize">
                    {agent.status}
                  </span>
                  <span className="text-[10px] font-mono text-theme-text-muted">{pct}%</span>
                </div>
                <div className="h-1 bg-theme-border rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${agentColor(color, pct)}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>

              {/* Current step */}
              {agent.current_step_name && agent.status === 'running' && (
                <div className="flex items-center gap-1.5 text-[10px] font-mono text-theme-text-muted truncate">
                  <ChevronRight className="w-3 h-3 flex-shrink-0 text-blue-400" />
                  <span className="truncate">{agent.current_step_name.replace(/_/g, ' ')}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Lower panel: step log + findings */}
      <div className="grid grid-cols-2 gap-3">
        {/* Step log */}
        <div className="border border-theme-border rounded-xl overflow-hidden">
          <div className="px-4 py-2.5 border-b border-theme-border bg-theme-bg/60">
            <span className="text-[10px] font-mono font-semibold text-theme-text-muted tracking-widest">
              STEP LOG
            </span>
          </div>
          <div className="h-64 overflow-y-auto p-3 space-y-1 font-mono text-[11px]">
            {Object.entries(agents).flatMap(([agentType, agent]) =>
              agent.step_log.map((line, i) => (
                <div key={`${agentType}-${i}`} className="flex items-center gap-2 text-theme-text-muted">
                  <CheckCircle2 className="w-3 h-3 flex-shrink-0 text-green-500" />
                  <span>{line.replace('✓ ', '')}</span>
                </div>
              ))
            )}
            {isActive && (
              <div className="flex items-center gap-2 text-blue-400">
                <Loader2 className="w-3 h-3 animate-spin flex-shrink-0" />
                <span>
                  {Object.values(agents).find((a) => a.status === 'running')?.current_step_name?.replace(/_/g, ' ') ?? 'processing...'}
                </span>
              </div>
            )}
            {Object.values(agents).every((a) => a.status === 'queued') && (
              <p className="text-theme-text-muted/50 py-4 text-center">Waiting for pipeline to start...</p>
            )}
            <div ref={stepLogEndRef} />
          </div>
        </div>

        {/* Findings feed */}
        <div className="border border-theme-border rounded-xl overflow-hidden">
          <div className="px-4 py-2.5 border-b border-theme-border bg-theme-bg/60 flex items-center justify-between">
            <span className="text-[10px] font-mono font-semibold text-theme-text-muted tracking-widest">
              LIVE FINDINGS
            </span>
            {findings.length > 0 && (
              <span className="text-[10px] font-mono text-theme-text-muted">{findings.length} found</span>
            )}
          </div>
          <div className="h-64 overflow-y-auto p-3 space-y-2">
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
                      {f.source_system} · {f.timestamp}
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
