import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import Filters, { EMPTY_FILTERS } from '../components/Filters';
import { ActionBadge, Empty, ErrorNote, PageHeader, Pagination, Panel, SeverityBadge, Spinner, ThreatTag } from '../components/ui';
import { usePolling } from '../hooks';
import { SEVERITY_BG, fmtDateTime } from '../lib/theme';

const LIMIT = 25;

export function RiskMeter({ value, severity }) {
  return (
    <span className="flex items-center gap-2">
      <span className="h-1.5 w-14 overflow-hidden rounded-full bg-line">
        <span className={`block h-full rounded-full ${SEVERITY_BG[severity]}`} style={{ width: `${value}%` }} />
      </span>
      <span className="mono w-7 text-right">{value}</span>
    </span>
  );
}

export default function Threats() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [offset, setOffset] = useState(0);
  const { data, error, loading, refresh } = usePolling(() => api.threats({ ...filters, limit: LIMIT, offset }), 5000, [filters, offset]);
  const change = (f) => { setFilters(f); setOffset(0); };

  return (
    <>
      <PageHeader title="Threats" description="Every request the detection engine flagged, newest first. Select a row to see why it was flagged and what the system did." />
      <ErrorNote error={error} onRetry={refresh} />
      <Panel>
        <Filters value={filters} onChange={change} />
        {loading && !data ? <Spinner /> : data?.items.length === 0 ? (
          <Empty title="No threats match these filters" hint="Clear the filters, or run an attack simulation from the dashboard." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[920px]">
              <thead className="border-b border-line">
                <tr>{['Threat', 'Time', 'Source IP', 'Endpoint', 'Type', 'Risk', 'Severity', 'Action', 'Instance'].map((h) => <th key={h} className="th">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data?.items.map((t) => (
                  <tr key={t.id} tabIndex={0} onClick={() => navigate(`/threats/${t.threat_id}`)}
                    onKeyDown={(e) => e.key === 'Enter' && navigate(`/threats/${t.threat_id}`)}
                    className="cursor-pointer transition-colors hover:bg-raised">
                    <td className="td mono text-brand">{t.threat_id}</td>
                    <td className="td whitespace-nowrap text-mute">{fmtDateTime(t.timestamp)}</td>
                    <td className="td mono">{t.source_ip}</td>
                    <td className="td mono max-w-[16rem] truncate text-mute" title={t.endpoint}><span className="text-dim">{t.method}</span> {t.endpoint}</td>
                    <td className="td"><ThreatTag type={t.threat_type} /></td>
                    <td className="td"><RiskMeter value={t.risk_score} severity={t.severity} /></td>
                    <td className="td"><SeverityBadge value={t.severity} /></td>
                    <td className="td"><ActionBadge value={t.action} /></td>
                    <td className="td mono text-mute">{t.instance_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && <Pagination total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />}
      </Panel>
    </>
  );
}
