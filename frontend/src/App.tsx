import { useState, useEffect, useCallback } from 'react';
import {
  Search,
  BarChart3,
  FileText,
  CheckCircle2,
  ArrowRight,
  Activity,
  Lock,
  Cpu,
  Server,
  GitBranch,
  ChevronDown,
  LayoutDashboard,
  LogIn,
  LogOut,
  Target,
  Zap,
  Download,
  TableProperties,
  Shield,
  Share2,
  Play,
  Clock,
  Database,
  Globe,
  Mail,
  MessageSquare,
  HardDrive,
  Layers,
  KeyRound,
  EyeOff,
  FileLock2,
} from 'lucide-react';
import WebGLBackground from './components/WebGLBackground';
import ScrollReveal from './components/ScrollReveal';
import ParallaxSection from './components/ParallaxSection';
import ScrollIndicator from './components/ScrollIndicator';
import ScrollProgressBar from './components/ScrollProgressBar';
import TextReveal from './components/TextReveal';
import MagneticElement from './components/MagneticElement';
import ThemeToggle from './components/ThemeToggle';
import DemoModeToggle from './components/DemoModeToggle';
import Loader from './components/Loader';
import Dashboard from './components/dashboard/Dashboard';
import RequestAccessModal from './components/RequestAccessModal';
import { useTheme } from './context/ThemeContext';
import { useView } from './context/ViewContext';
import { useAuth } from './context/AuthContext';
import { useDemoMode } from './context/DemoModeContext';
import AuthModal from './components/auth/AuthModal';
import { useScrollProgress, useMousePosition } from './hooks/useScrollProgress';
import { useSystemHealth } from './hooks/useSystemHealth';

// ─── Data ─────────────────────────────────────────────────────────────────────

const agents = [
  {
    id: '01',
    name: 'Research',
    icon: Search,
    description:
      'Pulls structured data from Salesforce, NetSuite, SEC EDGAR, HubSpot and Crunchbase via REST APIs. Accesses Bloomberg, CapIQ, PitchBook and other closed systems via TinyFish browser automation.',
    status: 'ACTIVE',
    capabilities: [
      'OAuth 2.0 / API key authentication',
      'SOQL and SuiteQL financial queries',
      'SEC EDGAR public filing extraction',
      'TinyFish browser automation for closed systems',
    ],
  },
  {
    id: '02',
    name: 'Analysis',
    icon: BarChart3,
    description:
      'Cross-references extracted data in real time. Detects revenue variances between CRM and ERP, flags cost anomalies, and scores findings by confidence — with LLM-powered synthesis and deterministic fallbacks.',
    status: 'ACTIVE',
    capabilities: [
      'Revenue variance detection (>5% threshold)',
      'Cost anomaly detection (>8% threshold)',
      'Cross-source discrepancy flagging',
      'LLM confidence scoring with fallback',
    ],
  },
  {
    id: '03',
    name: 'Delivery',
    icon: FileText,
    description:
      'Generates the executive PDF and Excel workbook, performs a PII compliance sweep, then distributes results to your configured channels — automatically, without manual steps.',
    status: 'ACTIVE',
    capabilities: [
      'LLM-drafted executive summary',
      'Structured PDF + Excel output',
      'PII compliance review before distribution',
      'Slack, email, Google Drive, SharePoint delivery',
    ],
  },
];

const restIntegrations = [
  { name: 'Salesforce', detail: 'OAuth 2.0 · CRM pipeline & deal history' },
  { name: 'NetSuite', detail: 'OAuth 1.0 TBA · Revenue, P&L, balance sheet' },
  { name: 'SEC EDGAR', detail: 'Public API · 10-K, 10-Q, insider transactions' },
  { name: 'HubSpot', detail: 'API Key · Marketing metrics & lead funnel' },
  { name: 'Crunchbase', detail: 'API Key · Funding history & acquisitions' },
];

const browserIntegrations = [
  'Bloomberg Terminal',
  'Capital IQ',
  'PitchBook',
  'LinkedIn Sales Navigator',
  'SAP Fiori',
  'Oracle Fusion',
  'Microsoft Dynamics',
  'QuickBooks',
  'ZoomInfo',
  'Marketo',
];

const distributionChannels = [
  {
    icon: MessageSquare,
    name: 'Slack',
    detail: 'Formatted summary posted to your channel via Incoming Webhook',
  },
  {
    icon: Mail,
    name: 'Email',
    detail: 'HTML report with optional PDF attachment via SMTP',
  },
  {
    icon: HardDrive,
    name: 'Google Drive',
    detail: 'PDF and Excel uploaded via Service Account — shareable link returned',
  },
  {
    icon: Layers,
    name: 'SharePoint',
    detail: 'JSON and PDF uploaded via Microsoft Graph API (OAuth 2.0)',
  },
];

