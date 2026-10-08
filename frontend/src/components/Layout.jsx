import { Activity, Gauge, LogOut, Menu, ScrollText, Server, ShieldAlert, SlidersHorizontal, Trophy, X, Zap } from 'lucide-react';
import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../auth';
import { api } from '../api';
import { usePolling } from '../hooks';

const NAV = [
  { to: '/', label: 'Dashboard', icon: Gauge, end: true },
  { to: '/attack-lab', label: '⚡ ATTACK LAB', icon: Zap },
  { to: '/threats', label: 'Threats', icon: ShieldAlert },
  { to: '/traffic', label: 'Traffic', icon: Activity },
  { to: '/instances', label: 'Instances', icon: Server },
  { to: '/rules', label: 'Security rules', icon: SlidersHorizontal },
  { to: '/audit', label: 'Audit logs', icon: ScrollText },
];

function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <img src="/favicon.svg" alt="" className="h-8 w-8" />
      <span className="text-[17px] font-semibold tracking-tight">CloudSentry</span>
    </div>
  );
}

const PILL = {
  OPERATIONAL: { dot: 'bg-ok', text: 'text-ok', label: 'System operational' },
  DEGRADED: { dot: 'bg-warn', text: 'text-warn', label: 'System degraded' },
  DOWN: { dot: 'bg-crit', text: 'text-crit', label: 'System outage' },
  UNKNOWN: { dot: 'bg-dim', text: 'text-mute', label: 'Connecting' },
};

export default function Layout() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const health = usePolling(() => api.health(), 4000);
  const progress = usePolling(() => api.progress(), 3000);
  const status = health.error ? 'DOWN' : health.data?.status || 'UNKNOWN';
  const pill = PILL[status];

  const userProg = progress.data || {
    level: 4,
    title: 'CLOUD DEFENDER',
    xp: 720,
    next_level_xp: 1000,
    progress_percent: 72,
  };

  const ratingCard = (
    <div className="mx-3 my-2 rounded-lg border border-line bg-panel p-2.5">
      <div className="flex items-center justify-between text-[11px]">
        <span className="font-semibold text-brand">LEVEL 0{userProg.level}</span>
        <span className="font-mono text-dim">{userProg.xp}/{userProg.next_level_xp} XP</span>
      </div>
      <p className="mt-0.5 truncate text-xs font-medium text-ink">{userProg.title}</p>
      <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-line">
        <div
          className="h-full rounded-full bg-brand transition-all duration-500"
          style={{ width: `${userProg.progress_percent || 72}%` }}
        />
      </div>
    </div>
  );

  const nav = (
    <nav className="flex flex-1 flex-col gap-1 p-3">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={() => setOpen(false)}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              isActive ? 'bg-brand/10 text-brand' : 'text-mute hover:bg-raised hover:text-ink'
            }`
          }
        >
          <Icon className="h-4 w-4" /> {label}
        </NavLink>
      ))}
      <div className="mt-auto">
        {ratingCard}
      </div>
    </nav>
  );

  return (
    <div className="flex min-h-full">
      {/* desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-56 shrink-0 flex-col border-r border-line bg-bg-soft lg:flex">
        <div className="flex h-14 items-center border-b border-line px-4">
          <Logo />
        </div>
        {nav}
        <div className="border-t border-line p-4 text-xs text-dim">
          Served by <span className="mono text-mute">{health.data?.instance_id || '-'}</span>
        </div>
      </aside>

      {/* mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
          <aside className="absolute left-0 top-0 flex h-full w-64 flex-col border-r border-line bg-bg-soft">
            <div className="flex h-14 items-center justify-between border-b border-line px-4">
              <Logo />
              <button aria-label="Close menu" onClick={() => setOpen(false)}>
                <X className="h-5 w-5 text-mute" />
              </button>
            </div>
            {nav}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-line bg-bg/90 px-4 backdrop-blur lg:px-6">
          <div className="flex items-center gap-3">
            <button className="lg:hidden" aria-label="Open menu" onClick={() => setOpen(true)}>
              <Menu className="h-5 w-5 text-mute" />
            </button>
            <div className="lg:hidden">
              <Logo />
            </div>
            <div className="hidden items-center gap-2 rounded-full border border-line bg-panel px-3 py-1 text-xs lg:flex" role="status">
              <span className={`h-2 w-2 rounded-full ${pill.dot} ${status === 'OPERATIONAL' ? 'pulse-dot' : ''}`} />
              <span className={`font-medium ${pill.text}`}>{pill.label}</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-full border border-line bg-panel px-3 py-1 text-xs lg:hidden" role="status">
              <span className={`h-2 w-2 rounded-full ${pill.dot}`} />
              <span className={pill.text}>{status === 'OPERATIONAL' ? 'Operational' : status === 'DEGRADED' ? 'Degraded' : status === 'DOWN' ? 'Outage' : '...'}</span>
            </div>
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium leading-tight">{user.username}</p>
              <p className="text-xs text-dim">{user.role === 'ADMIN' ? 'Administrator' : 'Analyst'}</p>
            </div>
            <button className="btn-ghost !px-2.5" onClick={logout} aria-label="Sign out" title="Sign out">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 lg:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
