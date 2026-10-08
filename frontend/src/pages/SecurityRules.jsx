import { Lock, Loader2 } from 'lucide-react';
import { useState } from 'react';
import { api } from '../api';
import { useAuth } from '../auth';
import { ActionBadge, ErrorNote, PageHeader, Panel, SeverityBadge, Spinner, Switch, ThreatTag } from '../components/ui';
import { usePolling } from '../hooks';

const PRESETS = [
  { label: 'SQL injection', v: { endpoint: '/api/search', method: 'GET', payload: "1' UNION SELECT username, password FROM users --", request_count: 12, failed_logins: 0 } },
  { label: 'XSS', v: { endpoint: '/api/cart', method: 'POST', payload: '<img src=x onerror=alert(1)>', request_count: 12, failed_logins: 0 } },
  { label: 'Path traversal', v: { endpoint: '/files/../../etc/passwd', method: 'GET', payload: '', request_count: 4, failed_logins: 0 } },
  { label: 'Brute force', v: { endpoint: '/auth/login', method: 'POST', payload: '{"username":"admin"}', request_count: 60, failed_logins: 42 } },
  { label: 'Request flood', v: { endpoint: '/api/products', method: 'GET', payload: '', request_count: 900, failed_logins: 0 } },
  { label: 'Normal request', v: { endpoint: '/api/products', method: 'GET', payload: '', request_count: 8, failed_logins: 0 } },
];

function Inspector() {
  const [form, setForm] = useState(PRESETS[0].v);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const run = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setResult(await api.inspect({ ...form, request_count: Number(form.request_count) || 0, failed_logins: Number(form.failed_logins) || 0 }));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel title="Request inspector" subtitle="Describe a request and see how the engine scores it. Results are logged to the audit trail. Nothing is executed.">
      <form onSubmit={run} className="grid gap-5 p-4 lg:grid-cols-2">
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <button type="button" key={p.label} className="btn-ghost !px-2.5 !py-1 text-xs" onClick={() => { setForm(p.v); setResult(null); }}>{p.label}</button>
            ))}
          </div>
          <div className="flex gap-2">
            <select className="field !w-28" aria-label="Method" value={form.method} onChange={set('method')}>
              {['GET', 'POST', 'PUT', 'DELETE', 'PATCH'].map((m) => <option key={m}>{m}</option>)}
            </select>
            <input className="field mono" aria-label="Endpoint" value={form.endpoint} onChange={set('endpoint')} required maxLength={300} />
          </div>
          <textarea className="field mono min-h-[5rem]" aria-label="Payload" placeholder="Request payload" value={form.payload} onChange={set('payload')} maxLength={2000} />
          <div className="grid grid-cols-2 gap-3">
            <label className="text-xs text-mute">Requests per minute
              <input type="number" min="0" className="field mt-1" value={form.request_count} onChange={set('request_count')} /></label>
            <label className="text-xs text-mute">Failed logins
              <input type="number" min="0" className="field mt-1" value={form.failed_logins} onChange={set('failed_logins')} /></label>
          </div>
          <button className="btn-primary" disabled={busy}>{busy && <Loader2 className="h-4 w-4 animate-spin" />} Inspect request</button>
        </div>
        <div className="rounded-lg border border-line bg-bg-soft p-4">
          <ErrorNote error={error} />
          {!result ? <p className="text-sm text-dim">The verdict appears here.</p> : (
            <div className="space-y-3 text-sm">
              <div className="flex flex-wrap items-center gap-3"><ThreatTag type={result.threat_type} /><SeverityBadge value={result.severity} /><ActionBadge value={result.action} /></div>
              <p className="text-4xl font-semibold tracking-tight">{result.risk_score}<span className="text-lg text-dim"> / 100</span></p>
              <p className="text-mute">{result.reason}</p>
              <p className="text-xs text-dim">Logged as <span className="mono text-mute">{result.threat_id}</span> by <span className="mono text-mute">{result.instance_id}</span></p>
            </div>
          )}
        </div>
      </form>
    </Panel>
  );
}

export default function SecurityRules() {
  const { isAdmin } = useAuth();
  const { data, error, refresh } = usePolling(() => api.rules(), 0);
  const [busy, setBusy] = useState(null);
  const [actionError, setActionError] = useState(null);

  const toggle = async (rule, enabled) => {
    setBusy(rule.id);
    setActionError(null);
    try {
      await api.updateRule(rule.id, enabled);
      await refresh();
    } catch (e) {
      setActionError(e);
    } finally {
      setBusy(null);
    }
  };

  const group = (cat) => (data || []).filter((r) => r.category === cat);
  return (
    <>
      <PageHeader title="Security rules" description="The protections CloudSentry applies to every request. Detection rules can be switched off to demonstrate their effect." />
      <ErrorNote error={error || actionError} onRetry={refresh} />
      {!data ? <Spinner /> : (
        <div className="space-y-4">
          <Panel title="Detection rules" subtitle={isAdmin ? 'Changes apply to the next request.' : 'Only administrators can change these.'}>
            <ul className="divide-y divide-line">
              {group('detection').map((r) => (
                <li key={r.id} className="flex items-center gap-4 px-4 py-4">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{r.name}</p>
                    <p className="mt-0.5 text-sm text-mute">{r.description}</p>
                  </div>
                  <span className={`hidden text-xs font-medium sm:block ${r.enabled ? 'text-ok' : 'text-dim'}`}>{r.enabled ? 'Enabled' : 'Disabled'}</span>
                  <Switch checked={r.enabled} disabled={!isAdmin || busy === r.id} label={`${r.name} enabled`} onChange={(v) => toggle(r, v)} />
                </li>
              ))}
            </ul>
          </Panel>
          <Panel title="Platform protections" subtitle="Built into the application and always on.">
            <ul className="divide-y divide-line">
              {group('platform').map((r) => (
                <li key={r.id} className="flex items-center gap-4 px-4 py-4">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{r.name}</p>
                    <p className="mt-0.5 text-sm text-mute">{r.description}</p>
                  </div>
                  <span className="flex items-center gap-1.5 text-xs text-ok"><Lock className="h-3.5 w-3.5" /> Always on</span>
                </li>
              ))}
            </ul>
          </Panel>
          <Inspector />
        </div>
      )}
    </>
  );
}