const capabilities = [
  {
    title: 'Stateful Execution',
    icon: Server,
    description:
      'Each pipeline step is checkpointed. If a run is interrupted, it resumes from the last completed step — not from the beginning.',
    metrics: ['Step-level recovery', 'Async task queue', 'Persistent state'],
  },
  {
    title: 'Credential Vault',
    icon: KeyRound,
    description:
      'API keys, OAuth tokens, and service account credentials are stored encrypted (AES-256-GCM) in your private vault. Configure each source once — the agents handle authentication on every run.',
    metrics: ['AES-256-GCM encryption', 'Per-engagement isolation', 'Credential reuse'],
  },
  {
    title: 'Multi-Agent Coordination',
    icon: GitBranch,
    description:
      'Research, Analysis, and Delivery run as a sequential pipeline with explicit state handoffs. Each step validates its output before passing forward.',
    metrics: ['Sequential pipeline', 'State validation', 'LLM + deterministic fallback'],
  },
  {
    title: 'TinyFish Browser Automation',
    icon: Cpu,
    description:
      'For data sources without open APIs — Bloomberg, CapIQ, PitchBook, SAP — KEEN delegates to TinyFish browser automation infrastructure, built and maintained by the TinyFish accelerator team.',
    metrics: ['Natural-language goals', 'TinyFish API delegation', 'Human-like extraction'],
  },
];

const securityPoints = [
  {
    icon: KeyRound,
    title: 'Encrypted Credential Vault',
    detail:
      'Every API key and token is encrypted with AES-256-GCM before storage. Credentials are scoped to your engagement — never shared across accounts.',
  },
  {
    icon: EyeOff,
    title: 'Per-User Data Isolation',
    detail:
      'Engagements are stamped with your user ID at creation. Other users — including admins — cannot read your engagement data or extracted findings.',
  },
  {
    icon: FileLock2,
    title: 'JWT Authentication',
    detail:
      'Authentication runs through Supabase with ES256 JWKS verification on the backend. Tokens are short-lived and verified on every API request.',
  },
  {
    icon: Shield,
    title: 'Full Audit Trail',
    detail:
      'Every data point extracted carries a timestamp, source system, and agent step ID. The complete chain-of-custody is stored with each engagement.',
  },
  {
    icon: Database,
    title: 'No Training on Your Data',
    detail:
      'Extracted deal data is used only to generate your report. It is not used to train models, shared with third parties, or retained beyond your account.',
  },
  {
    icon: Globe,
    title: 'Deployed on Fly.io (EU/US)',
    detail:
      'Backend runs on Fly.io with regional routing. Database hosted on Supabase with row-level security enforced at the Postgres layer.',
  },
];

// ─── Component ────────────────────────────────────────────────────────────────

