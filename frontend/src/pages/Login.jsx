import { Loader2 } from 'lucide-react';
import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth';

export default function Login() {
  const { user, login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await login(username.trim(), password);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-full lg:grid-cols-[1.1fr_1fr]">
      <section className="grid-bg relative hidden flex-col justify-between border-r border-line p-12 lg:flex">
        <div className="flex items-center gap-3">
          <img src="/favicon.svg" alt="" className="h-10 w-10" />
          <span className="text-xl font-semibold tracking-tight">CloudSentry</span>
        </div>
        <div className="max-w-lg">
          <h1 className="text-4xl font-semibold leading-tight tracking-tight">
            Every API request, scored and answered in milliseconds.
          </h1>
          <p className="mt-5 text-base leading-relaxed text-mute">
            CloudSentry watches API traffic, scores each request from 0 to 100, and throttles or blocks
            brute force, request floods, SQL injection, XSS and path traversal on its own, with a full audit trail.
          </p>
        </div>
        <dl className="grid max-w-lg grid-cols-3 gap-6 text-sm">
          <div>
            <dt className="text-dim">Detection</dt>
            <dd className="mt-1 font-medium">5 transparent rules</dd>
          </div>
          <div>
            <dt className="text-dim">Backends</dt>
            <dd className="mt-1 font-medium">2 load-balanced instances</dd>
          </div>
          <div>
            <dt className="text-dim">Response</dt>
            <dd className="mt-1 font-medium">Allow, monitor, throttle, block</dd>
          </div>
        </dl>
      </section>

      <section className="flex items-center justify-center px-6 py-12">
        <form onSubmit={submit} className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <img src="/favicon.svg" alt="" className="h-9 w-9" />
            <span className="text-lg font-semibold">CloudSentry</span>
          </div>
          <h2 className="text-2xl font-semibold tracking-tight">Sign in</h2>
          <p className="mt-1.5 text-sm text-mute">Use your administrator or analyst account.</p>

          <label className="mt-8 block text-sm font-medium" htmlFor="username">Username</label>
          <input id="username" className="field mt-1.5" autoComplete="username" autoFocus required value={username}
            onChange={(e) => setUsername(e.target.value)} />

          <label className="mt-4 block text-sm font-medium" htmlFor="password">Password</label>
          <input id="password" type="password" className="field mt-1.5" autoComplete="current-password" required value={password}
            onChange={(e) => setPassword(e.target.value)} />

          {error && (
            <p className="mt-4 rounded-md border border-crit/40 bg-crit/10 px-3 py-2 text-sm text-crit" role="alert">{error}</p>
          )}

          <button className="btn-primary mt-6 w-full" disabled={busy}>
            {busy && <Loader2 className="h-4 w-4 animate-spin" />} Sign in
          </button>
          <p className="mt-6 text-xs leading-relaxed text-dim">
            Repeated failed sign-ins are themselves treated as a brute-force attack and will lock your IP out for a while.
          </p>
        </form>
      </section>
    </div>
  );
}
