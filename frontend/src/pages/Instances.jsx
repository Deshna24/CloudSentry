import {
  ArrowDown,
  ArrowRight,
  Award,
  CheckCircle2,
  Database,
  Globe,
  Network,
  Power,
  RotateCcw,
  Server,
  Trophy,
  Zap,
} from 'lucide-react';
import { useState } from 'react';
import { api } from '../api';
import { useAuth } from '../auth';
import { ErrorNote, PageHeader, Panel, Spinner, StatusDot, StatusText } from '../components/ui';
import { usePolling } from '../hooks';
import { STATUS, timeAgo } from '../lib/theme';

function Node({ icon: Icon, title, status, detail, children }) {
  const s = STATUS[status] || STATUS.DOWN;
  return (
    <div className={`panel min-w-0 flex-1 p-4 ${status === 'DOWN' ? '!border-crit/50 bg-crit/5' : ''}`}>
      <div className="flex items-center gap-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-md bg-raised">
          <Icon className={`h-4 w-4 ${s.text}`} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{title}</p>
          <div className="mt-0.5 flex items-center gap-2">
            <StatusDot status={status} pulse />
            <StatusText status={status} />
          </div>
        </div>
      </div>
      <p className="mt-3 text-xs text-dim">{detail}</p>
      {children}
    </div>
  );
}

const Arrow = () => (
  <div className="flex items-center justify-center text-dim">
    <ArrowRight className="hidden h-5 w-5 md:block" />
    <ArrowDown className="h-5 w-5 md:hidden" />
  </div>
);

