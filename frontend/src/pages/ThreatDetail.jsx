import { ArrowLeft } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api';
import { ActionBadge, ErrorNote, Panel, SeverityBadge, Spinner, ThreatTag } from '../components/ui';
import { SEVERITY_BG, SEVERITY_TEXT, fmtDateTime } from '../lib/theme';

function Row({ label, children }) {
  return (
    <div className="flex flex-col gap-1 border-b border-line px-4 py-3 last:border-0 sm:flex-row sm:items-center sm:gap-6">
      <dt className="w-40 shrink-0 text-sm text-dim">{label}</dt>
      <dd className="min-w-0 break-words text-sm">{children}</dd>
    </div>
  );
}

export default function ThreatDetail() {
  const { id } = useParams();
  const [t, setT] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setT(null);
    setError(null);
    api.threat(id).then(setT).catch(setError);
  }, [id]);

  return (
    <>
      <Link to="/threats" className="mb-4 inline-flex items-center gap-1.5 text-sm text-mute hover:text-ink">
        <ArrowLeft className="h-4 w-4" /> All threats
      </Link>
      <ErrorNote error={error} />
      {!t && !error && <Spinner />}
      {t && (
        <>
          <div className="mb-5 flex flex-wrap items-center gap-3">
            <h1 className="text-xl font-semibold tracking-tight">Threat <span className="mono text-[20px] text-brand">#{t.threat_id}</span></h1>
            <SeverityBadge value={t.severity} />
            <ActionBadge value={t.action} />
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <div className="space-y-4 lg:col-span-2">
              <Panel title="What happened">
                <div className="space-y-4 p-4 text-sm leading-relaxed">
                  <div>
                    <p className="text-dim">Threat</p>
                    <p className="mt-1 text-base font-medium"><ThreatTag type={t.threat_type} /></p>
                    <p className="mt-1 text-mute">{t.explanation}</p>
                  </div>
                  <div>
                    <p className="text-dim">Why it was detected</p>
                    <p className="mt-1">{t.reason}</p>
                  </div>
                  <div>
                    <p className="text-dim">Action taken</p>
                    <p className="mt-1">{t.response}</p>
                  </div>
                </div>
              </Panel>

              <Panel title="Request details">
                <dl>
                  <Row label="Timestamp">{fmtDateTime(t.timestamp)}</Row>
                  <Row label="Source IP"><span className="mono">{t.source_ip}</span></Row>
                  <Row label="Endpoint"><span className="mono"><span className="text-dim">{t.method}</span> {t.endpoint}</span></Row>
                  <Row label="Requests per minute">{t.request_count.toLocaleString()}</Row>
                  <Row label="Failed attempts">{t.failed_logins.toLocaleString()}</Row>
                  <Row label="Response">{t.status_code} in {Math.round(t.response_time)} ms</Row>
                  <Row label="Caller role">{t.user_role}</Row>
                  <Row label="Processed by"><span className="mono">{t.instance_id}</span></Row>
                  <Row label="Request ID"><span className="mono text-xs text-mute">{t.request_id}</span></Row>
                </dl>
              </Panel>

              {t.payload && (
                <Panel title="Captured payload" subtitle="Stored and shown as inert text. It is never executed.">
                  <pre className="mono overflow-x-auto whitespace-pre-wrap break-all p-4 text-crit">{t.payload}</pre>
                </Panel>
              )}
            </div>

            <Panel title="Risk score" className="h-fit">
              <div className="p-5">
                <p className={`text-5xl font-semibold tracking-tight ${SEVERITY_TEXT[t.severity]}`}>
                  {t.risk_score}<span className="text-xl text-dim"> / 100</span>
                </p>
                <div className="mt-4 h-2 overflow-hidden rounded-full bg-line">
                  <div className={`h-full rounded-full ${SEVERITY_BG[t.severity]}`} style={{ width: `${t.risk_score}%` }} />
                </div>
                <p className="mt-4 text-sm text-mute">
                  Severity <span className={`font-medium ${SEVERITY_TEXT[t.severity]}`}>{t.severity.toLowerCase()}</span>. Scores below 30 are allowed, 30-59 monitored, 60-79 throttled and 80 or more blocked.
                </p>
              </div>
            </Panel>
          </div>
        </>
      )}
    </>
  );
}
