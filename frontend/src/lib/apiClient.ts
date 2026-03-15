/**
 * KEEN API Client — typed fetch wrapper for the backend REST API.
 *
 * In development the Vite proxy forwards /api and /ws to localhost:8000.
 * In production set VITE_API_URL to your Cloud Run backend URL, e.g.:
 *   VITE_API_URL=https://keen-backend-xxxx.run.app
 */

// In dev VITE_API_URL is empty → relative paths hit the Vite proxy.
// In production it's the full Cloud Run URL.
const BACKEND_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? '';
const API_BASE = `${BACKEND_URL}/api/v1`;

/** Read the current data mode from localStorage without needing React context. */
function isDemoMode(): boolean {
  return localStorage.getItem('keen-data-mode') !== 'live';
}

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

// ── Finding endpoints ───────────────────────────────────

export interface Finding {
  id: string;
  agent_run_id: string;
  finding_type: string;
  source_system?: string;
  title: string;
  description?: string;
  data?: Record<string, unknown>;
  severity: 'info' | 'warning' | 'critical';
  requires_human_review: boolean;
  created_at: string;
}

export const findingsApi = {
  list: (engagementId: string) =>
    request<Finding[]>(`/engagements/${engagementId}/findings`),
};

export const engagementsApi = {
  create: (data: EngagementInput) =>
    request<Engagement>('/engagements', {
      method: 'POST',
      body: {
        ...data,
        // Inject the current data mode into the engagement config so the
        // backend Research Agent knows whether to use DemoConnector or live connectors.
        config: { demo_mode: isDemoMode(), ...(data.config ?? {}) },
      } as Record<string, unknown>,
    }),

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

  delete: (id: string) =>
    request<void>(`/engagements/${id}`, { method: 'DELETE' }),
};

// ── Credentials endpoints ───────────────────────────────

export interface CredentialField {
  key: string;
  label: string;
  placeholder: string;
  secret: boolean;        // true → render as password input
  required: boolean;
}

export interface SystemCredentialSpec {
  system_name: string;
  display_name: string;
  category: string;
  auth_type: string;
  fields: CredentialField[];
}