export default function Instances() {
  const { isAdmin } = useAuth();
  const { data, error, refresh } = usePolling(() => api.instances(), 2000);
  const [busy, setBusy] = useState('');
  const [actionError, setActionError] = useState(null);
  const [rewardBanner, setRewardBanner] = useState(null);

  const toggle = async (inst) => {
    setBusy(inst.id);
    setActionError(null);
    try {
      const res = await api.instanceFailure(inst.id, !inst.forced_down);
      if (!inst.forced_down && res?.gamification) {
        setRewardBanner({
          xp: res.gamification.xp_earned || 300,
          achievement: 'HIGH AVAILABILITY',
        });
      }
      await refresh();
    } catch (e) {
      setActionError(e);
    } finally {
      setBusy('');
    }
  };

  const handleChallengeFailover = async (shouldFail) => {
    setBusy('challenge');
    setActionError(null);
    try {
      const res = await api.instanceFailure('API-01', shouldFail);
      if (shouldFail && res?.gamification) {
        setRewardBanner({
          xp: res.gamification.xp_earned || 300,
          achievement: 'HIGH AVAILABILITY',
        });
      }
      await refresh();
    } catch (e) {
      setActionError(e);
    } finally {
      setBusy('');
    }
  };

  const api01 = data?.instances.find((i) => i.id === 'API-01');
  const api02 = data?.instances.find((i) => i.id === 'API-02');
  const isApi01Down = api01?.forced_down || api01?.status === 'DOWN';
  const logical = data?.instances.some((i) => i.mode === 'logical');

  return (
    <>
      <PageHeader
        title="Instances"
        description="Backend instances behind the load balancer. Fail one to watch traffic carry on through the other."
      />
      <ErrorNote error={error || actionError} onRetry={refresh} />

      {rewardBanner && (
        <div className="mb-4 flex items-center justify-between rounded-lg border border-brand/40 bg-brand/10 p-3.5 text-sm">
          <div className="flex items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand/20 text-brand">
              <Trophy className="h-4 w-4" />
            </span>
            <div>
              <p className="font-semibold text-ink">+{rewardBanner.xp} XP AWARDED &middot; ☁️ {rewardBanner.achievement} UNLOCKED!</p>
              <p className="text-xs text-mute">API-01 failed successfully while API-02 and the Load Balancer preserved zero-downtime availability.</p>
            </div>
          </div>
          <button onClick={() => setRewardBanner(null)} className="text-xs text-mute hover:text-ink">
            Dismiss
          </button>
        </div>
      )}

      {!data ? (
        <Spinner />
      ) : (
        <div className="space-y-6">
          {/* Interactive Cloud Infrastructure Challenge (Requirement 12) */}
          <Panel
            title="☁️ Infrastructure Challenge"
            subtitle="Demonstrate fault tolerance and high availability in live cloud environments"
          >
            <div className="p-4 space-y-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {/* API-01 status */}
                <div className={`rounded-lg border p-3 ${isApi01Down ? 'border-crit/40 bg-crit/10' : 'border-line bg-bg-soft'}`}>
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-semibold">API-01</span>
                    <span className="text-sm">{isApi01Down ? '🔴' : '🟢'}</span>
                  </div>
                  <p className={`mt-1 font-mono text-xs font-bold ${isApi01Down ? 'text-crit' : 'text-ok'}`}>
                    {isApi01Down ? 'DOWN' : 'HEALTHY'}
                  </p>
                  <p className="text-[11px] text-dim">{isApi01Down ? 'Forced down by admin' : 'Serving traffic'}</p>
                </div>

                {/* API-02 status */}
                <div className="rounded-lg border border-line bg-bg-soft p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-semibold">API-02</span>
                    <span className="text-sm">🟢</span>
                  </div>
                  <p className="mt-1 font-mono text-xs font-bold text-ok">
                    {isApi01Down ? 'SERVING 100%' : 'HEALTHY'}
                  </p>
                  <p className="text-[11px] text-dim">{isApi01Down ? 'Handling all failover traffic' : 'In rotation'}</p>
                </div>

                {/* Load balancer status */}
                <div className={`rounded-lg border p-3 ${isApi01Down ? 'border-brand/40 bg-brand/10' : 'border-line bg-bg-soft'}`}>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold">Load Balancer</span>
                    <span className="text-sm">🟢</span>
                  </div>
                  <p className={`mt-1 text-xs font-bold ${isApi01Down ? 'text-brand' : 'text-ok'}`}>
                    {isApi01Down ? '⚡ FAILOVER ACTIVE' : 'OPERATIONAL'}
                  </p>
                  <p className="text-[11px] text-dim">Round-robin upstream routing</p>
                </div>

                {/* Database status */}
                <div className="rounded-lg border border-line bg-bg-soft p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold">Database</span>
                    <span className="text-sm">🟢</span>
                  </div>
                  <p className="mt-1 text-xs font-bold text-ok">CONNECTED</p>
                  <p className="text-[11px] text-dim">{data.database.latency_ms} ms latency</p>
                </div>
              </div>

              {isAdmin && (
                <div className="flex flex-wrap items-center gap-3 border-t border-line pt-3">
                  {isApi01Down ? (
                    <button
                      type="button"
                      disabled={busy === 'challenge'}
                      onClick={() => handleChallengeFailover(false)}
                      className="btn-primary !py-2 text-xs"
                    >
                      <RotateCcw className="h-3.5 w-3.5" /> RECOVER API-01 TO ROTATION
                    </button>
                  ) : (
                    <button
                      type="button"
                      disabled={busy === 'challenge'}
                      onClick={() => handleChallengeFailover(true)}
                      className="btn-danger !py-2 text-xs"
                    >
                      <Power className="h-3.5 w-3.5" /> SIMULATE INSTANCE FAILURE
                    </button>
                  )}
                  <span className="text-xs text-dim">
                    Triggers simulated failover logic. API-02 absorbs traffic with zero user disruption.
                  </span>
                </div>
              )}
            </div>
          </Panel>

          {/* Topology diagram */}
          <div className="flex flex-col items-stretch gap-3 md:flex-row md:items-center">
            <Node icon={Globe} title="Users" status="HEALTHY" detail="Browser sessions hitting the API" />
            <Arrow />
            <Node icon={Network} title="Load balancer" status={data.load_balancer.status} detail={data.load_balancer.detail} />
            <Arrow />
            <div className="flex min-w-0 flex-[1.4] flex-col gap-3">
              {data.instances.map((i) => (
                <Node key={i.id} icon={Server} title={i.id} status={i.status} detail={i.detail}>
                  <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
                    <dt className="text-dim">Last heartbeat</dt>
                    <dd className="text-right text-mute">{timeAgo(i.last_heartbeat)}</dd>
                    <dt className="text-dim">Requests, last hour</dt>
                    <dd className="text-right text-mute">
                      {(i.requests_1h || 0).toLocaleString()} ({i.share_percent}%)
                    </dd>
                    <dt className="text-dim">Mode</dt>
                    <dd className="text-right text-mute">{i.mode}</dd>
                  </dl>
                  {isAdmin && i.mode !== '-' && (
                    <button
                      className={`mt-3 w-full ${i.forced_down ? 'btn-primary' : 'btn-ghost'} !py-1.5 text-xs`}
                      disabled={busy === i.id}
                      onClick={() => toggle(i)}
                    >
                      <Power className="h-3.5 w-3.5" />{' '}
                      {i.forced_down ? `Recover ${i.id}` : `Simulate instance failure`}
                    </button>
                  )}
                </Node>
              ))}
            </div>
            <Arrow />
            <Node
              icon={Database}
              title="PostgreSQL"
              status={data.database.status}
              detail={`Query latency ${data.database.latency_ms} ms`}
            />
          </div>

          <Panel title="How the failover works">
            <div className="grid gap-4 p-4 text-sm leading-relaxed text-mute md:grid-cols-3">
              <p>
                <span className="font-medium text-ink">1. Round robin.</span> The load balancer alternates requests between healthy instances. Every response carries an <span className="mono">X-Instance-Id</span> header and every audit row records which instance served it.
              </p>
              <p>
                <span className="font-medium text-ink">2. Failure.</span> A simulated failure makes the instance answer 503. The load balancer retries the same request on the other instance, so users see no errors.
              </p>
              <p>
                <span className="font-medium text-ink">3. Recovery.</span> Recover the instance and it rejoins the rotation within a few seconds. Instances prove they are alive with a heartbeat every 10 seconds.
              </p>
            </div>
            {logical && (
              <p className="border-t border-line px-4 py-3 text-sm text-warn">
                Logical mode: one server process is playing several instance IDs. Routing is emulated inside the API. Deploy separate services for true multi-instance hosting.
              </p>
            )}
          </Panel>
        </div>
      )}
    </>
  );
}
