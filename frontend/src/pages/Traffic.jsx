import { useState } from 'react';
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../api';
import { ActionBadge, ErrorNote, PageHeader, Panel, Spinner, ThreatTag, chartTooltip } from '../components/ui';
import { usePolling } from '../hooks';
import { fmtNum, fmtTime, timeAgo } from '../lib/theme';

const WINDOWS = [{ v: 15, l: '15 min' }, { v: 60, l: '1 hour' }, { v: 360, l: '6 hours' }, { v: 1440, l: '24 hours' }];
const axis = { tick: { fill: '#5f708c', fontSize: 11 }, tickLine: false, axisLine: false };
const INSTANCE_COLORS = ['#5ab0ff', '#2dd4bf', '#c084fc', '#fbbf24'];

function codeColor(code) {
  const c = Number(code);
  if (c >= 500) return '#f87171';
  if (c === 429 || c === 403) return '#fbbf24';
  if (c >= 400) return '#fb923c';
  return '#34d399';
}

export default function Traffic() {
  const [minutes, setMinutes] = useState(60);
  const { data: d, error, refresh } = usePolling(() => api.traffic(minutes), 5000, [minutes]);

  return (
    <>
      <PageHeader title="Traffic" description="What the API is receiving, and how the load balancer spreads it across backend instances.">
        <div className="flex rounded-md border border-line p-0.5" role="group" aria-label="Time window">
          {WINDOWS.map((w) => (
            <button key={w.v} onClick={() => setMinutes(w.v)}
              className={`rounded px-3 py-1.5 text-sm ${minutes === w.v ? 'bg-brand/15 text-brand' : 'text-mute hover:text-ink'}`}>{w.l}</button>
          ))}
        </div>
      </PageHeader>
      <ErrorNote error={error} onRetry={refresh} />
      {!d ? <Spinner /> : (
        <div className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-3">
            <Panel className="lg:col-span-2" title="Requests over time" subtitle={`${fmtNum(d.total_requests)} evaluated requests, average response ${d.avg_response_time} ms`} bodyClass="p-4 pt-5">
              <div className="h-64">
                <ResponsiveContainer>
                  <LineChart data={d.timeline.map((t) => ({ time: fmtTime(t.timestamp), requests: t.requests, rt: t.avg_response_time }))} margin={{ left: -12, right: 8, top: 4 }}>
                    <CartesianGrid stroke="#233250" strokeDasharray="3 6" vertical={false} />
                    <XAxis dataKey="time" {...axis} minTickGap={50} />
                    <YAxis {...axis} width={48} />
                    <Tooltip {...chartTooltip} cursor={{ stroke: '#233250' }} />
                    <Line type="monotone" dataKey="requests" name="Requests" stroke="#5ab0ff" strokeWidth={2} dot={false} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Panel>

            <Panel title="Load distribution" subtitle="Share of requests handled by each backend instance">
              <div className="space-y-5 p-5">
                {d.by_instance.length === 0 && <p className="text-sm text-dim">No requests in this window.</p>}
                {d.by_instance.map((i, n) => (
                  <div key={i.label}>
                    <div className="mb-1.5 flex items-baseline justify-between">
                      <span className="mono font-medium">{i.label}</span>
                      <span className="text-2xl font-semibold">{i.percent}%</span>
                    </div>
                    <div className="h-2.5 overflow-hidden rounded-full bg-line">
                      <div className="h-full rounded-full transition-all duration-500" style={{ width: `${i.percent}%`, background: INSTANCE_COLORS[n % 4] }} />
                    </div>
                    <p className="mt-1 text-xs text-dim">{fmtNum(i.count)} requests</p>
                  </div>
                ))}
              </div>
            </Panel>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <Panel title="Requests by endpoint" bodyClass="p-4">
              <div className="h-60">
                <ResponsiveContainer>
                  <BarChart data={d.by_endpoint} layout="vertical" margin={{ left: 8, right: 16 }}>
                    <XAxis type="number" {...axis} />
                    <YAxis type="category" dataKey="label" width={118} {...axis} tick={{ fill: '#93a3bd', fontSize: 11, fontFamily: 'IBM Plex Mono, monospace' }} />
                    <Tooltip {...chartTooltip} />
                    <Bar dataKey="count" name="Requests" fill="#5ab0ff" radius={[0, 4, 4, 0]} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
            <Panel title="Requests by HTTP method" bodyClass="p-4">
              <div className="h-60">
                <ResponsiveContainer>
                  <BarChart data={d.by_method} margin={{ left: -8, right: 8 }}>
                    <CartesianGrid stroke="#233250" strokeDasharray="3 6" vertical={false} />
                    <XAxis dataKey="label" {...axis} />
                    <YAxis {...axis} width={48} />
                    <Tooltip {...chartTooltip} />
                    <Bar dataKey="count" name="Requests" fill="#2dd4bf" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
            <Panel title="Response codes" bodyClass="p-4">
              <div className="h-60">
                <ResponsiveContainer>
                  <BarChart data={d.status_codes} margin={{ left: -8, right: 8 }}>
                    <CartesianGrid stroke="#233250" strokeDasharray="3 6" vertical={false} />
                    <XAxis dataKey="label" {...axis} />
                    <YAxis {...axis} width={48} />
                    <Tooltip {...chartTooltip} />
                    <Bar dataKey="count" name="Requests" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                      {d.status_codes.map((c) => <Cell key={c.label} fill={codeColor(c.label)} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
          </div>

          <Panel title="Latest requests" subtitle="Each row shows which backend instance handled the request">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[820px]">
                <thead className="border-b border-line">
                  <tr>{['Time', 'Source IP', 'Request', 'Status', 'Response', 'Threat', 'Action', 'Handled by'].map((h) => <th key={h} className="th">{h}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {d.recent_requests.map((r) => (
                    <tr key={r.id}>
                      <td className="td whitespace-nowrap text-mute">{timeAgo(r.timestamp)}</td>
                      <td className="td mono">{r.source_ip}</td>
                      <td className="td mono max-w-[15rem] truncate text-mute" title={r.endpoint}><span className="text-dim">{r.method}</span> {r.endpoint}</td>
                      <td className="td mono" style={{ color: codeColor(r.status_code) }}>{r.status_code}</td>
                      <td className="td text-mute">{Math.round(r.response_time)} ms</td>
                      <td className="td"><ThreatTag type={r.threat_type} /></td>
                      <td className="td"><ActionBadge value={r.action} /></td>
                      <td className="td mono font-medium">{r.instance_id}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>
      )}
    </>
  );
}
