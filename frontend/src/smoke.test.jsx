// Smoke test: mounts every page against a RUNNING backend (VITE_API_URL) and checks real data renders.
// Run:  VITE_API_URL=http://localhost:8000 SMOKE_USER=admin SMOKE_PASS=... npm test
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, clearToken, setToken } from './api';
import App from './App';
import { AuthProvider } from './auth';

globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
const errors = [];
vi.spyOn(console, 'error').mockImplementation((...a) => errors.push(a.map(String).join(' ')));

// Mount authenticated: token is already set before render so AuthProvider.api.me() succeeds.
const mount = (path) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  );

// Mount signed-out: clear token first so Protected redirects to /login.
const mountSignedOut = (path) => {
  clearToken();
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  );
};

let authToken = '';

beforeAll(async () => {
  const res = await api.login(process.env.SMOKE_USER || 'admin', process.env.SMOKE_PASS || 'AdminPass#123');
  authToken = res.access_token;
  setToken(authToken);
});

// Restore token before each test so api.me() inside AuthProvider always succeeds.
beforeEach(() => {
  if (authToken) setToken(authToken);
});

afterEach(cleanup);

describe('CloudSentry UI against live API', () => {
  it('shows the login page when signed out', async () => {
    mountSignedOut('/');
    expect(await screen.findByText('Sign in', { selector: 'h2' })).toBeTruthy();
    // Restore immediately so next test is not affected.
    setToken(authToken);
  });

  it('renders the dashboard with KPIs, health and threat feed', async () => {
    mount('/');
    expect(await screen.findByText('Requests / sec', {}, { timeout: 10000 })).toBeTruthy();
    expect(await screen.findByText('Threat level')).toBeTruthy();
    expect(await screen.findByText('Load balancer', {}, { timeout: 8000 })).toBeTruthy();
    expect(await screen.findByText('Simulate attack')).toBeTruthy();
    expect((await screen.findAllByText(/^risk \d+/, {}, { timeout: 8000 })).length).toBeGreaterThan(0);
  });

  it('starts an attack simulation from the button and shows the pipeline', async () => {
    mount('/');
    const btn = await screen.findByText('Simulate attack', {}, { timeout: 10000 });
    fireEvent.click(btn);
    expect(await screen.findByText(/Attack simulation running/, {}, { timeout: 10000 })).toBeTruthy();
    expect(await screen.findByText('Traffic spike')).toBeTruthy();
    await api.resetSimulation();
  });

  for (const [path, text] of [
    ['/attack-lab', 'Controlled Security Simulation'],
    ['/threats', 'Every request the detection engine flagged'],
    ['/traffic', 'Load distribution'],
    ['/instances', 'How the failover works'],
    ['/rules', 'Request inspector'],
    ['/audit', 'The complete security trail'],
  ]) {
    it(`renders ${path}`, async () => {
      mount(path);
      expect(await screen.findByText(new RegExp(text), {}, { timeout: 10000 })).toBeTruthy();
    });
  }

  it('lists threats and opens a threat detail page', async () => {
    const feed = await api.threats({ limit: 1 });
    mount(`/threats/${feed.items[0].threat_id}`);
    expect(await screen.findByText('What happened', {}, { timeout: 10000 })).toBeTruthy();
    expect(await screen.findByText('Request details')).toBeTruthy();
  });

  it('threat table and audit table show rows', async () => {
    mount('/threats');
    await waitFor(() => expect(screen.getAllByText(/^CS-\d+/).length).toBeGreaterThan(5), { timeout: 10000 });
    cleanup();
    mount('/audit');
    await waitFor(() => expect(screen.getAllByText(/^API-0[12]$/).length).toBeGreaterThan(5), { timeout: 10000 });
  });

  it('threw no React errors', () => {
    const real = errors.filter((e) => !/act\(|not wrapped|Warning: An update/.test(e));
    expect(real).toEqual([]);
  });
});
