import { API_URL } from './config';

const TOKEN_KEY = 'cloudsentry_token';
let memoryToken = null;
export const getToken = () => memoryToken || localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => {
  memoryToken = t;
  try { localStorage.setItem(TOKEN_KEY, t); } catch {}
};
export const clearToken = () => {
  memoryToken = null;
  try { localStorage.removeItem(TOKEN_KEY); } catch {}
};

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = 'GET', body, params, timeout = 12000 } = {}) {
  const url = new URL(API_URL + path);
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v);
  });
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  const token = getToken();
  try {
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    });
    const data = await res.json().catch(() => null);
    if (res.status === 401 && path !== '/auth/login' && token) {
      clearToken();
      window.dispatchEvent(new Event('cloudsentry:logout'));
    }
    if (!res.ok) {
      const detail = typeof data?.detail === 'string' ? data.detail : `Request failed (${res.status})`;
      throw new ApiError(detail, res.status);
    }
    return data;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err.name === 'AbortError') throw new ApiError('The API took too long to respond.', 0);
    throw new ApiError('Cannot reach the API. Check that the backend is running and VITE_API_URL is correct.', 0);
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  login: (username, password) => request('/auth/login', { method: 'POST', body: { username, password } }),
  me: () => request('/auth/me'),
  summary: () => request('/dashboard/summary'),
  health: () => request('/health/detailed'),
  traffic: (minutes) => request('/traffic', { params: { minutes } }),
  threats: (params) => request('/threats', { params }),
  threat: (id) => request(`/threats/${id}`),
  instances: () => request('/instances'),
  auditLogs: (params) => request('/audit-logs', { params }),
  rules: () => request('/security-rules'),
  updateRule: (id, enabled) => request(`/security-rules/${id}`, { method: 'PUT', body: { enabled } }),
  inspect: (body) => request('/inspect', { method: 'POST', body }),
  attack: (scenario = 'full') => request('/simulation/attack', { method: 'POST', body: { scenario } }),
  launchSimulation: (body) => request('/simulation/launch', { method: 'POST', body }),
  simulationStatus: () => request('/simulation/status'),
  simulationRun: (id) => request(`/simulation/${id}`),
  resetRun: (id) => request(`/simulation/${id}/reset`, { method: 'POST' }),
  normalTraffic: () => request('/simulation/normal', { method: 'POST' }),
  resetSimulation: () => request('/simulation/reset', { method: 'POST' }),
  instanceFailure: (instance_id, down) =>
    request('/simulation/instance-failure', { method: 'POST', body: { instance_id, down } }),
  progress: () => request('/gamification/progress'),
  missions: () => request('/gamification/missions'),
  achievements: () => request('/gamification/achievements'),
};
