import { Search } from 'lucide-react';
import { ACTIONS, SEVERITIES, THREAT_LABEL, THREAT_TYPES } from '../lib/theme';
import { Select } from './ui';

export const EMPTY_FILTERS = { threat_type: '', severity: '', action: '', q: '', date_from: '', date_to: '' };

export default function Filters({ value, onChange, includeNormal = false, searchHint = 'Search IP or endpoint' }) {
  const set = (k) => (v) => onChange({ ...value, [k]: v });
  const types = THREAT_TYPES.filter((t) => includeNormal || t !== 'NORMAL');
  const dirty = Object.values(value).some(Boolean);
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-line p-3">
      <div className="relative min-w-[12rem] flex-1">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-dim" />
        <input className="field !pl-9" placeholder={searchHint} aria-label="Search" value={value.q} onChange={(e) => set('q')(e.target.value)} />
      </div>
      <Select label="Threat type" placeholder="All threat types" value={value.threat_type} onChange={set('threat_type')}
        options={types.map((t) => ({ value: t, label: THREAT_LABEL[t] }))} />
      <Select label="Severity" placeholder="All severities" value={value.severity} onChange={set('severity')}
        options={SEVERITIES.map((s) => ({ value: s, label: s[0] + s.slice(1).toLowerCase() }))} />
      <Select label="Action" placeholder="All actions" value={value.action} onChange={set('action')}
        options={ACTIONS.map((a) => ({ value: a, label: a[0] + a.slice(1).toLowerCase() }))} />
      <input type="date" className="field !w-auto" aria-label="From date" value={value.date_from} onChange={(e) => set('date_from')(e.target.value)} />
      <input type="date" className="field !w-auto" aria-label="To date" value={value.date_to} onChange={(e) => set('date_to')(e.target.value)} />
      {dirty && <button className="btn-ghost" onClick={() => onChange(EMPTY_FILTERS)}>Clear</button>}
    </div>
  );
}
