'use client';

import { FormEvent, useState } from 'react';

export default function LoginScreen({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    if (username.trim().toLowerCase() === 'admin' && password.trim() === 'admin123') {
      localStorage.setItem('groute-authenticated', 'true');
      onAuthenticated();
      return;
    }
    setError('Invalid GRoute credentials.');
  }

  return <main className="login-screen"><div className="login-aurora aurora-one" /><div className="login-aurora aurora-two" /><div className="login-grid" /><section className="login-showcase"><img src="/GRoute_Logo.png" alt="GRoute" /><p className="login-kicker">MARITIME INTELLIGENCE</p><h1>Safer seas.<br /><span>Smarter routes.</span></h1><p className="login-copy">Persistent iceberg intelligence, live vessel awareness, and AI-assisted routing for demanding waters.</p><div className="login-signals"><span><b />LIVE ICEBERG MOTION</span><span><b />AI ROUTE GUIDANCE</span><span><b />MARITIME RISK LAYER</span></div></section><section className="login-card"><div className="login-card-glow" /><p className="eyebrow">Secure operations access</p><h2>Welcome to GRoute</h2><p className="login-card-copy">Sign in to open your maritime command view.</p><form onSubmit={submit}><label>Username<input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="admin" /></label><label>Password<input autoComplete="current-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="••••••••" /></label>{error && <p className="login-error" aria-live="polite">{error}</p>}<button className="login-submit" type="submit">Enter command center <span>→</span></button><button className="google-login" type="button" onClick={() => { window.location.href = 'http://localhost:8000/api/auth/google'; }}><span className="google-mark">G</span> Continue with Google <span>↗</span></button></form><div className="login-foot"><span>ENCRYPTED SESSION</span><span>GROUTE / v1.0</span></div></section></main>;
}
