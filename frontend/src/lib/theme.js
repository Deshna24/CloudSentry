export const THREAT_LABEL = {
  NORMAL: 'Normal',
  BRUTE_FORCE: 'Brute force',
  RATE_ABUSE: 'Rate abuse',
  SQL_INJECTION: 'SQL injection',
  XSS: 'XSS',
  PATH_TRAVERSAL: 'Path traversal',
};
export const THREAT_COLOR = {
  NORMAL: '#4f7cac',
  BRUTE_FORCE: '#f87171',
  RATE_ABUSE: '#fbbf24',
  SQL_INJECTION: '#c084fc',
  XSS: '#fb923c',
  PATH_TRAVERSAL: '#2dd4bf',
};
export const THREAT_TYPES = Object.keys(THREAT_LABEL);

export const SEVERITY_STYLE = {
  LOW: 'bg-ok/10 text-ok ring-ok/30',
  MEDIUM: 'bg-warn/10 text-warn ring-warn/30',
  HIGH: 'bg-hot/10 text-hot ring-hot/30',
  CRITICAL: 'bg-crit/15 text-crit ring-crit/40',
};
export const SEVERITY_TEXT = { LOW: 'text-ok', MEDIUM: 'text-warn', HIGH: 'text-hot', CRITICAL: 'text-crit' };
export const SEVERITY_BG = { LOW: 'bg-ok', MEDIUM: 'bg-warn', HIGH: 'bg-hot', CRITICAL: 'bg-crit' };
export const SEVERITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

export const ACTION_STYLE = {
  ALLOW: 'bg-line/60 text-mute ring-line',
  MONITOR: 'bg-brand/10 text-brand ring-brand/30',
  THROTTLE: 'bg-warn/10 text-warn ring-warn/30',
  BLOCK: 'bg-crit/15 text-crit ring-crit/40',
};
export const ACTIONS = ['ALLOW', 'MONITOR', 'THROTTLE', 'BLOCK'];

export const STATUS = {
  HEALTHY: { dot: 'bg-ok', text: 'text-ok', label: 'Healthy' },
  WARNING: { dot: 'bg-warn', text: 'text-warn', label: 'Warning' },
  DOWN: { dot: 'bg-crit', text: 'text-crit', label: 'Down' },
};

export const fmtNum = (n) => (n === null || n === undefined ? '-' : Number(n).toLocaleString());
export const fmtTime = (iso) => (iso ? new Date(iso).toLocaleTimeString([], { hour12: false }) : '-');
export const fmtDateTime = (iso) =>
  iso ? new Date(iso).toLocaleString([], { hour12: false, month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '-';
export function fmtDuration(sec) {
  if (sec === null || sec === undefined) return '-';
  const d = Math.floor(sec / 86400), h = Math.floor((sec % 86400) / 3600), m = Math.floor((sec % 3600) / 60);
  if (d) return `${d}d ${h}h`;
  if (h) return `${h}h ${m}m`;
  if (m) return `${m}m ${Math.floor(sec % 60)}s`;
  return `${Math.floor(sec)}s`;
}
export function timeAgo(iso) {
  if (!iso) return '-';
  const s = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 5) return 'just now';
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}
