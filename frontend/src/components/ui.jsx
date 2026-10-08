import { AlertTriangle, Loader2 } from 'lucide-react';
import { ACTION_STYLE, SEVERITY_STYLE, STATUS, THREAT_COLOR, THREAT_LABEL } from '../lib/theme';

export function SeverityBadge({ value }) {
  if (!value) return <span className="text-dim">-</span>;
  return (
    <span className={`inline-flex rounded px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${SEVERITY_STYLE[value]}`}>
      {value}
    </span>
  );
}

export function ActionBadge({ value }) {
  if (!value) return <span className="text-dim">-</span>;
  return (
    <span className={`inline-flex rounded px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${ACTION_STYLE[value]}`}>
      {value}
    </span>
  );
}

export function ThreatTag({ type }) {
  if (!type) return <span className="text-dim">-</span>;
  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap text-sm">
      <span className="h-2 w-2 rounded-full" style={{ background: THREAT_COLOR[type] }} />
      {THREAT_LABEL[type] || type}
    </span>
  );
}

export function StatusDot({ status, pulse = false }) {
  const s = STATUS[status] || STATUS.DOWN;
  return <span className={`inline-block h-2.5 w-2.5 shrink-0 rounded-full ${s.dot} ${pulse && status === 'HEALTHY' ? 'pulse-dot' : ''}`} />;
}

export function StatusText({ status }) {
  const s = STATUS[status] || STATUS.DOWN;
  return <span className={`text-sm font-medium ${s.text}`}>{s.label}</span>;
}

export function Panel({ title, subtitle, action, children, className = '', bodyClass = '' }) {
  return (
    <section className={`panel ${className}`}>
      {(title || action) && (
        <header className="panel-head">
          <div className="min-w-0">
            <h2 className="panel-title">{title}</h2>
            {subtitle && <p className="mt-0.5 text-xs text-dim">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className={bodyClass}>{children}</div>
    </section>
  );
}

export function PageHeader({ title, description, children }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm text-mute">{description}</p>}
      </div>
      <div className="flex flex-wrap items-center gap-2">{children}</div>
    </div>
  );
}

export function Spinner({ label = 'Loading' }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-sm text-mute" role="status">
      <Loader2 className="h-4 w-4 animate-spin" /> {label}
    </div>
  );
}

export function ErrorNote({ error, onRetry }) {
  if (!error) return null;
  return (
    <div className="mb-4 flex items-start gap-3 rounded-lg border border-crit/40 bg-crit/10 px-4 py-3 text-sm" role="alert">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-crit" />
      <div className="flex-1">
        <p className="font-medium text-crit">Something went wrong</p>
        <p className="text-mute">{error.message}</p>
      </div>
      {onRetry && (
        <button className="btn-ghost !py-1" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function Empty({ title, hint }) {
  return (
    <div className="px-6 py-14 text-center">
      <p className="text-sm font-medium">{title}</p>
      {hint && <p className="mt-1 text-sm text-dim">{hint}</p>}
    </div>
  );
}

export function Switch({ checked, onChange, disabled, label }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative h-6 w-11 shrink-0 rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${checked ? 'bg-ok' : 'bg-line'}`}
    >
      <span className={`absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${checked ? 'translate-x-5' : ''}`} />
    </button>
  );
}

export function Pagination({ total, limit, offset, onChange }) {
  const page = Math.floor(offset / limit) + 1;
  const pages = Math.max(1, Math.ceil(total / limit));
  return (
    <div className="flex items-center justify-between gap-3 border-t border-line px-4 py-3 text-sm text-mute">
      <span>
        {total === 0 ? 'No results' : `${offset + 1}-${Math.min(offset + limit, total)} of ${total.toLocaleString()}`}
      </span>
      <div className="flex items-center gap-2">
        <button className="btn-ghost !py-1" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>
          Previous
        </button>
        <span className="hidden sm:inline">
          Page {page} of {pages}
        </span>
        <button className="btn-ghost !py-1" disabled={page >= pages} onClick={() => onChange(offset + limit)}>
          Next
        </button>
      </div>
    </div>
  );
}

export function Select({ value, onChange, options, placeholder, label }) {
  return (
    <select aria-label={label} className="field !w-auto min-w-[9rem]" value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">{placeholder}</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

export const chartTooltip = {
  contentStyle: { background: '#0d1422', border: '1px solid #233250', borderRadius: 8, fontSize: 12, color: '#e8eef8' },
  labelStyle: { color: '#93a3bd' },
  itemStyle: { color: '#e8eef8' },
  cursor: { fill: 'rgba(90,176,255,0.06)' },
};
