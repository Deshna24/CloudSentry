import { Power, RotateCcw, Zap } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../api';
import { useAuth } from '../auth';
import { usePolling } from '../hooks';
import { ActionBadge, Empty, ErrorNote, Panel, PageHeader, SeverityBadge, Spinner, StatusDot, Switch, ThreatTag, chartTooltip } from '../components/ui';
import { SEVERITIES, SEVERITY_BG, SEVERITY_TEXT, THREAT_COLOR, THREAT_LABEL, fmtDuration, fmtNum, fmtTime, timeAgo } from '../lib/theme';

function Kpi({ label, value, hint, tone = 'text-ink' }) {
  return (
    <div className="bg-panel px-4 py-4">
      <p className="text-xs text-mute">{label}</p>
      <p className={`mt-1.5 text-[28px] font-semibold leading-none tracking-tight ${tone}`}>{value}</p>
      <p className="mt-2 truncate text-xs text-dim">{hint}</p>
    </div>
  );
}

function AttackPipeline({ s }) {
  const sim = s.simulation;
  const cutoff = Date.now() - 150000;
  const simThreats = s.recent_threats.filter((t) => t.source === 'simulation' && new Date(t.timestamp).getTime() > cutoff);
  const rate = simThreats.find((t) => t.threat_type === 'RATE_ABUSE') || simThreats[0];
  const rps = sim.active ? sim.current_rps : s.kpis.requests_per_second;
  const steps = [
    { label: 'Traffic spike', detail: `${fmtNum(rps)} req/s`, done: rps >= 300 },
    { label: 'Threat detected', detail: s.threat_level.level !== 'LOW' ? THREAT_LABEL[simThreats[0]?.threat_type] || 'Anomaly' : 'Watching', done: s.threat_level.level !== 'LOW' },
    { label: 'Risk score rises', detail: `${s.threat_level.risk}/100`, done: s.threat_level.risk >= 60 },
    { label: 'Source identified', detail: rate?.source_ip || '-', done: simThreats.length > 0, mono: true },
    { label: 'Throttled or blocked', detail: simThreats.some((t) => t.action === 'BLOCK') ? 'Blocked' : simThreats.some((t) => t.action === 'THROTTLE') ? 'Throttled' : '-', done: simThreats.some((t) => ['BLOCK', 'THROTTLE'].includes(t.action)) },
    { label: 'Incident in feed', detail: simThreats.length ? `${simThreats.length}+ new` : '-', done: simThreats.length > 0 },
  ];
  return (
    <ol className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
      {steps.map((st, i) => (
        <li key={st.label} className="relative">
          <div className="flex items-center gap-2">
            <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${st.done ? 'bg-crit' : 'bg-line'}`} />
            <span className={`h-px flex-1 ${i === steps.length - 1 ? 'hidden' : st.done ? 'bg-crit/60' : 'bg-line'}`} />
          </div>
          <p className={`mt-2 text-sm font-medium ${st.done ? 'text-ink' : 'text-dim'}`}>{st.label}</p>
          <p className={`mt-0.5 truncate text-xs ${st.done ? 'text-mute' : 'text-dim'} ${st.mono ? 'font-mono' : ''}`}>{st.detail}</p>
        </li>
      ))}
    </ol>
  );
}

function ThreatLevel({ level }) {
  const { level: name, risk } = level;
  const bands = [
    { w: 30, c: 'bg-ok/40' },
    { w: 30, c: 'bg-warn/40' },
    { w: 20, c: 'bg-hot/40' },
    { w: 20, c: 'bg-crit/50' },
  ];
  return (
    <Panel title="Threat level" subtitle="Highest risk in the last 2 minutes of live traffic">
      <div className="p-5">
        <div className="flex items-baseline justify-between">
          <p className={`text-3xl font-semibold tracking-tight ${SEVERITY_TEXT[name]}`}>{name}</p>
          <p className="text-sm text-mute"><span className="text-xl font-semibold text-ink">{risk}</span> / 100</p>
        </div>
        <div className="relative mt-5">
          <div className="flex h-2 gap-0.5 overflow-hidden rounded-full">
            {bands.map((b, i) => <div key={i} className={b.c} style={{ width: `${b.w}%` }} />)}
          </div>
          <div className="absolute -top-1.5 h-5 w-0.5 rounded bg-ink transition-all duration-500" style={{ left: `calc(${Math.min(risk, 99)}% )` }} />
        </div>
        <div className="mt-2 flex justify-between text-xs text-dim">
          {SEVERITIES.map((v) => <span key={v} className={v === name ? SEVERITY_TEXT[v] : ''}>{v.toLowerCase()}</span>)}
        </div>
      </div>
    </Panel>
  );
}

function SystemHealth({ health, isAdmin, onToggle, busy }) {
  const h = health.data;
  const first = h?.instances?.[0];
  return (
    <Panel
      title="System health"
      action={isAdmin && first && (
        <button className="btn-ghost !py-1 text-xs" disabled={busy} onClick={() => onToggle(first)}>
          <Power className="h-3.5 w-3.5" /> {first.forced_down ? `Recover ${first.id}` : `Fail ${first.id}`}
        </button>
      )}
    >
      {!h ? <Spinner /> : (
        <ul className="divide-y divide-line">
          {[{ name: 'Load balancer', ...h.load_balancer }, ...h.instances.map((i) => ({ name: i.id, mono: true, ...i })), { name: 'Database', ...h.database }].map((r) => (
            <li key={r.name} className="flex items-center gap-3 px-4 py-3">
              <StatusDot status={r.status} pulse />
              <div className="min-w-0 flex-1">
                <p className={`text-sm font-medium ${r.mono ? 'font-mono' : ''}`}>{r.name}</p>
                <p className="truncate text-xs text-dim">{r.detail}</p>
              </div>
              <span className={`text-xs font-medium ${r.status === 'HEALTHY' ? 'text-ok' : r.status === 'WARNING' ? 'text-warn' : 'text-crit'}`}>
                {r.status === 'HEALTHY' ? 'Healthy' : r.status === 'WARNING' ? 'Warning' : 'Down'}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

export default function Dashboard() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const summary = usePolling(() => api.summary(), 2000);
  const health = usePolling(() => api.health(), 2500);
  const [live, setLive] = useState(false);
  const [busy, setBusy] = useState('');
  const [actionError, setActionError] = useState(null);
  const s = summary.data;
  const simActive = !!s?.simulation?.active;

  useEffect(() => {
    if (!live) return undefined;
    const tick = () => api.normalTraffic().catch(() => {});
    tick();
    const id = setInterval(tick, 2000);
    return () => clearInterval(id);
  }, [live]);

  const act = async (name, fn) => {
    setBusy(name);
    setActionError(null);
    try {
      await fn();
      await Promise.all([summary.refresh(), health.refresh()]);
    } catch (e) {
      setActionError(e);
    } finally {
      setBusy('');
    }
  };

  const chartData = useMemo(
    () => (s?.timeseries || []).map((t) => ({
      time: fmtTime(t.timestamp),
      allowed: Math.max(t.rps - t.blocked - t.throttled, 0),
      throttled: t.throttled,
      blocked: t.blocked,
    })),
    [s],
  );
  const dist = useMemo(() => (s?.threat_distribution || []).map((d) => ({ ...d, name: THREAT_LABEL[d.type] || d.type })), [s]);
  const distTotal = dist.reduce((a, d) => a + d.count, 0);

  if (!s) {
    return summary.error ? <ErrorNote error={summary.error} onRetry={summary.refresh} /> : <Spinner label="Loading dashboard" />;
  }
  const k = s.kpis;
  const idle = k.rps_age_seconds === null || k.rps_age_seconds > 15;

  const gam = s?.gamification || {
    level: 4,
    title: 'CLOUD DEFENDER',
    xp: 720,
    next_level_xp: 1000,
    progress_percent: 72,
  };

  return (
    <>
      <div className="mb-4 flex flex-col justify-between gap-4 rounded-xl border border-line bg-panel p-4 sm:flex-row sm:items-center">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-ok pulse-dot" />
            <h1 className="text-xl font-bold tracking-tight text-ink">CLOUDSENTRY</h1>
            <span className="rounded-full border border-line bg-raised px-2.5 py-0.5 text-xs font-semibold text-ok">
              ● OPERATIONAL
            </span>
          </div>
          <p className="mt-0.5 text-xs text-mute">Cloud Security Command Center &mdash; Real-time API telemetry, anomaly scoring, and automated containment.</p>
        </div>

        {/* Security Rating Card */}
        <div className="flex items-center gap-4 rounded-lg border border-line bg-bg-soft px-4 py-2.5">
          <div>
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-brand">SECURITY RATING: LEVEL 0{gam.level}</span>
              <span className="font-mono text-dim">{gam.xp} / {gam.next_level_xp} XP</span>
            </div>
            <p className="text-xs font-medium text-ink">{gam.title}</p>
            <div className="mt-1.5 h-1.5 w-44 overflow-hidden rounded-full bg-line">
              <div
                className="h-full rounded-full bg-brand transition-all duration-500"
                style={{ width: `${gam.progress_percent || 72}%` }}
              />
            </div>
          </div>
          <Link to="/attack-lab" className="btn-primary !py-1.5 text-xs">
            <Zap className="h-3.5 w-3.5 fill-current" /> Attack Lab
          </Link>
        </div>
      </div>

      <PageHeader title="Security dashboard" description="Live view of API traffic, detected threats and the automated response.">
        {isAdmin ? (
          <>
            <label className="flex items-center gap-2 rounded-md border border-line px-3 py-1.5 text-sm text-mute">
              <Switch checked={live} onChange={setLive} label="Generate normal traffic" /> Normal traffic
            </label>
            <button className="btn-ghost" disabled={!!busy} onClick={() => act('reset', async () => { setLive(false); await api.resetSimulation(); })}>
              <RotateCcw className="h-4 w-4" /> Reset simulation
            </button>
            <button className="btn-danger" disabled={simActive || !!busy} onClick={() => act('attack', () => api.attack('full'))}>
              <Zap className="h-4 w-4" /> {simActive ? 'Attack running' : 'Simulate attack'}
            </button>
          </>
        ) : (
          <span className="rounded-md border border-line px-3 py-1.5 text-sm text-dim">Read-only access (analyst)</span>
        )}
      </PageHeader>

      <ErrorNote error={actionError || summary.error} onRetry={summary.refresh} />

      {(simActive || s.threat_level.level !== 'LOW') && (
        <section className={`mb-4 rounded-lg border p-4 ${simActive ? 'border-crit/50 bg-crit/10' : 'border-line bg-panel'}`}>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <span className={`h-2.5 w-2.5 rounded-full ${simActive ? 'pulse-dot bg-crit' : 'bg-dim'}`} />
              <p className="text-sm font-medium">
                {simActive ? `Attack simulation running - phase ${s.simulation.phase} of ${s.simulation.phases_total}, ${fmtNum(s.simulation.current_rps)} req/s` : 'Recent attack activity'}
              </p>
            </div>
            {simActive && (
              <div className="flex gap-1" aria-hidden>
                {Array.from({ length: s.simulation.phases_total }).map((_, i) => (
                  <span key={i} className={`h-1.5 w-8 rounded-full ${i < s.simulation.phase ? 'bg-crit' : 'bg-line'}`} />
                ))}
              </div>
            )}
          </div>
          <AttackPipeline s={s} />
        </section>
      )}

      <div className="mb-4 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line bg-line md:grid-cols-3 xl:grid-cols-6">
        <Kpi label="Requests / sec" value={fmtNum(k.requests_per_second)} hint={idle ? 'idle - turn on normal traffic' : 'live'} tone={k.requests_per_second >= 300 && !idle ? 'text-crit' : 'text-ink'} />
        <Kpi label="Active users" value={fmtNum(k.active_users)} hint="unique sources, last hour" />
        <Kpi label="Threats detected" value={fmtNum(k.threats_detected)} hint="last 24 hours" tone="text-hot" />
        <Kpi label="Requests blocked" value={fmtNum(k.requests_blocked)} hint="last 24 hours" tone="text-crit" />
        <Kpi label="Requests throttled" value={fmtNum(k.requests_throttled)} hint="last 24 hours" tone="text-warn" />
        <Kpi label="API uptime" value={fmtDuration(k.uptime_seconds)} hint="since this instance started" />
      </div>

      <div className="mb-4 grid gap-4 lg:grid-cols-3">
        <Panel
          className="lg:col-span-2"
          title="Requests per second"
          subtitle="Allowed, throttled and blocked traffic, most recent 60 samples"
          action={
            <span className={`flex items-center gap-2 text-xs font-medium ${simActive ? 'text-crit' : idle ? 'text-dim' : 'text-ok'}`}>
              <span className={`h-2 w-2 rounded-full ${simActive ? 'pulse-dot bg-crit' : idle ? 'bg-dim' : 'pulse-dot bg-ok'}`} />
              {simActive ? 'Under attack' : idle ? 'Idle' : 'Live'}
            </span>
          }
          bodyClass="p-4 pt-5"
        >
          <div className="h-72 w-full">
            <ResponsiveContainer>
              <AreaChart data={chartData} margin={{ top: 4, right: 8, left: -12, bottom: 0 }}>
                <defs>
                  <linearGradient id="gAllowed" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#5ab0ff" stopOpacity={0.5} /><stop offset="100%" stopColor="#5ab0ff" stopOpacity={0.03} /></linearGradient>
                  <linearGradient id="gThrottled" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#fbbf24" stopOpacity={0.65} /><stop offset="100%" stopColor="#fbbf24" stopOpacity={0.05} /></linearGradient>
                  <linearGradient id="gBlocked" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#f87171" stopOpacity={0.75} /><stop offset="100%" stopColor="#f87171" stopOpacity={0.05} /></linearGradient>
                </defs>
                <CartesianGrid stroke="#233250" strokeDasharray="3 6" vertical={false} />
                <XAxis dataKey="time" tick={{ fill: '#5f708c', fontSize: 11 }} tickLine={false} axisLine={false} minTickGap={48} />
                <YAxis tick={{ fill: '#5f708c', fontSize: 11 }} tickLine={false} axisLine={false} width={52} />
                <Tooltip {...chartTooltip} formatter={(v, n) => [`${v} req/s`, n]} />
                <Area type="monotone" dataKey="allowed" name="Allowed" stackId="1" stroke="#5ab0ff" strokeWidth={2} fill="url(#gAllowed)" isAnimationActive={false} />
                <Area type="monotone" dataKey="throttled" name="Throttled" stackId="1" stroke="#fbbf24" strokeWidth={2} fill="url(#gThrottled)" isAnimationActive={false} />
                <Area type="monotone" dataKey="blocked" name="Blocked" stackId="1" stroke="#f87171" strokeWidth={2} fill="url(#gBlocked)" isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 flex flex-wrap gap-5 pl-3 text-xs text-mute">
            {[['Allowed', '#5ab0ff'], ['Throttled', '#fbbf24'], ['Blocked', '#f87171']].map(([n, c]) => (
              <span key={n} className="flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{ background: c }} />{n}</span>
            ))}
          </div>
        </Panel>

        <div className="flex flex-col gap-4">
          <ThreatLevel level={s.threat_level} />
          <SystemHealth health={health} isAdmin={isAdmin} busy={!!busy}
            onToggle={(inst) => act('fail', () => api.instanceFailure(inst.id, !inst.forced_down))} />
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel className="lg:col-span-2" title="Threat feed" subtitle="Most recent detections, select one for details"
          action={<Link to="/threats" className="text-sm text-brand hover:underline">View all</Link>}>
          {s.recent_threats.length === 0 ? (
            <Empty title="No threats detected" hint="Traffic looks normal. Run an attack simulation to see detections appear here." />
          ) : (
            <ul className="divide-y divide-line">
              {s.recent_threats.map((t) => (
                <li key={t.id}>
                  <button onClick={() => navigate(`/threats/${t.threat_id}`)}
                    className="flex w-full flex-wrap items-center gap-x-4 gap-y-1.5 px-4 py-3 text-left transition-colors hover:bg-raised">
                    <SeverityBadge value={t.severity} />
                    <div className="min-w-[10rem] flex-1">
                      <ThreatTag type={t.threat_type} />
                      <p className="mono mt-0.5 truncate text-xs text-dim">{t.source_ip} &middot; {t.method} {t.endpoint}</p>
                    </div>
                    <span className="mono text-sm text-mute">risk {t.risk_score}</span>
                    <ActionBadge value={t.action} />
                    <span className="w-16 text-right text-xs text-dim">{timeAgo(t.timestamp)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Threat distribution" subtitle="Last 24 hours" bodyClass="p-4">
          {distTotal === 0 ? <Empty title="No data yet" /> : (
            <>
              <div className="relative mx-auto h-48 w-48">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie data={dist} dataKey="count" nameKey="name" innerRadius={58} outerRadius={84} paddingAngle={2} stroke="none" isAnimationActive={false}>
                      {dist.map((d) => <Cell key={d.type} fill={THREAT_COLOR[d.type]} />)}
                    </Pie>
                    <Tooltip {...chartTooltip} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-2xl font-semibold">{fmtNum(distTotal)}</span>
                  <span className="text-xs text-dim">requests</span>
                </div>
              </div>
              <ul className="mt-4 space-y-2">
                {dist.map((d) => (
                  <li key={d.type} className="flex items-center gap-3 text-sm">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: THREAT_COLOR[d.type] }} />
                    <span className="flex-1 text-mute">{d.name}</span>
                    <span className="font-medium">{fmtNum(d.count)}</span>
                    <span className="w-12 text-right text-xs text-dim">{((100 * d.count) / distTotal).toFixed(1)}%</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Panel>
      </div>
    </>
  );
}
