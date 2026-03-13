/**
 * KEEN API Client — typed fetch wrapper for the backend REST API.
 */

const API_BASE = '/api/v1';

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: Record<string, unknown>;
  headers?: Record<string, string>;
}

class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`API Error ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {} } = options;

  const config: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  };

  if (body && method !== 'GET') {
    config.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE}${endpoint}`, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, error.detail || 'Unknown error');
  }

  return response.json();
}

// ── Lead endpoints ──────────────────────────────────────

export interface Lead {
  id: string;
  name: string;
  email: string;
  company?: string;
  aum_range?: string;
  message?: string;
  created_at: string;
}

export interface LeadInput {
  name: string;
  email: string;
  company?: string;
  aum_range?: string;
  message?: string;
}

export const leadsApi = {
  create: (data: LeadInput) =>
    request<Lead>('/leads', { method: 'POST', body: data as unknown as Record<string, unknown> }),

  list: (skip = 0, limit = 50) =>
    request<Lead[]>(`/leads?skip=${skip}&limit=${limit}`),

  get: (id: string) =>
    request<Lead>(`/leads/${id}`),
};

// ── Engagement endpoints ────────────────────────────────

export interface AgentRunSummary {
  id: string;
  agent_type: string;
  status: string;
  progress_pct: number;
  current_step: number;
  total_steps: number;
}

export interface Engagement {
  id: string;
  company_name: string;
  target_company?: string;
  pe_firm?: string;
  deal_size?: string;
  engagement_type: string;
  status: string;
  config: Record<string, unknown>;
  notes?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
  agent_runs?: AgentRunSummary[];
}

export interface EngagementInput {
  company_name: string;
  target_company?: string;
  pe_firm?: string;
  deal_size?: string;
  config?: Record<string, unknown>;
  notes?: string;
}

export const engagementsApi = {
  create: (data: EngagementInput) =>
    request<Engagement>('/engagements', { method: 'POST', body: data as unknown as Record<string, unknown> }),

  list: (skip = 0, limit = 50) =>
    request<Engagement[]>(`/engagements?skip=${skip}&limit=${limit}`),

  get: (id: string) =>
    request<Engagement>(`/engagements/${id}`),

  start: (id: string) =>
    request<Engagement>(`/engagements/${id}/start`, { method: 'POST' }),

  pause: (id: string) =>
    request<Engagement>(`/engagements/${id}/pause`, { method: 'POST' }),

  resume: (id: string) =>
    request<Engagement>(`/engagements/${id}/resume`, { method: 'POST' }),
};

// ── WebSocket ───────────────────────────────────────────

export function connectAgentStatus(
  engagementId?: string,
  onMessage?: (event: Record<string, unknown>) => void,
): WebSocket {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsHost = window.location.host;
  const params = engagementId ? `?engagement_id=${engagementId}` : '';
  const ws = new WebSocket(`${wsProtocol}//${wsHost}/ws/agent-status${params}`);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage?.(data);
    } catch {
      // Ignore non-JSON messages
    }
  };

  return ws;
}

export { ApiError };
export default { leadsApi, engagementsApi, connectAgentStatus };
