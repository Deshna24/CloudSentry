import {
  AlertTriangle,
  Award,
  CheckCircle2,
  ChevronRight,
  Clock,
  Crosshair,
  Database,
  ExternalLink,
  Flame,
  Globe,
  Lock,
  Play,
  RotateCcw,
  Server,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Terminal,
  Trophy,
  Waves,
  Zap,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import { ErrorNote, PageHeader, Panel, SeverityBadge, ActionBadge, Spinner } from '../components/ui';
import { usePolling } from '../hooks';
import { fmtNum, fmtTime } from '../lib/theme';

const ATTACKS = [
  {
    type: 'BRUTE_FORCE',
    name: 'Brute Force',
    icon: Lock,
    desc: 'Simulates repeated failed authentication attempts against login endpoints.',
    defaultEndpoint: '/login',
    samplePayload: '{"username":"admin","password":"***"}',
    threatCategory: 'Authentication Flood',
  },
  {
    type: 'RATE_ABUSE',
    name: 'Rate Abuse',
    icon: Waves,
    desc: 'Simulates abnormal request volume against an API service exceeding thresholds.',
    defaultEndpoint: '/api',
    samplePayload: 'GET /api?filter=all [900+ req/min]',
    threatCategory: 'Denial of Service',
  },
  {
    type: 'SQL_INJECTION',
    name: 'SQL Injection',
    icon: Database,
    desc: 'Simulates suspicious database-query payload patterns and SQL dialect escapes.',
    defaultEndpoint: '/search',
    samplePayload: "1' UNION SELECT username, password FROM users --",
    threatCategory: 'Data Exfiltration',
  },
  {
    type: 'XSS',
    name: 'XSS',
    icon: Flame,
    desc: 'Simulates suspicious script injection patterns into HTML/JSON input fields.',
    defaultEndpoint: '/users',
    samplePayload: '<script>alert(document.cookie)</script>',
    threatCategory: 'Client Script Injection',
  },
  {
    type: 'PATH_TRAVERSAL',
    name: 'Path Traversal',
    icon: Crosshair,
    desc: 'Simulates attempts to escape web directories and access unauthorized host file paths.',
    defaultEndpoint: '/files',
    samplePayload: '/files/../../../../etc/passwd',
    threatCategory: 'Unauthorized File Access',
  },
];

const INTENSITIES = [
  { key: 'LOW', label: 'LOW', range: '100–300 req/s', rps: 250 },
  { key: 'MEDIUM', label: 'MEDIUM', range: '300–600 req/s', rps: 500 },
  { key: 'HIGH', label: 'HIGH', range: '600–1000 req/s', rps: 850 },
  { key: 'EXTREME', label: 'EXTREME', range: '1000–1500+ req/s', rps: 1300 },
];

const ENDPOINTS = ['/login', '/users', '/search', '/api', '/files', '/admin'];
const DURATIONS = [10, 20, 30];

const STAGES = [
  { key: 'preparing', label: 'Preparing', desc: 'Preparing simulation...' },
  { key: 'traffic_spike', label: 'Traffic Spike', desc: 'Traffic increasing...' },
  { key: 'detection', label: 'Detection', desc: 'CloudSentry analysing behaviour...' },
  { key: 'classification', label: 'Classification', desc: 'Risk score calculated...' },
  { key: 'response', label: 'Response', desc: 'Automated response triggered...' },
  { key: 'contained', label: 'Contained', desc: 'Threat contained.' },
];

export default function AttackLab() {
  const { user, isAdmin } = useAuth();
  const navigate = useNavigate();

  // Attack Configuration State
  const [selectedAttack, setSelectedAttack] = useState(ATTACKS[0]);
  const [intensity, setIntensity] = useState('HIGH');
  const [endpoint, setEndpoint] = useState(ATTACKS[0].defaultEndpoint);
  const [duration, setDuration] = useState(20);

  // Simulation execution state
  const [launching, setLaunching] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [showSummaryModal, setShowSummaryModal] = useState(false);
  const [summaryData, setSummaryData] = useState(null);

  // Polling states
  const simState = usePolling(() => api.simulationStatus(), 1200);
  const progressState = usePolling(() => api.progress(), 2500);
  const missionsState = usePolling(() => api.missions(), 3000);
  const achievementsState = usePolling(() => api.achievements(), 3000);

  const activeRun = simState.data?.latest_run;
  const isSimActive = Boolean(simState.data?.active);

  // Sync selected endpoint when attack changes
  const handleSelectAttack = (att) => {
    setSelectedAttack(att);
    setEndpoint(att.defaultEndpoint);
  };

  // Watch for simulation completion to show Summary Modal
  useEffect(() => {
    if (activeRun && activeRun.status === 'complete' && activeRun.phase_index === 7) {
      if (!summaryData || summaryData.run_id !== activeRun.run_id) {
        setSummaryData(activeRun);
        setShowSummaryModal(true);
      }
    }
  }, [activeRun, summaryData]);

  const handleLaunch = async () => {
    if (!isAdmin) return;
    setLaunching(true);
    setActionError(null);
    setShowSummaryModal(false);

    try {
      const res = await api.launchSimulation({
        attack_type: selectedAttack.type,
        target_endpoint: endpoint,
        intensity,
        duration: Number(duration),
      });
      await simState.refresh();
      await progressState.refresh();
    } catch (err) {
      setActionError(err.message || 'Failed to launch simulation');
    } finally {
      setLaunching(false);
    }
  };

  const handleReset = async () => {
    setActionError(null);
    try {
      await api.resetSimulation();
      setShowSummaryModal(false);
      setSummaryData(null);
      await Promise.all([
        simState.refresh(),
        progressState.refresh(),
        missionsState.refresh(),
        achievementsState.refresh(),
      ]);
    } catch (err) {
      setActionError(err.message || 'Failed to reset lab');
    }
  };

  // Compute live stage index
  const currentStageIndex = useMemo(() => {
    if (!isSimActive && activeRun?.status === 'complete') return 6;
    if (!isSimActive) return 0;
    const p = activeRun?.phase_index || simState.data?.phase || 1;
    return Math.min(6, Math.max(1, p));
  }, [isSimActive, activeRun, simState.data]);

  const liveRiskScore = isSimActive ? activeRun?.risk_score || 85 : activeRun?.risk_score || 0;
  const liveRps = isSimActive ? simState.data?.current_rps || 640 : 0;
  const liveRequests = activeRun?.requests_generated || (isSimActive ? liveRps * 2 : 0);

  // Status computation
  const statusBadge = useMemo(() => {
    if (!isSimActive && activeRun?.status === 'complete') {
      return {
        label: 'CONTAINED',
        color: 'text-ok bg-ok/10 border-ok/30',
        dot: 'bg-ok',
        icon: ShieldCheck,
      };
    }
    if (isSimActive) {
      if (currentStageIndex >= 5) {
        return {
          label: 'CRITICAL',
          color: 'text-crit bg-crit/10 border-crit/40',
          dot: 'bg-crit animate-ping',
          icon: AlertTriangle,
        };
      }
      return {
        label: 'ANALYSING',
        color: 'text-warn bg-warn/10 border-warn/30',
        dot: 'bg-warn animate-pulse',
        icon: Zap,
      };
    }
    return {
      label: 'STANDBY',
      color: 'text-dim bg-line/40 border-line',
      dot: 'bg-dim',
      icon: Shield,
    };
  }, [isSimActive, activeRun, currentStageIndex]);

  const userProgress = progressState.data || {
    xp: 720,
    level: 4,
    title: 'CLOUD DEFENDER',
    next_level_xp: 1000,
    progress_percent: 72,
  };

  return (
    <div className="space-y-6">
      {/* Header & Command Banner */}
      <div className="flex flex-col justify-between gap-4 border-b border-line pb-5 sm:flex-row sm:items-center">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-brand/15 text-brand">
              <Zap className="h-4 w-4" />
            </span>
            <h1 className="text-xl font-semibold tracking-tight text-ink">ATTACK LAB</h1>
            <span className="rounded-full border border-brand/30 bg-brand/10 px-2.5 py-0.5 text-[11px] font-medium text-brand">
              Controlled Security Simulation
            </span>
          </div>
          <p className="mt-1 text-sm text-mute">
            Configure synthetic API attacks, observe real-time automated detection and containment, and earn Defender XP.
          </p>
        </div>

        {/* User XP & Level Card */}
        <div className="flex items-center gap-4 rounded-lg border border-line bg-panel p-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-brand/30 bg-brand/10 text-brand">
            <Trophy className="h-5 w-5" />
          </div>
          <div className="min-w-[130px]">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-brand">LEVEL 0{userProgress.level}</span>
              <span className="font-mono text-dim">{userProgress.xp} / {userProgress.next_level_xp} XP</span>
            </div>
            <p className="truncate text-xs font-medium text-ink">{userProgress.title}</p>
            <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-line">
              <div
                className="h-full rounded-full bg-brand transition-all duration-500"
                style={{ width: `${userProgress.progress_percent || 72}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      <ErrorNote error={actionError} />

      {/* Main Grid: Attack Configuration & Live Telemetry */}
      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left Column: Attack Configuration (7 Cols) */}
        <div className="space-y-6 lg:col-span-7">
          {/* Step 1: Choose Attack */}
          <Panel title="1. Choose Attack Simulation" subtitle="All telemetry remains 100% synthetic inside CloudSentry">
            <div className="grid gap-3 p-4 sm:grid-cols-2">
              {ATTACKS.map((att) => {
                const Icon = att.icon;
                const isSelected = selectedAttack.type === att.type;
                return (
                  <button
                    key={att.type}
                    type="button"
                    onClick={() => handleSelectAttack(att)}
                    disabled={isSimActive}
                    className={`flex flex-col text-left rounded-lg border p-3.5 transition-all ${
                      isSelected
                        ? 'border-brand bg-brand/10 shadow-[0_0_15px_rgba(90,176,255,0.15)] ring-1 ring-brand/50'
                        : 'border-line bg-bg-soft/70 hover:border-dim hover:bg-raised'
                    } ${isSimActive ? 'opacity-60 cursor-not-allowed' : ''}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span
                          className={`flex h-7 w-7 items-center justify-center rounded-md ${
                            isSelected ? 'bg-brand text-bg' : 'bg-line/60 text-mute'
                          }`}
                        >
                          <Icon className="h-3.5 w-3.5" />
                        </span>
                        <span className="text-sm font-semibold text-ink">{att.name}</span>
                      </div>
                      {isSelected && <span className="h-2 w-2 rounded-full bg-brand pulse-dot" />}
                    </div>
                    <p className="mt-2 text-xs leading-relaxed text-mute">{att.desc}</p>
                    <div className="mt-2.5 flex items-center justify-between border-t border-line/60 pt-2 text-[11px] text-dim font-mono">
                      <span>Default: {att.defaultEndpoint}</span>
                      <span className="text-brand/80">{att.threatCategory}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </Panel>

          {/* Step 2: Configure Intensity, Target Endpoint, Duration */}
          <Panel title="2. Attack Configuration" subtitle="Fine-tune simulation parameters">
            <div className="space-y-5 p-4 text-sm">
              {/* Intensity Slider */}
              <div>
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-mute">Attack Intensity</label>
                  <span className="font-mono text-xs font-semibold text-brand">
                    {intensity} ({INTENSITIES.find((i) => i.key === intensity)?.range})
                  </span>
                </div>
                <div className="mt-2 grid grid-cols-4 gap-2">
                  {INTENSITIES.map((lvl) => (
                    <button
                      key={lvl.key}
                      type="button"
                      disabled={isSimActive}
                      onClick={() => setIntensity(lvl.key)}
                      className={`rounded-md border py-2 text-center text-xs font-medium transition-colors ${
                        intensity === lvl.key
                          ? 'border-brand bg-brand/15 text-brand ring-1 ring-brand/40'
                          : 'border-line bg-bg-soft text-mute hover:border-dim hover:text-ink'
                      }`}
                    >
                      {lvl.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Endpoint & Duration */}
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-medium text-mute" htmlFor="target-endpoint">
                    Target Endpoint
                  </label>
                  <select
                    id="target-endpoint"
                    disabled={isSimActive}
                    className="field mono mt-1.5"
                    value={endpoint}
                    onChange={(e) => setEndpoint(e.target.value)}
                  >
                    {ENDPOINTS.map((ep) => (
                      <option key={ep} value={ep}>
                        {ep}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-mute">Attack Duration</label>
                  <div className="mt-1.5 flex gap-2">
                    {DURATIONS.map((sec) => (
                      <button
                        key={sec}
                        type="button"
                        disabled={isSimActive}
                        onClick={() => setDuration(sec)}
                        className={`flex-1 rounded-md border py-2 text-xs font-medium transition-colors ${
                          duration === sec
                            ? 'border-brand bg-brand/15 text-brand ring-1 ring-brand/40'
                            : 'border-line bg-bg-soft text-mute hover:border-dim hover:text-ink'
                        }`}
                      >
                        {sec} sec
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center gap-3 border-t border-line pt-4">
                {isAdmin ? (
                  <>
                    <button
                      type="button"
                      disabled={isSimActive || launching}
                      onClick={handleLaunch}
                      className="btn-primary !px-5 !py-2.5 flex-1 shadow-lg shadow-brand/20"
                    >
                      {launching || isSimActive ? (
                        <>
                          <Spinner className="h-4 w-4" /> Simulation in Progress...
                        </>
                      ) : (
                        <>
                          <Play className="h-4 w-4 fill-current" /> LAUNCH SIMULATION
                        </>
                      )}
                    </button>
                    <button
                      type="button"
                      disabled={launching}
                      onClick={handleReset}
                      className="btn-ghost !px-4 !py-2.5"
                    >
                      <RotateCcw className="h-4 w-4" /> RESET LAB
                    </button>
                  </>
                ) : (
                  <p className="rounded-md border border-line bg-panel p-3 text-xs text-dim">
                    Analyst accounts have read-only access. Sign in as administrator to launch simulations.
                  </p>
                )}
              </div>
            </div>
          </Panel>
        </div>

        {/* Right Column: Live Attack Panel & Attack vs Defense Split (5 Cols) */}
        <div className="space-y-6 lg:col-span-5">
          {/* Live Attack Telemetry Panel */}
          <Panel
            title="Live Attack Panel"
            subtitle={isSimActive ? 'Live telemetry stream' : 'Awaiting simulation launch'}
            action={
              <div className={`flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${statusBadge.color}`}>
                <span className={`h-2 w-2 rounded-full ${statusBadge.dot}`} />
                {statusBadge.label}
              </div>
            }
          >
            <div className="space-y-4 p-4">
              {/* Telemetry Gauge Cards */}
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-line bg-bg-soft p-3">
                  <p className="text-xs text-mute">Requests / sec</p>
                  <p className="mono mt-1 text-2xl font-bold text-ink">
                    {fmtNum(liveRps)}
                  </p>
                  <p className="mt-1 text-[11px] text-dim font-mono">
                    {isSimActive ? `Active flood on ${endpoint}` : 'Baseline ~80 req/s'}
                  </p>
                </div>
                <div className="rounded-lg border border-line bg-bg-soft p-3">
                  <p className="text-xs text-mute">Risk Score</p>
                  <p className={`mono mt-1 text-2xl font-bold ${liveRiskScore >= 80 ? 'text-crit' : liveRiskScore >= 60 ? 'text-warn' : 'text-ok'}`}>
                    {liveRiskScore} <span className="text-xs text-dim">/ 100</span>
                  </p>
                  <p className="mt-1 text-[11px] text-dim">
                    {liveRiskScore >= 80 ? 'CRITICAL - Auto Block' : liveRiskScore >= 60 ? 'HIGH - Throttle' : 'Low risk baseline'}
                  </p>
                </div>
              </div>

              {/* Progress Stage Pipeline (Requirements 5) */}
              <div className="rounded-lg border border-line bg-panel p-3.5">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-mute">Simulation Progression</p>
                <div className="space-y-2">
                  <div className="grid grid-cols-6 gap-1">
                    {STAGES.map((st, i) => {
                      const isComplete = currentStageIndex > i + 1;
                      const isCurrent = currentStageIndex === i + 1;
                      return (
                        <div key={st.key} className="flex flex-col items-center">
                          <div
                            className={`h-1.5 w-full rounded-full transition-all duration-300 ${
                              isComplete
                                ? 'bg-ok'
                                : isCurrent
                                ? 'bg-brand pulse-dot'
                                : 'bg-line'
                            }`}
                          />
                          <span
                            className={`mt-1 text-[10px] truncate max-w-[50px] ${
                              isCurrent ? 'font-semibold text-brand' : isComplete ? 'text-mute' : 'text-dim'
                            }`}
                          >
                            {st.label}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                  <p className="pt-1 text-xs text-center font-mono text-dim">
                    {isSimActive
                      ? STAGES[Math.max(0, currentStageIndex - 1)]?.desc
                      : activeRun?.status === 'complete'
                      ? 'Threat successfully contained and mitigated.'
                      : 'Idle — select attack and click Launch Simulation.'}
                  </p>
                </div>
              </div>

              {/* Attack vs Defense Split Panel (Requirement 7) */}
              <div className="rounded-lg border border-line bg-bg-soft overflow-hidden">
                <div className="grid grid-cols-2 divide-x divide-line text-xs">
                  {/* Left: Attacker */}
                  <div className="p-3.5 space-y-2 bg-crit/5">
                    <div className="flex items-center gap-1.5 text-crit font-semibold">
                      <AlertTriangle className="h-3.5 w-3.5" /> ATTACKER
                    </div>
                    <div>
                      <span className="text-dim">Attack: </span>
                      <span className="font-semibold text-ink">{isSimActive || activeRun ? activeRun?.attack_type || selectedAttack.type : selectedAttack.type}</span>
                    </div>
                    <div>
                      <span className="text-dim">Target: </span>
                      <span className="font-mono text-ink">{isSimActive || activeRun ? activeRun?.target_endpoint || endpoint : endpoint}</span>
                    </div>
                    <div>
                      <span className="text-dim">Intensity: </span>
                      <span className="font-mono text-ink">{intensity}</span>
                    </div>
                    <div>
                      <span className="text-dim">Requests: </span>
                      <span className="font-mono text-ink">{fmtNum(liveRequests)}</span>
                    </div>
                  </div>

                  {/* Right: CloudSentry */}
                  <div className="p-3.5 space-y-2 bg-ok/5">
                    <div className="flex items-center gap-1.5 text-ok font-semibold">
                      <Shield className="h-3.5 w-3.5" /> CLOUDSENTRY
                    </div>
                    <div>
                      <span className="text-dim">Detection: </span>
                      <span className="font-semibold text-ok">{isSimActive || activeRun ? 'Active ✓' : 'Standby'}</span>
                    </div>
                    <div>
                      <span className="text-dim">Risk Score: </span>
                      <span className="font-mono font-bold text-ink">{liveRiskScore} / 100</span>
                    </div>
                    <div>
                      <span className="text-dim">Threat: </span>
                      <span className="font-semibold text-ink">{isSimActive || activeRun ? activeRun?.threat_type || selectedAttack.name : 'Normal'}</span>
                    </div>
                    <div>
                      <span className="text-dim">Action: </span>
                      <span className={`font-mono font-bold ${activeRun?.action === 'BLOCK' ? 'text-crit' : activeRun?.action === 'THROTTLE' ? 'text-warn' : 'text-ok'}`}>
                        {activeRun?.action || (isSimActive ? 'ANALYSING' : 'ALLOW')}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Panel>
        </div>
      </div>

      {/* Gamification Sections: Missions & Achievements */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Missions Section (Requirement 9) */}
        <Panel
          title="Defender Missions"
          subtitle="Complete interactive objectives to earn XP and level up"
          action={
            <span className="text-xs font-mono text-dim">
              {missionsState.data?.filter((m) => m.completed).length || 0} / 4 Completed
            </span>
          }
        >
          <div className="divide-y divide-line">
            {(missionsState.data || []).map((m) => (
              <div key={m.id} className="flex items-center justify-between gap-4 p-4 hover:bg-raised/40 transition-colors">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-semibold text-brand">{m.code}</span>
                    <span className="text-sm font-semibold text-ink">{m.title}</span>
                    {m.completed && (
                      <span className="rounded-full bg-ok/10 border border-ok/30 px-2 py-0.2 text-[10px] font-semibold text-ok">
                        COMPLETED
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-mute">{m.goal}</p>
                  <div className="mt-2 flex items-center gap-3">
                    <div className="h-1.5 flex-1 max-w-[200px] overflow-hidden rounded-full bg-line">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          m.completed ? 'bg-ok' : 'bg-brand'
                        }`}
                        style={{ width: `${m.progress_percent || 0}%` }}
                      />
                    </div>
                    <span className="font-mono text-[11px] text-dim">{m.progress_percent}%</span>
                  </div>
                </div>
                <div className="text-right">
                  <span className="rounded-md border border-brand/20 bg-brand/10 px-2.5 py-1 font-mono text-xs font-semibold text-brand">
                    +{m.reward_xp} XP
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        {/* Achievements Section (Requirement 10) */}
        <Panel
          title="Achievement Vault"
          subtitle="Special honors unlocked across the cyber simulation platform"
          action={
            <span className="text-xs font-mono text-dim">
              {achievementsState.data?.filter((a) => a.unlocked).length || 0} / 6 Unlocked
            </span>
          }
        >
          <div className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-3">
            {(achievementsState.data || []).map((ach) => (
              <div
                key={ach.key}
                className={`flex flex-col items-center rounded-lg border p-3 text-center transition-all ${
                  ach.unlocked
                    ? 'border-brand/40 bg-brand/10 shadow-[0_0_12px_rgba(90,176,255,0.1)]'
                    : 'border-line/60 bg-bg-soft/50 opacity-40'
                }`}
              >
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-full border ${
                    ach.unlocked
                      ? 'border-brand bg-brand/20 text-brand'
                      : 'border-line bg-line/40 text-dim'
                  }`}
                >
                  <Award className="h-5 w-5" />
                </div>
                <p className="mt-2 text-xs font-semibold text-ink">{ach.title}</p>
                <p className="mt-1 text-[11px] text-mute line-clamp-2">{ach.description}</p>
                <span className="mt-2 font-mono text-[10px] text-brand">+{ach.xp_reward} XP</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {/* Score Summary Modal (Requirement 11) */}
      {showSummaryModal && summaryData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border border-brand/50 bg-panel p-6 shadow-2xl shadow-brand/10 animate-in fade-in zoom-in-95 duration-200">
            <div className="text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-ok/40 bg-ok/10 text-ok">
                <ShieldCheck className="h-6 w-6" />
              </div>
              <h2 className="mt-3 text-lg font-bold tracking-tight text-ink">SIMULATION COMPLETE</h2>
              <p className="text-xs font-semibold uppercase tracking-wider text-ok">🛡 THREAT CONTAINED</p>
            </div>

            {/* Verification Checklist */}
            <ul className="mt-4 space-y-1.5 rounded-lg border border-line bg-bg-soft p-3 text-xs text-mute">
              <li className="flex items-center justify-between">
                <span>Threat detected</span>
                <span className="text-ok font-bold">✓</span>
              </li>
              <li className="flex items-center justify-between">
                <span>Risk calculated</span>
                <span className="text-ok font-bold">✓</span>
              </li>
              <li className="flex items-center justify-between">
                <span>Automated response</span>
                <span className="text-ok font-bold">✓</span>
              </li>
              <li className="flex items-center justify-between">
                <span>Incident logged</span>
                <span className="text-ok font-bold">✓</span>
              </li>
              <li className="flex items-center justify-between">
                <span>Service available</span>
                <span className="text-ok font-bold">✓</span>
              </li>
            </ul>

            {/* Metrics Breakdown */}
            <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-md border border-line bg-bg-soft p-2.5">
                <p className="text-dim">Risk Score</p>
                <p className="mono text-lg font-bold text-crit">{summaryData.risk_score} / 100</p>
              </div>
              <div className="rounded-md border border-line bg-bg-soft p-2.5">
                <p className="text-dim">Requests Analysed</p>
                <p className="mono text-lg font-bold text-ink">{fmtNum(summaryData.requests_generated || 1284)}</p>
              </div>
            </div>

            {/* XP Award Banner */}
            <div className="mt-4 flex items-center justify-between rounded-lg border border-brand/40 bg-brand/15 p-3">
              <div className="flex items-center gap-2">
                <Trophy className="h-4 w-4 text-brand" />
                <span className="text-xs font-semibold text-ink">XP EARNED</span>
              </div>
              <span className="font-mono text-sm font-bold text-brand">+{summaryData.xp_earned || 200} XP</span>
            </div>

            {/* Modal Actions */}
            <div className="mt-5 flex gap-3">
              <button
                type="button"
                onClick={() => setShowSummaryModal(false)}
                className="btn-ghost flex-1 !py-2 text-xs"
              >
                RUN AGAIN
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowSummaryModal(false);
                  navigate('/threats');
                }}
                className="btn-primary flex-1 !py-2 text-xs"
              >
                VIEW INCIDENT <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
