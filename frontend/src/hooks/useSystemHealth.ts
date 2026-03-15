import { useState, useEffect, useCallback } from 'react';
import { connectAgentStatus } from '../lib/apiClient';

export type CheckStatus = 'pass' | 'fail' | 'pending';

export interface HealthCheck {
  name: string;
  description: string;
  status: CheckStatus;
  detail?: string;
}

export type SystemStatus = 'OPERATIONAL' | 'DEGRADED' | 'OFFLINE';

export interface SystemHealth {
  status: SystemStatus;
  checks: HealthCheck[];
  loading: boolean;
  lastChecked: Date | null;
  recheck: () => void;
}

const BACKEND_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? '';

async function checkApi(): Promise<HealthCheck> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/health`, { signal: AbortSignal.timeout(5000) });
    const data = await res.json();
    if (res.ok && data.status === 'healthy') {
      return { name: 'API', description: 'Backend reachable', status: 'pass' };
    }
    return { name: 'API', description: 'Backend reachable', status: 'fail', detail: `Unexpected response: ${data.status}` };
  } catch (err) {
    return { name: 'API', description: 'Backend reachable', status: 'fail', detail: (err as Error).message };
  }
}

async function checkReadiness(): Promise<HealthCheck[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/health/ready`, { signal: AbortSignal.timeout(5000) });
    const data = await res.json() as { status: string; checks: Record<string, string> };
    const db = data.checks?.database ?? 'unknown';
    const redis = data.checks?.redis ?? 'unknown';
    return [
      {
        name: 'Database',
        description: 'PostgreSQL connectivity',
        status: db === 'connected' ? 'pass' : 'fail',
        detail: db !== 'connected' ? db : undefined,
      },
      {
        name: 'Redis',
        description: 'Redis connectivity',
        status: redis === 'connected' ? 'pass' : redis === 'unavailable' ? 'fail' : 'fail',
        detail: redis !== 'connected' ? redis : undefined,
      },
    ];
  } catch (err) {
    const detail = (err as Error).message;
    return [
      { name: 'Database', description: 'PostgreSQL connectivity', status: 'fail', detail },
      { name: 'Redis', description: 'Redis connectivity', status: 'fail', detail },
    ];
  }
}

async function checkLlm(): Promise<HealthCheck> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/health/llm`, { signal: AbortSignal.timeout(20000) });
    const data = await res.json() as {
      status: string;
      providers: Record<string, { ok: boolean; detail?: string }>;
    };

    const providers = data.providers ?? {};
    const passing = Object.entries(providers)
      .filter(([, p]) => p.ok)
      .map(([name, p]) => `${name}${p.detail ? ` (${p.detail})` : ''}`);
    const failing = Object.entries(providers)
      .filter(([, p]) => !p.ok)
      .map(([name, p]) => `${name}: ${p.detail ?? 'error'}`);

    if (data.status === 'connected') {
      return {
        name: 'LLM',
        description: 'AI Providers',
        status: 'pass',
        detail: passing.join(', '),
      };
    }
    return {
      name: 'LLM',
      description: 'AI Providers',
      status: 'fail',
      detail: failing.join(' · '),
    };
  } catch (err) {
    return { name: 'LLM', description: 'AI Providers', status: 'fail', detail: (err as Error).message };
  }
}

function checkWebSocket(): Promise<HealthCheck> {
  return new Promise((resolve) => {
    const timeout = setTimeout(() => {
      resolve({ name: 'WebSocket', description: 'Real-time agent updates', status: 'fail', detail: 'Connection timed out' });
    }, 5000);

    try {
      const ws = connectAgentStatus(undefined, undefined);
      ws.onopen = () => {
        clearTimeout(timeout);
        ws.close();
        resolve({ name: 'WebSocket', description: 'Real-time agent updates', status: 'pass' });
      };
      ws.onerror = () => {
        clearTimeout(timeout);
        ws.close();
        resolve({ name: 'WebSocket', description: 'Real-time agent updates', status: 'fail', detail: 'Connection refused' });
      };
    } catch (err) {
      clearTimeout(timeout);
      resolve({ name: 'WebSocket', description: 'Real-time agent updates', status: 'fail', detail: (err as Error).message });
    }
  });
}

export function useSystemHealth(pollIntervalMs = 60_000): SystemHealth {
  const [checks, setChecks] = useState<HealthCheck[]>([
    { name: 'API', description: 'Backend reachable', status: 'pending' },
    { name: 'Database', description: 'PostgreSQL connectivity', status: 'pending' },
    { name: 'Redis', description: 'Redis connectivity', status: 'pending' },
    { name: 'WebSocket', description: 'Real-time agent updates', status: 'pending' },
    { name: 'LLM', description: 'AI Providers', status: 'pending' },
  ]);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const run = useCallback(async () => {
    setLoading(true);
    const [api, readiness, ws, llm] = await Promise.all([
      checkApi(),
      checkReadiness(),
      checkWebSocket(),
      checkLlm(),
    ]);
    setChecks([api, ...readiness, ws, llm]);
    setLastChecked(new Date());
    setLoading(false);
  }, []);

  useEffect(() => {
    run();
    const interval = setInterval(run, pollIntervalMs);
    return () => clearInterval(interval);
  }, [run, pollIntervalMs]);

  const passing = checks.filter(c => c.status === 'pass').length;
  const total = checks.length;
  const status: SystemStatus =
    passing === total ? 'OPERATIONAL' :
    passing === 0 ? 'OFFLINE' :
    'DEGRADED';

  return { status, checks, loading, lastChecked, recheck: run };
}
