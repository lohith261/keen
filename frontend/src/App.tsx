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
} from 'lucide-react';
import WebGLBackground from './components/WebGLBackground';
import ScrollReveal from './components/ScrollReveal';
import ParallaxSection from './components/ParallaxSection';
import ScrollIndicator from './components/ScrollIndicator';
import ScrollProgressBar from './components/ScrollProgressBar';
import TextReveal from './components/TextReveal';
import CountUp from './components/CountUp';
import MagneticElement from './components/MagneticElement';
import ThemeToggle from './components/ThemeToggle';
import DemoModeToggle from './components/DemoModeToggle';
import Loader from './components/Loader';
import Dashboard from './components/dashboard/Dashboard';
import RequestAccessModal from './components/RequestAccessModal';
import { useTheme } from './context/ThemeContext';
import { useView } from './context/ViewContext';
import { useAuth } from './context/AuthContext';
import AuthModal from './components/auth/AuthModal';
import { useScrollProgress, useMousePosition } from './hooks/useScrollProgress';
import { useSystemHealth } from './hooks/useSystemHealth';

const agents = [
  {
    id: '01',
    name: 'Research',
    icon: Search,
    description: 'Autonomous authentication across 15+ enterprise systems',
    status: 'ACTIVE',
    capabilities: [
      'Multi-source extraction',
      'Dynamic credential handling',
      'API orchestration',
      'Live data reconciliation',
    ],
  },
  {
    id: '02',
    name: 'Analysis',
    icon: BarChart3,
    description: 'Real-time cross-referencing with variance detection',
    status: 'ACTIVE',
    capabilities: [
      'Discrepancy flagging',
      'Model synchronization',
      'Exception routing',
      'Validation protocols',
    ],
  },
  {
    id: '03',
    name: 'Delivery',
    icon: FileText,
    description: 'Board-ready output generation and distribution',
    status: 'ACTIVE',
    capabilities: [
      'Executive synthesis',
      'Multi-channel distribution',
      'Compliance tracking',
      'Audit trail generation',
    ],
  },
];

const operationalCapabilities = [
  {
    title: 'Stateful Execution',
    icon: Server,
    description:
      '90-second checkpointing ensures seamless recovery. System resumes at exact step, not beginning.',
    metrics: ['4-hour workflows', 'Zero restart overhead', 'Persistent state'],
  },
  {
    title: 'Dynamic Authentication',
    icon: Lock,
    description:
      'Semantic adaptation to auth flows—SSO, MFA, token rotation—without brittle selectors.',
    metrics: ['Multi-factor support', 'Session management', 'Credential vault'],
  },
  {
    title: 'Multi-Agent Coordination',
    icon: GitBranch,
    description:
      'Three specialized agents orchestrate workflows with real-time state synchronization.',
    metrics: ['Event-driven architecture', 'Async processing', 'Conflict resolution'],
  },
  {
    title: 'Browser Orchestration',
    icon: Cpu,
    description:
      'TinyFish infrastructure accesses the 60% of sources without APIs—like human analysts.',
    metrics: ['Headless automation', 'UI semantic parsing', 'Anti-detection measures'],
  },
];

const insights = [
  { label: 'TIME COMPRESSION', value: '4 weeks → 4 hours', metric: '98% reduction', numValue: 98, suffix: '%' },
  { label: 'COST EFFICIENCY', value: '$200K → $40K', metric: '80% savings', numValue: 80, suffix: '%' },
  { label: 'SYSTEM ACCESS', value: '15+ sources', metric: 'Live extraction', numValue: 15, suffix: '+' },
  { label: 'ACCURACY RATE', value: '99.7%', metric: 'Validated output', numValue: 99.7, suffix: '%' },
];