function App() {
  const [activeAgent, setActiveAgent] = useState(0);
  const [timestamp, setTimestamp] = useState('');
  const [isVisible, setIsVisible] = useState(false);
  const [navSolid, setNavSolid] = useState(false);
  const [statusOpen, setStatusOpen] = useState(false);
  const [requestAccessOpen, setRequestAccessOpen] = useState(false);
  const { status: systemStatus, checks, loading: healthLoading, lastChecked, recheck } = useSystemHealth();
  const [loading, setLoading] = useState(true);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalTab, setAuthModalTab] = useState<'signin' | 'signup'>('signin');
  const { theme } = useTheme();
  const { view, setView } = useView();
  const { user, signOut, loading: authLoading } = useAuth();
  const { setMode } = useDemoMode();

  const tryDemo = () => {
    setMode('demo');
    setView('dashboard');
  };

  const openDashboard = () => {
    if (user) {
      setView('dashboard');
    } else {
      setAuthModalTab('signin');
      setAuthModalOpen(true);
    }
  };

  const openSignIn = () => { setAuthModalTab('signin'); setAuthModalOpen(true); };
  const openSignUp = () => { setAuthModalTab('signup'); setAuthModalOpen(true); };

  const scrollProgress = useScrollProgress();
  const mouse = useMousePosition();

  const handleLoaderComplete = useCallback(() => {
    setLoading(false);
    requestAnimationFrame(() => setIsVisible(true));
  }, []);

  useEffect(() => {
    if (view === 'dashboard' && !authLoading && !user) {
      setView('landing');
      setAuthModalTab('signin');
      setAuthModalOpen(true);
    }
  }, [view, user, authLoading, setView]);

  useEffect(() => {
    const updateTimestamp = () => {
      const now = new Date();
      setTimestamp(now.toISOString().split('T')[0].replace(/-/g, '.'));
    };
    updateTimestamp();
    const timestampInterval = setInterval(updateTimestamp, 1000);
    const agentInterval = setInterval(() => setActiveAgent(p => (p + 1) % 3), 4000);
    const onScroll = () => setNavSolid(window.scrollY > 80);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      clearInterval(agentInterval);
      clearInterval(timestampInterval);
      window.removeEventListener('scroll', onScroll);
    };
  }, []);

  if (view === 'dashboard' && authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-theme-bg">
        <div className="w-1.5 h-1.5 rounded-full bg-theme-text-muted animate-pulse" />
      </div>
    );
  }

  if (view === 'dashboard' && user) {
    return <Dashboard />;
  }

  return (
    <div className="min-h-screen bg-theme-bg text-theme-text overflow-x-hidden transition-colors duration-400">
      {loading && <Loader onComplete={handleLoaderComplete} />}

      <WebGLBackground scrollProgress={scrollProgress} mouseX={mouse.x} mouseY={mouse.y} theme={theme} />
      <ScrollProgressBar progress={scrollProgress} />
      <ScrollIndicator />

      {/* ── Nav ──────────────────────────────────────────────────────────── */}
      <nav
        className={`fixed top-0 w-full z-50 transition-all duration-500 ${
          navSolid ? 'backdrop-blur-md border-b border-theme-border' : 'bg-transparent border-b border-transparent'
        }`}
        style={navSolid ? { backgroundColor: 'var(--color-nav-solid)' } : undefined}
      >
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-3 md:py-4">
          <div className="flex items-center justify-between">
            <MagneticElement strength={0.15}>
              <div className="flex items-center gap-2 md:gap-3">
                <div>
                  <h1 className="text-sm md:text-base font-bold tracking-tight">KEEN</h1>
                  <p className="text-[9px] md:text-[10px] text-theme-text-muted font-mono">
                    SHARPER JUDGMENT. FASTER EXECUTION.
                  </p>
                </div>
              </div>
            </MagneticElement>

            <div className="flex items-center gap-3 md:gap-6">
              {/* System status */}
              <div className="relative hidden sm:block">
                <button
                  onClick={() => setStatusOpen(o => !o)}
                  className="text-[10px] md:text-xs font-mono text-theme-text-muted hover:text-theme-text transition-colors flex items-center gap-1.5"
                >
                  STATUS:{' '}
                  <span className={systemStatus === 'OPERATIONAL' ? 'text-green-500' : systemStatus === 'DEGRADED' ? 'text-yellow-500' : 'text-red-500'}>
                    {healthLoading ? '...' : systemStatus}
                  </span>
                  <span className={`w-1.5 h-1.5 rounded-full ${systemStatus === 'OPERATIONAL' ? 'bg-green-500 animate-pulse' : systemStatus === 'DEGRADED' ? 'bg-yellow-500 animate-pulse' : 'bg-red-500'}`} />
                </button>

                {statusOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setStatusOpen(false)} />
                    <div className="absolute right-0 top-6 z-50 w-64 rounded-lg border border-theme-border bg-theme-bg shadow-xl p-3 font-mono text-[10px]">
                      <div className="flex items-center justify-between mb-2.5">
                        <span className="font-semibold text-theme-text text-[11px]">System Health</span>
                        <button onClick={recheck} className="text-theme-text-muted hover:text-theme-text transition-colors">↻</button>
                      </div>
                      <div className="space-y-2">
                        {checks.map(check => (
                          <div key={check.name} className="flex items-start gap-2">
                            <span className={`mt-0.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${check.status === 'pass' ? 'bg-green-500' : check.status === 'fail' ? 'bg-red-500' : 'bg-theme-text-muted animate-pulse'}`} />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between">
                                <span className="text-theme-text font-semibold">{check.name}</span>
                                <span className={check.status === 'pass' ? 'text-green-500' : check.status === 'fail' ? 'text-red-500' : 'text-theme-text-muted'}>
                                  {check.status === 'pending' ? 'checking' : check.status}
                                </span>
                              </div>
                              <p className="text-theme-text-muted">{check.description}</p>
                              {check.detail && <p className="text-red-400 mt-0.5 truncate" title={check.detail}>{check.detail}</p>}
                            </div>
                          </div>
                        ))}
                      </div>
                      {lastChecked && (
                        <p className="text-theme-text-muted mt-2.5 pt-2 border-t border-theme-border">
                          Last checked {lastChecked.toLocaleTimeString()}
                        </p>
                      )}
                    </div>
                  </>
                )}
              </div>

              <div className="text-[10px] md:text-xs font-mono text-theme-text-muted">{timestamp}</div>
              <DemoModeToggle />

              <button
                onClick={openDashboard}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[10px]
                           font-mono font-semibold backdrop-blur-sm transition-all duration-300 tracking-wider
                           border-theme-border bg-theme-border/30 text-theme-text-muted
                           hover:border-theme-text/40 hover:text-theme-text"
                title="Open pipeline dashboard"
              >
                <LayoutDashboard className="w-3 h-3 flex-shrink-0" />
                <span className="hidden sm:inline">DASHBOARD</span>
              </button>

              {!authLoading && (
                user ? (
                  <div className="flex items-center gap-2">
                    <span className="hidden md:block text-[10px] font-mono text-theme-text-muted max-w-[120px] truncate">{user.email}</span>
                    <button
                      onClick={() => signOut()}
                      title="Sign out"
                      className="flex items-center gap-1 px-2 py-1 rounded-full border text-[10px] font-mono font-semibold transition-all duration-200 border-theme-border text-theme-text-muted hover:border-red-500/50 hover:text-red-400"
                    >
                      <LogOut className="w-3 h-3" />
                      <span className="hidden sm:inline">OUT</span>
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={openSignIn}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-full border text-[10px] font-mono font-semibold transition-all duration-200 border-theme-border bg-transparent text-theme-text-muted hover:border-theme-text/40 hover:text-theme-text"
                    >
                      <LogIn className="w-3 h-3" />
                      <span>SIGN IN</span>
                    </button>
                    <button
                      onClick={openSignUp}
                      className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold transition-all duration-200 bg-orange-600 hover:bg-orange-500 text-white border border-orange-600"
                    >
                      <span>SIGN UP</span>
                    </button>
                  </div>
                )
              )}

              <ThemeToggle />
            </div>
          </div>
        </div>
      </nav>

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="relative min-h-screen flex items-center px-4 md:px-6 pt-20 pb-16">
        <div className="max-w-7xl mx-auto w-full relative z-10">
          <div className="mb-8 md:mb-12">
            <p
              className={`text-xs font-mono text-theme-text-muted mb-4 transition-all duration-700 ${
                isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
              }`}
            >
              TINYFISH ACCELERATOR / 2026 · EARLY ACCESS
            </p>

            <ParallaxSection speed={0.1}>
              <TextReveal
                text="Op/Intelligence"
                tag="h2"
                className="text-6xl md:text-8xl lg:text-9xl font-bold leading-none tracking-tighter"
                delay={0.3}
                stagger={0.05}
                type="chars"
              />
            </ParallaxSection>

            <ScrollReveal animation="fadeUp" delay={0.6} className="mt-6 md:mt-8">
              <p className="text-lg md:text-xl lg:text-2xl text-theme-text-secondary max-w-3xl leading-relaxed">
                Automate the data gathering and reporting layer of PE due diligence.
                Three agents research live sources, cross-reference findings, and deliver
                a structured report — while your team focuses on judgment.
              </p>
            </ScrollReveal>

            <ScrollReveal animation="fadeUp" delay={0.9}>
              <div className="mt-8 flex flex-wrap items-center gap-4">
                <MagneticElement strength={0.2}>
                  <button
                    onClick={() => setRequestAccessOpen(true)}
                    className="group px-6 py-3 bg-orange-600 hover:bg-orange-500 text-white text-sm font-medium transition-all duration-300 flex items-center gap-2"
                  >
                    Book a Demo
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-300" />
                  </button>
                </MagneticElement>
                <MagneticElement strength={0.2}>
                  <button
                    onClick={tryDemo}
                    className="flex items-center gap-2 px-6 py-3 border border-theme-border hover:border-orange-600/50 text-sm font-medium transition-all duration-300 text-theme-text-secondary hover:text-theme-text"
                  >
                    <Play className="w-3.5 h-3.5" />
                    Try Live Demo
                  </button>
                </MagneticElement>
              </div>

              {/* Honest pilot label */}
              <p className="mt-5 text-[11px] font-mono text-theme-text-faint">
                Currently in pilot · 5 REST integrations live · 10 more via TinyFish browser automation
              </p>
            </ScrollReveal>
          </div>

          <div
            className={`absolute bottom-12 left-1/2 -translate-x-1/2 transition-all duration-1000 delay-[1.2s] ${
              isVisible ? 'opacity-100' : 'opacity-0'
            }`}
          >
            <ChevronDown className="w-5 h-5 text-theme-text-faint animate-bounce" />
          </div>
        </div>
      </section>

      {/* ── How It Works ─────────────────────────────────────────────────── */}
      <section className="relative py-16 md:py-24 px-4 md:px-6">
        <div className="max-w-7xl mx-auto">
          <ScrollReveal animation="fadeUp" className="mb-12 md:mb-16 text-center">
            <p className="text-xs font-mono text-orange-600 mb-3 tracking-widest">THE PROCESS</p>
            <TextReveal
              text="How It Works"
              tag="h3"
              className="text-3xl md:text-5xl font-bold"
              stagger={0.04}
            />
            <p className="text-sm md:text-base text-theme-text-muted mt-4 max-w-xl mx-auto">
              From company name to structured report — fully automated, start to finish.
            </p>
          </ScrollReveal>

          <div className="relative">
            <div className="hidden md:block absolute top-12 left-[16.67%] right-[16.67%] h-px bg-gradient-to-r from-transparent via-orange-600/30 to-transparent" />
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-6">
              {[
                {
                  step: '01',
                  icon: Target,
                  title: 'Define Your Engagement',
                  description:
                    "Name the target company and set your objectives. Store credentials for your data sources in the encrypted vault once — the system reuses them on every run.",
                  detail: 'Takes ~5 minutes',
                  color: 'from-orange-600/10',
                },
                {
                  step: '02',
                  icon: Zap,
                  title: 'Agents Run Autonomously',
                  description:
                    'Research pulls data from connected sources. Analysis cross-references and flags variances. Each step is checkpointed — if a run is interrupted it resumes, not restarts.',
                  detail: 'Runs autonomously',
                  color: 'from-blue-600/10',
                },
                {
                  step: '03',
                  icon: Download,
                  title: 'Report Delivered Automatically',
                  description:
                    'An executive PDF and Excel workbook are generated and pushed to your Slack, inbox, Google Drive, or SharePoint — no manual downloads, no copy-pasting.',
                  detail: 'Delivered automatically',
                  color: 'from-green-600/10',
                },
              ].map(({ step, icon: Icon, title, description, detail, color }, idx) => (
                <ScrollReveal key={idx} animation="fadeUp" delay={idx * 0.15}>
                  <div className="relative group">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="w-10 h-10 rounded-full border border-orange-600/40 bg-orange-600/10 flex items-center justify-center flex-shrink-0">
                        <span className="text-xs font-mono font-bold text-orange-500">{step}</span>
                      </div>
                      <div className="flex-1 h-px bg-theme-border" />
                    </div>
                    <div className="relative bg-theme-surface backdrop-blur-sm border border-theme-border p-6 md:p-8 hover:border-orange-600/30 transition-all duration-500 overflow-hidden">
                      <div className={`absolute inset-0 bg-gradient-to-br ${color} to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />
                      <div className="relative z-10">
                        <div className="w-12 h-12 flex items-center justify-center border border-theme-border group-hover:border-orange-600/40 transition-all duration-300 mb-5">
                          <Icon className="w-6 h-6 text-orange-600" />
                        </div>
                        <h4 className="text-xl font-bold mb-3">{title}</h4>
                        <p className="text-sm text-theme-text-secondary leading-relaxed mb-5">{description}</p>
                        <div className="flex items-center gap-2">
                          <Clock className="w-3 h-3 text-orange-600/60" />
                          <span className="text-[11px] font-mono text-theme-text-muted">{detail}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </ScrollReveal>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── What You Receive ─────────────────────────────────────────────── */}
      <section className="relative py-16 md:py-20 px-4 md:px-6">
        <div className="max-w-7xl mx-auto">
          <ScrollReveal animation="fadeUp" className="mb-10 md:mb-14">
            <p className="text-xs font-mono text-orange-600 mb-3 tracking-widest">DELIVERABLES</p>
            <TextReveal
              text="What You Receive"
              tag="h3"
              className="text-3xl md:text-5xl font-bold"
              stagger={0.04}
            />
            <p className="text-sm md:text-base text-theme-text-muted mt-4 max-w-2xl">
              Every engagement produces four concrete outputs — generated, formatted, and distributed automatically.
            </p>
          </ScrollReveal>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              {
                icon: FileText,
                label: 'EXECUTIVE REPORT',
                title: 'Board-Ready PDF',
                description:
                  'LLM-drafted narrative with key findings, flagged discrepancies, and sourced data points — formatted for investment committee review.',
                tag: 'PDF export',
                accent: 'border-orange-600/60 bg-orange-600/5',
                iconColor: 'text-orange-500',
              },
              {
                icon: TableProperties,
                label: 'FINANCIAL MODEL',
                title: 'Excel Workbook',
                description:
                  'Extracted financials — revenue, expense, and balance sheet data — structured in Excel with source annotations and variance flags.',
                tag: 'Excel export',
                accent: 'border-green-600/40 bg-green-600/5',
                iconColor: 'text-green-500',
              },
              {
                icon: Shield,
                label: 'AUDIT TRAIL',
                title: 'Full Chain-of-Custody',
                description:
                  'Every data point carries a timestamp, source system, and agent step ID. The complete extraction log is stored with your engagement.',
                tag: 'Always included',
                accent: 'border-blue-600/40 bg-blue-600/5',
                iconColor: 'text-blue-400',
              },
              {
                icon: Share2,
                label: 'DISTRIBUTION',
                title: 'Pushed to Your Workflow',
                description:
                  'Results are automatically delivered to Slack, email, Google Drive, or SharePoint — wherever your team already works.',
                tag: 'Auto-delivered',
                accent: 'border-purple-600/40 bg-purple-600/5',
                iconColor: 'text-purple-400',
              },
            ].map(({ icon: Icon, label, title, description, tag, accent, iconColor }, idx) => (
              <ScrollReveal key={idx} animation="fadeUp" delay={idx * 0.1}>
                <div className={`group relative bg-theme-surface backdrop-blur-sm border ${accent} p-6 hover:shadow-lg hover:shadow-black/20 transition-all duration-500 h-full flex flex-col`}>
                  <div className="flex items-start justify-between mb-4">
                    <div className="w-10 h-10 flex items-center justify-center border border-theme-border">
                      <Icon className={`w-5 h-5 ${iconColor}`} />
                    </div>
                    <span className={`text-[9px] font-mono px-2 py-1 rounded-full border ${accent} ${iconColor}`}>{tag}</span>
                  </div>
                  <p className="text-[10px] font-mono text-theme-text-muted mb-1.5 tracking-wider">{label}</p>
                  <h4 className="text-base font-bold mb-3">{title}</h4>
                  <p className="text-xs text-theme-text-secondary leading-relaxed flex-1">{description}</p>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── Data Sources ─────────────────────────────────────────────────── */}
      <section className="relative py-16 md:py-20 px-4 md:px-6">
        <div className="max-w-7xl mx-auto">
          <ScrollReveal animation="fadeUp" className="mb-10 md:mb-14">
            <p className="text-xs font-mono text-orange-600 mb-3 tracking-widest">DATA SOURCES</p>
            <TextReveal
              text="What Gets Connected"
              tag="h3"
              className="text-3xl md:text-5xl font-bold"
              stagger={0.04}
            />
            <p className="text-sm md:text-base text-theme-text-muted mt-4 max-w-2xl">
              Five sources have direct REST API integrations. Ten more are accessible via TinyFish browser automation — for systems that don't expose public APIs.
            </p>
          </ScrollReveal>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* REST integrations */}
            <ScrollReveal animation="fadeLeft">
              <div className="bg-theme-surface backdrop-blur-sm border border-theme-border p-6 md:p-8 h-full">
                <div className="flex items-center gap-2 mb-6">
                  <Database className="w-4 h-4 text-orange-600" />
                  <span className="text-[11px] font-mono text-orange-600 tracking-widest">REST API · LIVE</span>
                </div>
                <div className="space-y-3">
                  {restIntegrations.map(({ name, detail }) => (
                    <div key={name} className="flex items-start justify-between gap-4 py-3 border-b border-theme-border-subtle last:border-0">
                      <div className="flex items-center gap-3">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0 mt-1.5" />
                        <span className="text-sm font-semibold">{name}</span>
                      </div>
                      <span className="text-[11px] font-mono text-theme-text-muted text-right leading-tight">{detail}</span>
                    </div>
                  ))}
                </div>
                <p className="mt-4 text-[11px] font-mono text-theme-text-faint">Credentials stored per-engagement in encrypted vault</p>
              </div>
            </ScrollReveal>

            {/* Browser automation */}
            <ScrollReveal animation="fadeRight">
              <div className="bg-theme-surface backdrop-blur-sm border border-theme-border p-6 md:p-8 h-full">
                <div className="flex items-center gap-2 mb-6">
                  <Cpu className="w-4 h-4 text-theme-text-muted" />
                  <span className="text-[11px] font-mono text-theme-text-muted tracking-widest">BROWSER AUTOMATION · VIA TINYFISH</span>
                </div>
                <div className="grid grid-cols-2 gap-2 mb-4">
                  {browserIntegrations.map(name => (
                    <div key={name} className="flex items-center gap-2 py-2 px-3 border border-theme-border-subtle">
                      <div className="w-1.5 h-1.5 rounded-full bg-theme-text-muted flex-shrink-0" />
                      <span className="text-xs text-theme-text-secondary">{name}</span>
                    </div>
                  ))}
                </div>
                <p className="text-[11px] font-mono text-theme-text-faint leading-relaxed">
                  Browser automation goals are delegated to the TinyFish API. Requires a TinyFish API key — built and maintained by the TinyFish accelerator.
                </p>
              </div>
            </ScrollReveal>
          </div>

          {/* Distribution channels */}
          <ScrollReveal animation="fadeUp" className="mt-6">
            <div className="bg-theme-surface backdrop-blur-sm border border-theme-border p-6 md:p-8">
              <div className="flex items-center gap-2 mb-6">
                <Share2 className="w-4 h-4 text-orange-600" />
                <span className="text-[11px] font-mono text-orange-600 tracking-widest">OUTPUT DISTRIBUTION · 4 CHANNELS</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {distributionChannels.map(({ icon: Icon, name, detail }) => (
                  <div key={name} className="flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                      <Icon className="w-4 h-4 text-orange-600" />
                      <span className="text-sm font-semibold">{name}</span>
                    </div>
                    <p className="text-[11px] text-theme-text-muted leading-relaxed">{detail}</p>
                  </div>
                ))}
              </div>
            </div>
          </ScrollReveal>
        </div>
      </section>

      {/* ── Agent Architecture ───────────────────────────────────────────── */}
      <section className="relative py-16 md:py-20 px-4 md:px-6">
        <div className="max-w-7xl mx-auto">
          <ScrollReveal animation="fadeLeft" className="mb-8 md:mb-10">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
              <div>
                <p className="text-xs font-mono text-orange-600 mb-3 tracking-widest">SYSTEM ARCHITECTURE</p>
                <TextReveal
                  text="Agent Architecture"
                  tag="h3"
                  className="text-3xl md:text-5xl font-bold"
                  stagger={0.04}
                />
              </div>
              <div className="flex items-center gap-2 text-xs font-mono text-theme-text-muted">
                <Activity className="w-3 h-3" />
                <span>RUNTIME ACTIVE</span>
              </div>
            </div>
          </ScrollReveal>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
            {agents.map((agent, idx) => {
              const Icon = agent.icon;
              const isActive = activeAgent === idx;
              return (
                <ScrollReveal key={idx} animation="fadeUp" delay={idx * 0.12}>
                  <div
                    className={`bg-theme-surface backdrop-blur-sm border p-6 md:p-8 transition-all duration-500 h-full ${
                      isActive ? 'border-orange-600 shadow-lg shadow-orange-600/10' : 'border-theme-border hover:border-orange-600/30'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-6">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 flex items-center justify-center border transition-all duration-300 ${isActive ? 'bg-orange-600/10 border-orange-600' : 'bg-theme-surface-elevated border-theme-border'}`}>
                          <Icon className={`w-5 h-5 ${isActive ? 'text-orange-500' : 'text-theme-text-muted'}`} />
                        </div>
                        <div>
                          <p className="text-[10px] font-mono text-theme-text-faint">{agent.id}</p>
                          <h4 className="text-xl font-bold">{agent.name}</h4>
                        </div>
                      </div>
                      {isActive && (
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                          <span className="text-[9px] font-mono text-green-500">LIVE</span>
                        </div>
                      )}
                    </div>
                    <p className="text-sm text-theme-text-secondary mb-6 leading-relaxed">{agent.description}</p>
                    <div className="space-y-2.5">
                      {agent.capabilities.map((cap, capIdx) => (
                        <div key={capIdx} className="flex items-start gap-2 text-xs text-theme-text-muted">
                          <ArrowRight className="w-3 h-3 mt-0.5 flex-shrink-0 text-orange-600/70" />
                          <span>{cap}</span>
                        </div>
                      ))}
                    </div>
                    <div className="mt-6 pt-6 border-t border-theme-border-subtle">
                      <div className="flex items-center justify-between">
                        <p className="text-[10px] font-mono text-theme-text-faint">
                          STATUS: <span className="text-green-500">{agent.status}</span>
                        </p>
                        <div className="w-16 h-[2px] bg-theme-border rounded overflow-hidden">
                          <div className="h-full bg-orange-600 transition-all duration-1000" style={{ width: isActive ? '100%' : '30%' }} />
                        </div>
                      </div>
                    </div>
                  </div>
                </ScrollReveal>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── Capabilities ─────────────────────────────────────────────────── */}
      <section className="relative py-16 md:py-20 px-4 md:px-6">
        <div className="max-w-7xl mx-auto">
          <ScrollReveal animation="fadeUp" className="mb-8 md:mb-10">
            <p className="text-xs font-mono text-orange-600 mb-3 tracking-widest">UNDER THE HOOD</p>
            <TextReveal
              text="How It's Built"
              tag="h3"
              className="text-3xl md:text-5xl font-bold"
              stagger={0.04}
            />
          </ScrollReveal>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
            {capabilities.map((capability, idx) => {
              const Icon = capability.icon;
              return (
                <ScrollReveal key={idx} animation={idx % 2 === 0 ? 'fadeLeft' : 'fadeRight'} delay={idx * 0.1}>
                  <div className="group relative bg-theme-surface backdrop-blur-sm border border-theme-border p-6 md:p-8 hover:border-orange-600/40 transition-all duration-500 overflow-hidden h-full">
                    <div className="absolute inset-0 bg-gradient-to-br from-orange-600/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                    <div className="relative z-10">
                      <div className="flex items-start gap-4 mb-4">
                        <div className="w-12 h-12 flex items-center justify-center border border-theme-border group-hover:border-orange-600/50 transition-all duration-300 flex-shrink-0">
                          <Icon className="w-6 h-6 text-orange-600 transition-transform duration-300 group-hover:scale-110" />
                        </div>
                        <div>
                          <h4 className="text-lg md:text-xl font-bold mb-2">{capability.title}</h4>
                          <p className="text-sm text-theme-text-secondary leading-relaxed">{capability.description}</p>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2 mt-6">
                        {capability.metrics.map((metric, metricIdx) => (
                          <span
                            key={metricIdx}
                            className="px-3 py-1.5 border text-[11px] font-mono text-theme-text-muted hover:border-orange-600/40 hover:text-theme-text-secondary transition-colors duration-300"
                            style={{ backgroundColor: 'var(--color-metric-chip-bg)', borderColor: 'var(--color-metric-chip-border)' }}
                          >
                            {metric}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </ScrollReveal>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── Security & Privacy ───────────────────────────────────────────── */}
      <section className="relative py-16 md:py-20 px-4 md:px-6">
        <div className="max-w-7xl mx-auto">
          <ScrollReveal animation="fadeUp" className="mb-10 md:mb-14">
            <p className="text-xs font-mono text-orange-600 mb-3 tracking-widest">SECURITY & PRIVACY</p>
            <TextReveal
              text="Your Deal Data is Protected"
              tag="h3"
              className="text-3xl md:text-5xl font-bold"
              stagger={0.04}
            />
            <p className="text-sm md:text-base text-theme-text-muted mt-4 max-w-2xl">
              PE due diligence involves sensitive, often non-public information.
              Here's exactly how we handle it.
            </p>
          </ScrollReveal>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {securityPoints.map(({ icon: Icon, title, detail }, idx) => (
              <ScrollReveal key={idx} animation="fadeUp" delay={idx * 0.08}>
                <div className="group bg-theme-surface backdrop-blur-sm border border-theme-border p-6 hover:border-green-600/30 transition-all duration-400 h-full">
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 flex items-center justify-center border border-theme-border group-hover:border-green-600/40 transition-all duration-300 flex-shrink-0">
                      <Icon className="w-5 h-5 text-green-500" />
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold mb-2">{title}</h4>
                      <p className="text-xs text-theme-text-secondary leading-relaxed">{detail}</p>
                    </div>
                  </div>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── Get Started CTA ──────────────────────────────────────────────── */}
      <section className="relative py-20 md:py-28 px-4 md:px-6">
        <div className="max-w-4xl mx-auto">
          <ScrollReveal animation="scale">
            <div className="relative bg-theme-surface backdrop-blur-sm border border-orange-600/30 p-10 md:p-16 overflow-hidden text-center">
              <div className="absolute inset-0 bg-gradient-to-br from-orange-600/8 via-transparent to-transparent pointer-events-none" />
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-px bg-gradient-to-r from-transparent via-orange-600/60 to-transparent" />

              <div className="relative z-10">
                <p className="text-xs font-mono text-orange-600 mb-4 tracking-widest">GET STARTED</p>

                <TextReveal
                  text="See it run on a real company."
                  tag="h3"
                  className="text-3xl md:text-5xl font-bold leading-tight mb-5"
                  stagger={0.03}
                />

                <p className="text-sm md:text-base text-theme-text-muted max-w-lg mx-auto mb-10 leading-relaxed">
                  Book a 30-minute session — we'll walk through a live engagement,
                  connect a data source you use, and show you the output in real time.
                </p>

                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                  <MagneticElement strength={0.2}>
                    <button
                      onClick={() => setRequestAccessOpen(true)}
                      className="group w-full sm:w-auto px-8 py-4 bg-orange-600 hover:bg-orange-500 text-white text-sm font-medium transition-all duration-300 flex items-center justify-center gap-2"
                    >
                      Book a Demo
                      <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-300" />
                    </button>
                  </MagneticElement>
                  <MagneticElement strength={0.2}>
                    <button
                      onClick={tryDemo}
                      className="group w-full sm:w-auto flex items-center justify-center gap-2 px-8 py-4 border border-theme-border hover:border-orange-600/50 text-sm font-medium transition-all duration-300 text-theme-text-secondary hover:text-theme-text"
                    >
                      <Play className="w-3.5 h-3.5" />
                      Explore Demo First
                    </button>
                  </MagneticElement>
                </div>

                <p className="text-[11px] font-mono text-theme-text-faint mt-8">
                  Backed by TinyFish Accelerator · Currently in early access · No commitment required
                </p>
              </div>
            </div>
          </ScrollReveal>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer className="relative border-t border-theme-border py-10 md:py-12 px-4 md:px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-12">
            <ScrollReveal animation="fadeUp">
              <div className="mb-4">
                <h3 className="text-base font-bold tracking-tight">KEEN</h3>
                <p className="text-[10px] text-theme-text-faint font-mono mt-1">
                  SHARPER JUDGMENT. FASTER EXECUTION.
                </p>
              </div>
              <p className="text-xs text-theme-text-faint leading-relaxed">
                AI-powered research and reporting for PE due diligence.
                Built at TinyFish Accelerator, 2026. Currently in early access.
              </p>
            </ScrollReveal>

            <ScrollReveal animation="fadeUp" delay={0.1}>
              <h4 className="text-[10px] font-mono text-theme-text-muted mb-4 tracking-wider">WHAT'S BUILT</h4>
              <ul className="space-y-2.5 text-xs text-theme-text-faint">
                {['Research → Analysis → Delivery Pipeline', 'AES-256 Credential Vault', 'PDF + Excel Report Generation', 'Slack, Email, Drive, SharePoint Distribution'].map(item => (
                  <li key={item} className="flex items-start gap-2">
                    <CheckCircle2 className="w-3 h-3 text-green-500 mt-0.5 flex-shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </ScrollReveal>

            <ScrollReveal animation="fadeUp" delay={0.2}>
              <h4 className="text-[10px] font-mono text-theme-text-muted mb-4 tracking-wider">INTEGRATIONS</h4>
              <ul className="space-y-2.5 text-xs text-theme-text-faint">
                {['Salesforce · NetSuite · SEC EDGAR', 'HubSpot · Crunchbase (REST API)', 'Bloomberg · CapIQ · PitchBook (TinyFish)', 'SAP · Oracle · Dynamics (TinyFish)'].map(item => (
                  <li key={item} className="hover:text-theme-text-secondary transition-colors duration-200 cursor-default">{item}</li>
                ))}
              </ul>
            </ScrollReveal>
          </div>

          <ScrollReveal animation="fade" delay={0.3}>
            <div className="mt-12 pt-8 border-t border-theme-border-subtle text-center">
              <p className="text-xs text-theme-text-faint font-mono">
                &copy; 2026 KEEN — BACKED BY TINYFISH ACCELERATOR · EARLY ACCESS
              </p>
            </div>
          </ScrollReveal>
        </div>
      </footer>

      {/* Modals */}
      {requestAccessOpen && <RequestAccessModal onClose={() => setRequestAccessOpen(false)} />}
      {authModalOpen && (
        <AuthModal
          initialTab={authModalTab}
          onClose={() => setAuthModalOpen(false)}
          onSuccess={() => { setAuthModalOpen(false); setView('dashboard'); }}
        />
      )}
    </div>
  );
}

export default App;