// Static registry of what fields each system needs.
// Matches the required credentials keys documented in each connector.
export const CREDENTIAL_SPECS: SystemCredentialSpec[] = [
  {
    system_name: "salesforce",
    display_name: "Salesforce CRM",
    category: "CRM",
    auth_type: "OAuth",
    fields: [
      { key: "client_id",     label: "Client ID",      placeholder: "3MVG9...",      secret: false, required: true },
      { key: "client_secret", label: "Client Secret",  placeholder: "abc123...",     secret: true,  required: true },
      { key: "refresh_token", label: "Refresh Token",  placeholder: "5Aep861...",    secret: true,  required: true },
      { key: "instance_url",  label: "Instance URL",   placeholder: "https://mycompany.salesforce.com", secret: false, required: true },
    ],
  },
  {
    system_name: "netsuite",
    display_name: "NetSuite ERP",
    category: "ERP",
    auth_type: "Token (OAuth 1.0)",
    fields: [
      { key: "account_id",       label: "Account ID",        placeholder: "1234567",   secret: false, required: true },
      { key: "consumer_key",     label: "Consumer Key",      placeholder: "abc...",    secret: false, required: true },
      { key: "consumer_secret",  label: "Consumer Secret",   placeholder: "xyz...",    secret: true,  required: true },
      { key: "token_id",         label: "Token ID",          placeholder: "tkn...",    secret: false, required: true },
      { key: "token_secret",     label: "Token Secret",      placeholder: "tks...",    secret: true,  required: true },
    ],
  },
  {
    system_name: "hubspot",
    display_name: "HubSpot",
    category: "Marketing",
    auth_type: "API Key",
    fields: [
      { key: "access_token", label: "Private App Token", placeholder: "pat-na1-...", secret: true, required: true },
    ],
  },
  {
    system_name: "crunchbase",
    display_name: "Crunchbase",
    category: "Intelligence",
    auth_type: "API Key",
    fields: [
      { key: "api_key",   label: "API Key",    placeholder: "cb_usr_...", secret: true,  required: true },
      { key: "permalink", label: "Company Permalink (optional)", placeholder: "acme-corp", secret: false, required: false },
    ],
  },
  {
    system_name: "bloomberg",
    display_name: "Bloomberg Terminal",
    category: "Market Data",
    auth_type: "Browser Login",
    fields: [
      { key: "username", label: "Bloomberg Username", placeholder: "user@firm.com", secret: false, required: true },
      { key: "password", label: "Bloomberg Password", placeholder: "",              secret: true,  required: true },
    ],
  },
  {
    system_name: "capiq",
    display_name: "S&P Capital IQ",
    category: "Market Data",
    auth_type: "Browser Login",
    fields: [
      { key: "username", label: "CapIQ Email",    placeholder: "user@firm.com", secret: false, required: true },
      { key: "password", label: "CapIQ Password", placeholder: "",              secret: true,  required: true },
    ],
  },
  {
    system_name: "pitchbook",
    display_name: "PitchBook",
    category: "Market Data",
    auth_type: "Browser Login",
    fields: [
      { key: "username", label: "PitchBook Email",    placeholder: "user@firm.com", secret: false, required: true },
      { key: "password", label: "PitchBook Password", placeholder: "",              secret: true,  required: true },
    ],
  },
  {
    system_name: "sales_navigator",
    display_name: "LinkedIn Sales Navigator",
    category: "Intelligence",
    auth_type: "Browser Login",
    fields: [
      { key: "username", label: "LinkedIn Email",    placeholder: "user@firm.com", secret: false, required: true },
      { key: "password", label: "LinkedIn Password", placeholder: "",              secret: true,  required: true },
    ],
  },
  {
    system_name: "quickbooks",
    display_name: "QuickBooks Online",
    category: "Accounting",
    auth_type: "Browser Login",
    fields: [
      { key: "username", label: "Intuit Email",       placeholder: "user@firm.com", secret: false, required: true },
      { key: "password", label: "Intuit Password",    placeholder: "",              secret: true,  required: true },
    ],
  },
  {
    system_name: "zoominfo",
    display_name: "ZoomInfo",
    category: "Intelligence",
    auth_type: "Browser Login",
    fields: [
      { key: "username", label: "ZoomInfo Email",    placeholder: "user@firm.com", secret: false, required: true },
      { key: "password", label: "ZoomInfo Password", placeholder: "",              secret: true,  required: true },
    ],
  },
  {
    system_name: "marketo",
    display_name: "Marketo Engage",
    category: "Marketing",
    auth_type: "Browser Login",
    fields: [
      { key: "username",     label: "Marketo Email",        placeholder: "user@firm.com",            secret: false, required: true },
      { key: "password",     label: "Marketo Password",     placeholder: "",                         secret: true,  required: true },
      { key: "instance_url", label: "Instance URL",         placeholder: "https://app-abc123.marketo.com", secret: false, required: false },
    ],
  },
  {
    system_name: "dynamics",
    display_name: "Microsoft Dynamics 365",
    category: "CRM",
    auth_type: "Browser Login",
    fields: [
      { key: "username",     label: "Microsoft 365 Email",  placeholder: "user@company.com",         secret: false, required: true },
      { key: "password",     label: "Microsoft 365 Password", placeholder: "",                       secret: true,  required: true },
      { key: "instance_url", label: "Dynamics Instance URL", placeholder: "https://org.crm.dynamics.com", secret: false, required: false },
    ],
  },
  {
    system_name: "sap",
    display_name: "SAP ERP",
    category: "ERP",
    auth_type: "Browser Login",
    fields: [
      { key: "username",     label: "SAP User ID",      placeholder: "JDOE",             secret: false, required: true },
      { key: "password",     label: "SAP Password",     placeholder: "",                 secret: true,  required: true },
      { key: "instance_url", label: "SAP Fiori URL",    placeholder: "https://company.sapbydesign.com", secret: false, required: true },
      { key: "client",       label: "Client Number",    placeholder: "100",              secret: false, required: false },
    ],
  },
  {
    system_name: "oracle",
    display_name: "Oracle Cloud ERP",
    category: "ERP",
    auth_type: "Browser Login",
    fields: [
      { key: "username",     label: "Oracle Cloud Email", placeholder: "user@company.com",          secret: false, required: true },
      { key: "password",     label: "Oracle Cloud Password", placeholder: "",                       secret: true,  required: true },
      { key: "instance_url", label: "Oracle Cloud URL",   placeholder: "https://company.fa.em2.oraclecloud.com", secret: false, required: true },
    ],
  },
  {
    system_name: "google_sheets",
    display_name: "Google Sheets",
    category: "Export",
    auth_type: "Service Account",
    fields: [
      {
        key: "service_account_json",
        label: "Service Account Key JSON",
        placeholder: '{"type":"service_account","project_id":"...","private_key_id":"..."}',
        secret: true,
        required: true,
      },
      {
        key: "share_email",
        label: "Share sheet with (email)",
        placeholder: "partner@firm.com",
        secret: false,
        required: false,
      },
    ],
  },
];

export const credentialsApi = {
  store: (engagementId: string, systemName: string, credentials: Record<string, string>) =>
    request<{ message: string; credential_id: string }>(
      `/credentials/${engagementId}/${systemName}`,
      { method: 'POST', body: { credentials } as unknown as Record<string, unknown> },
    ),

  list: (engagementId: string) =>
    request<{ systems: string[] }>(`/credentials/${engagementId}`),

  remove: (engagementId: string, systemName: string) =>
    request<void>(`/credentials/${engagementId}/${systemName}`, { method: 'DELETE' }),
};

// ── WebSocket ───────────────────────────────────────────

export function connectAgentStatus(
  engagementId?: string,
  onMessage?: (event: Record<string, unknown>) => void,
): WebSocket {
  // Derive WebSocket URL from VITE_API_URL if set, otherwise use current host
  let wsBase: string;
  if (BACKEND_URL) {
    // Convert https://... → wss://... or http://... → ws://...
    wsBase = BACKEND_URL.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:');
  } else {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    wsBase = `${wsProtocol}//${window.location.host}`;
  }

  const params = engagementId ? `?engagement_id=${engagementId}` : '';
  const ws = new WebSocket(`${wsBase}/ws/agent-status${params}`);

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