const integrations = [
  'Salesforce', 'NetSuite', 'SAP', 'Oracle', 'Dynamics',
  'QuickBooks', 'HubSpot', 'Marketo', 'Bloomberg', 'CapIQ',
  'PitchBook', 'SEC EDGAR', 'Sales Navigator', 'ZoomInfo', 'Crunchbase',
];

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
    requestAnimationFrame(() => {
      setIsVisible(true);
    });
  }, []);

  // Guard: if view flips to dashboard but no user (e.g. session expired), fall back gracefully
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

    const agentInterval = setInterval(() => {
      setActiveAgent((prev) => (prev + 1) % 3);
    }, 4000);

    const onScroll = () => {
      setNavSolid(window.scrollY > 80);
    };
    window.addEventListener('scroll', onScroll, { passive: true });

    return () => {
      clearInterval(agentInterval);
      clearInterval(timestampInterval);
      window.removeEventListener('scroll', onScroll);
    };
  }, []);

  // If the user tries to go to dashboard while auth is loading, wait
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

      <WebGLBackground
        scrollProgress={scrollProgress}
        mouseX={mouse.x}
        mouseY={mouse.y}
        theme={theme}
      />
      <ScrollProgressBar progress={scrollProgress} />
      <ScrollIndicator />

      <nav
        className={`fixed top-0 w-full z-50 transition-all duration-500 ${
          navSolid
            ? 'backdrop-blur-md border-b border-theme-border'
            : 'bg-transparent border-b border-transparent'
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
              <div className="relative hidden sm:block">
                <button
                  onClick={() => setStatusOpen(o => !o)}
                  className="text-[10px] md:text-xs font-mono text-theme-text-muted hover:text-theme-text transition-colors flex items-center gap-1.5"
                >
                  STATUS:{' '}
                  <span className={
                    systemStatus === 'OPERATIONAL' ? 'text-green-500' :
                    systemStatus === 'DEGRADED' ? 'text-yellow-500' :
                    'text-red-500'
                  }>
                    {healthLoading ? '...' : systemStatus}
                  </span>
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    systemStatus === 'OPERATIONAL' ? 'bg-green-500 animate-pulse' :
                    systemStatus === 'DEGRADED' ? 'bg-yellow-500 animate-pulse' :
                    'bg-red-500'
                  }`} />
                </button>

                {statusOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setStatusOpen(false)} />
                    <div className="absolute right-0 top-6 z-50 w-64 rounded-lg border border-theme-border bg-theme-bg shadow-xl p-3 font-mono text-[10px]">
                      <div className="flex items-center justify-between mb-2.5">
                        <span className="font-semibold text-theme-text text-[11px]">System Health</span>
                        <button
                          onClick={() => { recheck(); }}
                          className="text-theme-text-muted hover:text-theme-text transition-colors"
                        >
                          ↻
                        </button>
                      </div>

                      <div className="space-y-2">
                        {checks.map(check => (
                          <div key={check.name} className="flex items-start gap-2">
                            <span className={`mt-0.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                              check.status === 'pass' ? 'bg-green-500' :
                              check.status === 'fail' ? 'bg-red-500' :
                              'bg-theme-text-muted animate-pulse'
                            }`} />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between">
                                <span className="text-theme-text font-semibold">{check.name}</span>
                                <span className={
                                  check.status === 'pass' ? 'text-green-500' :
                                  check.status === 'fail' ? 'text-red-500' :
                                  'text-theme-text-muted'
                                }>
                                  {check.status === 'pending' ? 'checking' : check.status}
                                </span>
                              </div>
                              <p className="text-theme-text-muted">{check.description}</p>
                              {check.detail && (
                                <p className="text-red-400 mt-0.5 truncate" title={check.detail}>{check.detail}</p>
                              )}
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
              <div className="text-[10px] md:text-xs font-mono text-theme-text-muted">
                {timestamp}
              </div>
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

              {/* Auth controls */}
              {!authLoading && (
                user ? (
                  <div className="flex items-center gap-2">
                    <span className="hidden md:block text-[10px] font-mono text-theme-text-muted max-w-[120px] truncate">
                      {user.email}
                    </span>
                    <button
                      onClick={() => signOut()}
                      title="Sign out"
                      className="flex items-center gap-1 px-2 py-1 rounded-full border text-[10px]
                                 font-mono font-semibold transition-all duration-200
                                 border-theme-border text-theme-text-muted
                                 hover:border-red-500/50 hover:text-red-400"
                    >
                      <LogOut className="w-3 h-3" />
                      <span className="hidden sm:inline">OUT</span>
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={openSignIn}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-full border text-[10px]
                                 font-mono font-semibold transition-all duration-200
                                 border-theme-border bg-transparent text-theme-text-muted
                                 hover:border-theme-text/40 hover:text-theme-text"
                    >
                      <LogIn className="w-3 h-3" />
                      <span>SIGN IN</span>
                    </button>
                    <button
                      onClick={openSignUp}
                      className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px]
                                 font-mono font-semibold transition-all duration-200
                                 bg-orange-600 hover:bg-orange-500 text-white border border-orange-600"
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

      {/* Hero */}
      <section className="relative min-h-screen flex items-center px-4 md:px-6 pt-20 pb-16">
        <div className="max-w-7xl mx-auto w-full relative z-10">
          <div className="mb-8 md:mb-12">
            <p
              className={`text-xs font-mono text-theme-text-muted mb-4 transition-all duration-700 ${
                isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
              }`}
            >
              TINYFISH ACCELERATOR / 2026
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
                Multi-agent system replicating McKinsey-grade PE due diligence.
                Compressing 4 weeks into 4 hours through autonomous execution
                across live enterprise systems.
              </p>
            </ScrollReveal>

            <ScrollReveal animation="fadeUp" delay={0.9}>
              <div className="mt-8 flex items-center gap-4">
                <MagneticElement strength={0.2}>
                  <button
                    onClick={() => setRequestAccessOpen(true)}
                    className="group px-6 py-3 bg-orange-600 hover:bg-orange-500 text-white text-sm font-medium transition-all duration-300 flex items-center gap-2"
                  >
                    Request Access
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-300" />
                  </button>
                </MagneticElement>
                <MagneticElement strength={0.2}>
                  <a
                    href="https://github.com/keen-platform/keen/blob/main/README.md"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-6 py-3 border border-theme-border hover:border-orange-600/50 text-sm font-medium transition-all duration-300 text-theme-text-secondary hover:text-theme-text inline-block"
                  >
                    View Documentation
                  </a>
                </MagneticElement>
              </div>
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

      {/* Metrics */}
      <section className="relative py-16 md:py-20 px-4 md:px-6">
        <div className="max-w-7xl mx-auto">
          <ScrollReveal animation="fadeUp" className="mb-8 md:mb-10">
            <p className="text-xs font-mono text-orange-600 mb-3 tracking-widest">PERFORMANCE METRICS</p>
          </ScrollReveal>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
            {insights.map((insight, idx) => (
              <ScrollReveal
                key={idx}
                animation="fadeUp"
                delay={idx * 0.12}
              >
                <div className="group relative bg-theme-surface backdrop-blur-sm border border-theme-border p-6 md:p-8 hover:border-orange-600/50 transition-all duration-500 overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-br from-orange-600/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  <div className="relative z-10">
                    <p className="text-[10px] font-mono text-theme-text-muted mb-4 tracking-wider">
                      {insight.label}
                    </p>
                    <div className="text-3xl md:text-4xl font-bold text-theme-text mb-2">
                      <CountUp
                        end={insight.numValue}
                        suffix={insight.suffix}
                        decimals={insight.suffix === '%' && insight.numValue % 1 !== 0 ? 1 : 0}
                        duration={2.5}
                      />
                    </div>
                    <p className="text-xs text-theme-text-muted">{insight.metric}</p>
                  </div>
                  <div className="absolute bottom-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-orange-600/50 to-transparent scale-x-0 group-hover:scale-x-100 transition-transform duration-700" />
                </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* Agent Architecture */}
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
              <ScrollReveal
                key={idx}
                animation="fadeUp"
                delay={idx * 0.12}
              >
              <div
                className={`bg-theme-surface backdrop-blur-sm border p-6 md:p-8 transition-all duration-500 h-full ${
                  isActive
                    ? 'border-orange-600 shadow-lg shadow-orange-600/10'
                    : 'border-theme-border hover:border-orange-600/30'
                }`}
              >
                <div className="flex items-start justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-10 h-10 flex items-center justify-center border transition-all duration-300 ${
                        isActive ? 'bg-orange-600/10 border-orange-600' : 'bg-theme-surface-elevated border-theme-border'
                      }`}
                    >
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
                <p className="text-sm text-theme-text-secondary mb-6 leading-relaxed">
                  {agent.description}
                </p>
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
                      <div
                        className="h-full bg-orange-600 transition-all duration-1000"
                        style={{ width: isActive ? '100%' : '30%' }}
                      />
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

      {/* Operational Capabilities */}
      <section className="relative py-16 md:py-20 px-4 md:px-6">
        <div className="max-w-7xl mx-auto">
          <ScrollReveal animation="fadeUp" className="mb-8 md:mb-10">
            <p className="text-xs font-mono text-orange-600 mb-3 tracking-widest">CAPABILITIES</p>
            <TextReveal
              text="Operational Capabilities"
              tag="h3"
              className="text-3xl md:text-5xl font-bold"
              stagger={0.04}
            />
          </ScrollReveal>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
            {operationalCapabilities.map((capability, idx) => {
              const Icon = capability.icon;
              return (
                <ScrollReveal
                  key={idx}
                  animation={idx % 2 === 0 ? 'fadeLeft' : 'fadeRight'}
                  delay={idx * 0.1}
                >
                  <div className="group relative bg-theme-surface backdrop-blur-sm border border-theme-border p-6 md:p-8 hover:border-orange-600/40 transition-all duration-500 overflow-hidden h-full">
                    <div className="absolute inset-0 bg-gradient-to-br from-orange-600/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                    <div className="relative z-10">
                      <div className="flex items-start gap-4 mb-4">
                        <div className="w-12 h-12 flex items-center justify-center border border-theme-border group-hover:border-orange-600/50 transition-all duration-300 flex-shrink-0">
                          <Icon className="w-6 h-6 text-orange-600 transition-transform duration-300 group-hover:scale-110" />
                        </div>
                        <div>
                          <h4 className="text-lg md:text-xl font-bold mb-2">{capability.title}</h4>
                          <p className="text-sm text-theme-text-secondary leading-relaxed">
                            {capability.description}
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2 mt-6">
                        {capability.metrics.map((metric, metricIdx) => (
                          <span
                            key={metricIdx}
                            className="px-3 py-1.5 border text-[11px] font-mono text-theme-text-muted hover:border-orange-600/40 hover:text-theme-text-secondary transition-colors duration-300"
                            style={{
                              backgroundColor: 'var(--color-metric-chip-bg)',
                              borderColor: 'var(--color-metric-chip-border)',
                            }}
                          >
                            {metric}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-orange-600/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
                  </div>
                </ScrollReveal>
              );
            })}
          </div>
        </div>
      </section>

      {/* Integration Section */}
      <section className="relative py-16 md:py-20 px-4 md:px-6">
        <div className="max-w-7xl mx-auto">
          <ScrollReveal animation="scale">
            <div className="relative bg-theme-surface backdrop-blur-sm border border-theme-border p-6 md:p-12 overflow-hidden">
              <div className="absolute inset-0 bg-grid-pattern opacity-[0.02]" />
              <div className="relative z-10">
                <div className="mb-6 md:mb-8">
                  <p className="text-xs font-mono text-orange-600 mb-3 tracking-widest">INTEGRATION</p>
                  <TextReveal
                    text="Live Enterprise Integration"
                    tag="h3"
                    className="text-3xl md:text-5xl font-bold mb-3"
                    stagger={0.04}
                  />
                  <p className="text-sm md:text-base text-theme-text-muted">
                    Authenticated extraction from 15+ systems
                  </p>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 md:gap-3">
                  {integrations.map((source, idx) => (
                    <ScrollReveal
                      key={idx}
                      animation="fadeUp"
                      delay={idx * 0.04}
                      duration={0.6}
                    >
                      <div
                        className="group px-3 py-3 border border-theme-border text-xs font-mono text-theme-text-muted hover:border-orange-600/50 hover:text-theme-text-secondary transition-all duration-300 hover:scale-105 cursor-default text-center"
                        style={{ backgroundColor: 'var(--color-surface-elevated)' }}
                      >
                        {source}
                      </div>
                    </ScrollReveal>
                  ))}
                </div>
              </div>
            </div>
          </ScrollReveal>
        </div>
      </section>

      {/* Competitive Moat */}
      <section className="relative py-16 md:py-20 px-4 md:px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 md:gap-12">
            <ScrollReveal animation="fadeLeft">
              <div>
                <p className="text-xs font-mono text-orange-600 mb-4 tracking-widest">COMPETITIVE ADVANTAGE</p>
                <TextReveal
                  text="19-27 Month Technical Moat"
                  tag="h3"
                  className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 leading-tight"
                  stagger={0.04}
                />
                <p className="text-base md:text-lg text-theme-text-secondary leading-relaxed mb-8">
                  Full-stack workflow automation combining browser orchestration,
                  stateful execution, and semantic adaptation. Not document-based
                  AI or simple RPA—impossible to replicate quickly.
                </p>
                <div className="space-y-4">
                  {[
                    'TinyFish browser infrastructure integration',
                    'Proprietary state management engine',
                    'Multi-agent coordination framework',
                  ].map((item, idx) => (
                    <ScrollReveal key={idx} animation="fadeLeft" delay={0.2 + idx * 0.1}>
                      <div className="flex items-start gap-3 group">
                        <CheckCircle2 className="w-5 h-5 text-orange-600 mt-0.5 flex-shrink-0 transition-transform duration-300 group-hover:scale-110" />
                        <span className="text-sm text-theme-text-secondary group-hover:text-theme-text transition-colors duration-200">
                          {item}
                        </span>
                      </div>
                    </ScrollReveal>
                  ))}
                </div>
              </div>
            </ScrollReveal>

            <div className="space-y-4">
              {[
                {
                  label: 'TARGET MARKET',
                  title: 'Mid-Market PE Firms',
                  detail: '$100M-$1B AUM unable to afford tier-1 consulting',
                },
                {
                  label: 'PILOT TIMELINE',
                  title: '14 Days',
                  detail: 'Initial customer validation to production deployment',
                },
                {
                  label: 'ROI PER ENGAGEMENT',
                  title: '$160K Savings',
                  detail: 'Direct cost reduction vs. McKinsey/BCG baseline',
                },
              ].map((card, idx) => (
                <ScrollReveal key={idx} animation="fadeRight" delay={idx * 0.15}>
                  <MagneticElement strength={0.08}>
                    <div className="group relative bg-theme-surface backdrop-blur-sm border border-theme-border p-6 md:p-8 hover:border-orange-600/40 transition-all duration-500 overflow-hidden">
                      <div className="absolute inset-0 bg-gradient-to-r from-orange-600/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                      <div className="relative z-10">
                        <p className="text-[10px] font-mono text-theme-text-faint mb-2">{card.label}</p>
                        <p className="text-xl md:text-2xl font-bold mb-1">{card.title}</p>
                        <p className="text-xs text-theme-text-muted">{card.detail}</p>
                      </div>
                    </div>
                  </MagneticElement>
                </ScrollReveal>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
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
                Human wisdom meets machine speed. Multi-agent PE diligence that
                transforms curiosity into conviction.
              </p>
            </ScrollReveal>

            <ScrollReveal animation="fadeUp" delay={0.1}>
              <h4 className="text-[10px] font-mono text-theme-text-muted mb-4 tracking-wider">INFRASTRUCTURE</h4>
              <ul className="space-y-2.5 text-xs text-theme-text-faint">
                {['TinyFish Browser Automation', 'Stateful Execution Engine', 'Multi-Agent Coordination', 'Enterprise Authentication'].map(
                  (item) => (
                    <li key={item} className="hover:text-theme-text-secondary transition-colors duration-200 cursor-default">
                      {item}
                    </li>
                  )
                )}
              </ul>
            </ScrollReveal>

            <ScrollReveal animation="fadeUp" delay={0.2}>
              <h4 className="text-[10px] font-mono text-theme-text-muted mb-4 tracking-wider">CAPABILITIES</h4>
              <ul className="space-y-2.5 text-xs text-theme-text-faint">
                {['Live System Integration', 'Real-Time Analysis', 'Board-Ready Deliverables', 'Compliance Tracking'].map(
                  (item) => (
                    <li key={item} className="hover:text-theme-text-secondary transition-colors duration-200 cursor-default">
                      {item}
                    </li>
                  )
                )}
              </ul>
            </ScrollReveal>
          </div>

          <ScrollReveal animation="fade" delay={0.3}>
            <div className="mt-12 pt-8 border-t border-theme-border-subtle text-center">
              <p className="text-xs text-theme-text-faint font-mono">
                &copy; 2026 KEEN — BACKED BY TINYFISH ACCELERATOR
              </p>
            </div>
          </ScrollReveal>
        </div>
      </footer>

      {/* Request Access Modal */}
      {requestAccessOpen && (
        <RequestAccessModal onClose={() => setRequestAccessOpen(false)} />
      )}

      {/* Auth Modal */}
      {authModalOpen && (
        <AuthModal
          initialTab={authModalTab}
          onClose={() => setAuthModalOpen(false)}
          onSuccess={() => {
            setAuthModalOpen(false);
            setView('dashboard');
          }}
        />
      )}
    </div>
  );
}

export default App;
