import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import Filters, { EMPTY_FILTERS } from '../components/Filters';
import { ActionBadge, Empty, ErrorNote, PageHeader, Pagination, Panel, SeverityBadge, Spinner, ThreatTag } from '../components/ui';
import { usePolling } from '../hooks';
import { fmtDateTime } from '../lib/theme';

const LIMIT = 50;

export default function AuditLogs() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [offset, setOffset] = useState(0);
  const { data, error, loading, refresh } = usePolling(() => api.auditLogs({ ...filters, limit: LIMIT, offset }), 5000, [filters, offset]);
  const change = (f) => { setFilters(f); setOffset(0); };

  return (
    <>
      <PageHeader title="Audit logs" description="The complete security trail: every evaluated request and every administrator action, with the instance that handled it." />
      <ErrorNote error={error} onRetry={refresh} />
      <Panel>
        <Filters value={filters} onChange={change} includeNormal searchHint="Search user, IP or event" />
        {loading && !data ? <Spinner /> : data?.items.length === 0 ? (
          <Empty title="No log entries match" hint="Try clearing the filters." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1000px]">
              <thead className="border-b border-line">
                <tr>{['Timestamp', 'User', 'Event', 'Source IP', 'Threat', 'Risk', 'Severity', 'Action', 'Instance'].map((h) => <th key={h} className="th">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data?.items.map((l) => (
                  <tr key={l.id} className="hover:bg-raised/60">
                    <td className="td whitespace-nowrap text-mute">{fmtDateTime(l.timestamp)}</td>
                    <td className="td">{l.user}</td>
                    <td className="td max-w-[20rem]">
                      {l.threat_id && l.threat_type !== 'NORMAL'
                        ? <Link to={`/threats/${l.threat_id}`} className="text-brand hover:underline">{l.event}</Link>
                        : <span className={l.threat_type ? 'text-mute' : ''}>{l.event}</span>}
                    </td>
                    <td className="td mono">{l.source_ip}</td>
                    <td className="td">{l.threat_type ? <ThreatTag type={l.threat_type} /> : <span className="text-dim">admin action</span>}</td>
                    <td className="td mono">{l.risk_score ?? '-'}</td>
                    <td className="td"><SeverityBadge value={l.severity} /></td>
                    <td className="td"><ActionBadge value={l.action} /></td>
                    <td className="td mono text-mute">{l.instance_id}</td>
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
