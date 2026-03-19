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

/**
 * Read the Supabase access token from localStorage without React context.
 * Supabase stores the session under the key:
 *   sb-{project_ref}-auth-token
 */
function getAuthToken(): string | null {
  try {
    // Try all supabase session keys in localStorage
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('sb-') && key.endsWith('-auth-token')) {
        const raw = localStorage.getItem(key);
        if (raw) {
          const parsed = JSON.parse(raw) as { access_token?: string };
          return parsed.access_token ?? null;
        }
      }
    }
  } catch {
    // ignore
  }
  return null;
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

  const authHeaders: Record<string, string> = {};
  const token = getAuthToken();
  if (token) authHeaders['Authorization'] = `Bearer ${token}`;

  const config: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...headers,
    },
  };

  if (body && method !== 'GET') {
    config.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE}${endpoint}`, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    // FastAPI 422 returns detail as an array of validation error objects
    let detail: string;
    if (Array.isArray(error.detail)) {
      detail = error.detail
        .map((e: { msg?: string; loc?: string[] }) =>
          [e.loc?.slice(-1)[0], e.msg].filter(Boolean).join(': ')
        )
        .join('; ');
    } else {
      detail = String(error.detail || 'Unknown error');
    }
    throw new ApiError(response.status, detail);
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

  restart: (id: string) =>
    request<Engagement>(`/engagements/${id}/restart`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      // Pass the current data mode so the backend updates the engagement config
      // before re-running — ensures live mode actually uses live connectors.
      body: JSON.stringify({ demo_mode: isDemoMode() }),
    }),

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
    display_name: "Google Sheets & Drive",
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
        key: "folder_id",
        label: "Google Drive Folder ID (for Drive export)",
        placeholder: "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
        secret: false,
        required: false,
      },
      {
        key: "share_email",
        label: "Share with (email)",
        placeholder: "partner@firm.com",
        secret: false,
        required: false,
      },
    ],
  },
  // ── VDR ──────────────────────────────────────────────
  {
    system_name: "datasite",
    display_name: "Datasite VDR",
    category: "VDR",
    auth_type: "OAuth 2.0 (Client Credentials)",
    fields: [
      { key: "partner_id",     label: "Partner ID",     placeholder: "ds-partner-...", secret: false, required: true },
      { key: "partner_secret", label: "Partner Secret", placeholder: "",               secret: true,  required: true },
      { key: "project_id",     label: "Project ID",     placeholder: "proj-12345",     secret: false, required: true },
      { key: "folder_path",    label: "Folder Path (optional)", placeholder: "/Due Diligence", secret: false, required: false },
    ],
  },
  {
    system_name: "intralinks",
    display_name: "Intralinks VDR",
    category: "VDR",
    auth_type: "OAuth 2.0 (Resource Owner)",
    fields: [
      { key: "username",     label: "Intralinks Email",    placeholder: "user@firm.com", secret: false, required: true },
      { key: "password",     label: "Intralinks Password", placeholder: "",              secret: true,  required: true },
      { key: "workspace_id", label: "Workspace ID",        placeholder: "ws-12345",      secret: false, required: true },
      { key: "folder_id",    label: "Root Folder ID (optional)", placeholder: "fld-67890", secret: false, required: false },
    ],
  },
  // ── Expert Call Transcripts ───────────────────────────
  {
    system_name: "tegus",
    display_name: "Tegus",
    category: "Expert Transcripts",
    auth_type: "API Key",
    fields: [
      { key: "api_key", label: "API Key", placeholder: "teg_live_...", secret: true, required: true },
    ],
  },
  {
    system_name: "third_bridge",
    display_name: "Third Bridge",
    category: "Expert Transcripts",
    auth_type: "OAuth 2.0 (Client Credentials)",
    fields: [
      { key: "client_id",     label: "Client ID",     placeholder: "tb-client-...", secret: false, required: true },
      { key: "client_secret", label: "Client Secret", placeholder: "",              secret: true,  required: true },
    ],
  },
];

/** Map the UI auth_type label to the backend credential_type enum. */
function authTypeToCredType(authType: string): string {
  const a = authType.toLowerCase();
  if (a.includes('oauth')) return 'oauth';
  if (a === 'api key') return 'api_key';
  if (a.includes('token')) return 'token';
  if (a === 'browser login') return 'username_password';
  if (a === 'service account') return 'api_key';
  return 'api_key';
}

export const credentialsApi = {
  store: (
    engagementId: string,
    systemName: string,
    authType: string,
    credentialData: Record<string, string>,
  ) =>
    request<{ id: string; system_name: string; credential_type: string; created_at: string }>(
      `/credentials/${engagementId}/${systemName}`,
      {
        method: 'POST',
        body: {
          credential_type: authTypeToCredType(authType),
          credential_data: credentialData,
        } as unknown as Record<string, unknown>,
      },
    ),

  list: async (engagementId: string): Promise<{ systems: string[] }> => {
    const res = await request<{ systems: Array<{ system_name: string }>; total: number }>(
      `/credentials/${engagementId}`,
    );
    return { systems: res.systems.map((s) => s.system_name) };
  },

  remove: (engagementId: string, systemName: string) =>
    request<void>(`/credentials/${engagementId}/${systemName}`, { method: 'DELETE' }),
};

// ── Document endpoints ──────────────────────────────────

export interface DocumentRecord {
  id: string;
  engagement_id: string;
  filename: string;
  file_type: string;
  file_size_bytes: number;
  page_count?: number;
  status: 'processing' | 'ready' | 'error';
  error_message?: string;
  has_text: boolean;
  created_at: string;
}

export const documentsApi = {
  list: (engagementId: string) =>
    request<DocumentRecord[]>(`/engagements/${engagementId}/documents`),

  upload: async (engagementId: string, file: File): Promise<DocumentRecord> => {
    const formData = new FormData();
    formData.append('file', file);
    const resp = await fetch(`${API_BASE}/engagements/${engagementId}/documents`, {
      method: 'POST',
      body: formData,
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new ApiError(resp.status, err.detail || 'Upload failed');
    }
    return resp.json();
  },

  delete: (engagementId: string, documentId: string) =>
    request<void>(`/engagements/${engagementId}/documents/${documentId}`, { method: 'DELETE' }),
};

// ── Monitoring endpoints ────────────────────────────────

export interface MonitoringRun {
  id: string;
  schedule_id: string;
  engagement_id: string;
  status: string;
  deltas: Array<{
    metric: string;
    baseline: number;
    current: number;
    delta_abs: number;
    delta_pct: number;
    severity: 'info' | 'warning' | 'critical';
  }> | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface MonitoringSchedule {
  id: string;
  engagement_id: string;
  name: string;
  frequency: string;
  cron_expression: string | null;
  enabled: boolean;
  sources: string[] | null;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string;
  recent_runs: MonitoringRun[];
}

export const monitoringApi = {
  list: (engagementId: string) =>
    request<MonitoringSchedule[]>(`/engagements/${engagementId}/monitoring`),

  get: (engagementId: string, scheduleId: string) =>
    request<MonitoringSchedule>(`/engagements/${engagementId}/monitoring/${scheduleId}`),

  create: (engagementId: string, body: {
    name: string;
    frequency?: string;
    cron_expression?: string;
    sources?: string[];
    baseline_snapshot?: Record<string, number>;
  }) =>
    request<MonitoringSchedule>(`/engagements/${engagementId}/monitoring`, {
      method: 'POST',
      body: body as unknown as Record<string, unknown>,
    }),

  update: (engagementId: string, scheduleId: string, body: {
    name?: string;
    frequency?: string;
    enabled?: boolean;
    sources?: string[];
  }) =>
    request<MonitoringSchedule>(`/engagements/${engagementId}/monitoring/${scheduleId}`, {
      method: 'PATCH',
      body: body as unknown as Record<string, unknown>,
    }),

  delete: (engagementId: string, scheduleId: string) =>
    request<void>(`/engagements/${engagementId}/monitoring/${scheduleId}`, { method: 'DELETE' }),

  triggerRun: (engagementId: string, scheduleId: string, currentMetrics: Record<string, number> = {}) =>
    request<MonitoringRun>(`/engagements/${engagementId}/monitoring/${scheduleId}/run`, {
      method: 'POST',
      body: { current_metrics: currentMetrics } as unknown as Record<string, unknown>,
    }),

  listRuns: (engagementId: string, scheduleId: string) =>
    request<MonitoringRun[]>(`/engagements/${engagementId}/monitoring/${scheduleId}/runs`),
};

// ── Transcripts endpoints ───────────────────────────────

export interface ExpertTranscript {
  id: string;
  engagement_id: string;
  source: string;
  external_id: string | null;
  title: string;
  expert_name: string | null;
  expert_role: string | null;
  call_date: string | null;
  company_name: string | null;
  sentiment: string | null;
  key_themes: string[] | null;
  extracted_insights: string | null;
  file_size_bytes: number | null;
  status: string;
  error_message: string | null;
  created_at: string;
}

export const transcriptsApi = {
  list: (engagementId: string) =>
    request<ExpertTranscript[]>(`/engagements/${engagementId}/transcripts`),

  upload: async (engagementId: string, file: File): Promise<ExpertTranscript> => {
    const formData = new FormData();
    formData.append('file', file);
    const token = getAuthToken();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`${API_BASE}/engagements/${engagementId}/transcripts`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new ApiError(resp.status, err.detail || 'Upload failed');
    }
    return resp.json();
  },

  fetch: (engagementId: string, body: {
    source: 'tegus' | 'third_bridge';
    company_name: string;
    max_transcripts?: number;
  }) =>
    request<ExpertTranscript[]>(`/engagements/${engagementId}/transcripts/fetch`, {
      method: 'POST',
      body: body as unknown as Record<string, unknown>,
    }),

  delete: (engagementId: string, transcriptId: string) =>
    request<void>(`/engagements/${engagementId}/transcripts/${transcriptId}`, { method: 'DELETE' }),
};

// ── Primary Research (Commercial DD) ──────────────────────────────────────

export interface PrimaryResearchRecord {
  id: string;
  engagement_id: string;
  type: 'customer_interview' | 'channel_check' | 'win_loss' | 'market_sizing';
  company_name: string;
  contact_name: string | null;
  contact_role: string | null;
  interview_date: string | null;
  notes: string | null;
  sentiment: string | null;
  key_themes: string[];
  action_items: string[];
  status: string;
  created_at: string;
}

export interface ResearchSummary {
  total: number;
  by_type: Record<string, number>;
  sentiment_distribution: Record<string, number>;
  top_themes: string[];
  companies_covered: string[];
}

export const primaryResearchApi = {
  list: (engagementId: string, type?: string) => {
    const q = type ? `?type=${type}` : '';
    return request<PrimaryResearchRecord[]>(`/engagements/${engagementId}/primary-research${q}`);
  },
  create: (engagementId: string, body: Partial<PrimaryResearchRecord>) =>
    request<PrimaryResearchRecord>(`/engagements/${engagementId}/primary-research`, {
      method: 'POST',
      body: body as Record<string, unknown>,
    }),
  summary: (engagementId: string) =>
    request<ResearchSummary>(`/engagements/${engagementId}/primary-research/summary`),
  update: (engagementId: string, recordId: string, body: Partial<PrimaryResearchRecord>) =>
    request<PrimaryResearchRecord>(`/engagements/${engagementId}/primary-research/${recordId}`, {
      method: 'PATCH',
      body: body as Record<string, unknown>,
    }),
  delete: (engagementId: string, recordId: string) =>
    request<void>(`/engagements/${engagementId}/primary-research/${recordId}`, { method: 'DELETE' }),
};

// ── External Records (Verification) ───────────────────────────────────────

export interface ExternalRecord {
  id: string;
  engagement_id: string;
  source: 'courtlistener' | 'uspto' | 'ucc' | 'bank_statement';
  record_type: string;
  external_id: string | null;
  title: string;
  description: string | null;
  url: string | null;
  risk_level: string;
  raw_data: Record<string, unknown>;
  corroborates_finding: string | null;
  created_at: string;
}

export interface ConfidenceResult {
  overall_confidence: number;
  source_independence: number;
  per_finding: Record<string, number>;
}

export const externalRecordsApi = {
  list: (engagementId: string) =>
    request<ExternalRecord[]>(`/engagements/${engagementId}/external-records`),
  fetchCourt: (engagementId: string, companyName: string, maxResults = 10) =>
    request<ExternalRecord[]>(`/engagements/${engagementId}/external-records/fetch/court`, {
      method: 'POST',
      body: { company_name: companyName, max_results: maxResults },
    }),
  fetchPatents: (engagementId: string, companyName: string, maxResults = 10) =>
    request<ExternalRecord[]>(`/engagements/${engagementId}/external-records/fetch/patents`, {
      method: 'POST',
      body: { company_name: companyName, max_results: maxResults },
    }),
  uploadBankStatement: async (engagementId: string, file: File): Promise<ExternalRecord> => {
    const formData = new FormData();
    formData.append('file', file);
    const token = getAuthToken();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`${API_BASE}/engagements/${engagementId}/external-records/upload/bank-statement`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new ApiError(resp.status, err.detail || 'Upload failed');
    }
    return resp.json();
  },
  delete: (engagementId: string, recordId: string) =>
    request<void>(`/engagements/${engagementId}/external-records/${recordId}`, { method: 'DELETE' }),
  confidence: (engagementId: string) =>
    request<ConfidenceResult>(`/engagements/${engagementId}/external-records/confidence`),
};

// ── Legal Findings (Contract Analysis) ────────────────────────────────────

export interface LegalFinding {
  id: string;
  engagement_id: string;
  document_id: string | null;
  clause_type: string;
  text_excerpt: string;
  risk_level: string;
  requires_review: boolean;
  reviewed: boolean;
  notes: string | null;
  created_at: string;
}

export interface LegalRiskSummary {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  unreviewed: number;
}

export const legalFindingsApi = {
  list: (engagementId: string, params?: { clause_type?: string; requires_review?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.clause_type) q.set('clause_type', params.clause_type);
    if (params?.requires_review !== undefined) q.set('requires_review', String(params.requires_review));
    const qs = q.toString() ? `?${q.toString()}` : '';
    return request<LegalFinding[]>(`/engagements/${engagementId}/legal-findings${qs}`);
  },
  analyzeAll: (engagementId: string) =>
    request<LegalFinding[]>(`/engagements/${engagementId}/legal-findings/analyze-all`, { method: 'POST' }),
  update: (engagementId: string, findingId: string, body: Partial<LegalFinding>) =>
    request<LegalFinding>(`/engagements/${engagementId}/legal-findings/${findingId}`, {
      method: 'PATCH',
      body: body as Record<string, unknown>,
    }),
  delete: (engagementId: string, findingId: string) =>
    request<void>(`/engagements/${engagementId}/legal-findings/${findingId}`, { method: 'DELETE' }),
  riskSummary: (engagementId: string) =>
    request<LegalRiskSummary>(`/engagements/${engagementId}/legal-findings/risk-summary`),
};

// ── Technical DD (GitHub Analysis) ────────────────────────────────────────

export interface TechnicalDDReport {
  id: string;
  engagement_id: string;
  repo_url: string | null;
  language_stats: Record<string, number>;
  contributor_count: number | null;
  bus_factor: number | null;
  commit_velocity: number | null;
  open_issues_count: number | null;
  security_vulnerabilities: unknown[];
  dependency_risks: unknown[];
  health_score: number | null;
  status: string;
  error_message: string | null;
  created_at: string;
}

export const technicalDDApi = {
  list: (engagementId: string) =>
    request<TechnicalDDReport[]>(`/engagements/${engagementId}/technical-dd`),
  create: (engagementId: string, repoUrl: string, githubToken?: string) =>
    request<TechnicalDDReport>(`/engagements/${engagementId}/technical-dd`, {
      method: 'POST',
      body: { repo_url: repoUrl, github_token: githubToken },
    }),
  delete: (engagementId: string, reportId: string) =>
    request<void>(`/engagements/${engagementId}/technical-dd/${reportId}`, { method: 'DELETE' }),
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
