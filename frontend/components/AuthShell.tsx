'use client';

import { ReactNode, useEffect, useState } from 'react';
import AccountCenter from './AccountCenter';
import CurrentInspector from './CurrentInspector';
import IcebergSpeedInspector from './IcebergSpeedInspector';
import LoginScreen from './LoginScreen';
import RouteComparisonPanel from './RouteComparisonPanel';
import SOSControl from './SOSControl';
import VoyagePromo from './VoyagePromo';

export default function AuthShell({ children }: { children: ReactNode }) {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  useEffect(() => { const params = new URLSearchParams(window.location.search); if (params.get('sso') === 'success') { localStorage.setItem('groute-authenticated', 'true'); window.history.replaceState({}, '', window.location.pathname); setAuthenticated(true); return; } setAuthenticated(localStorage.getItem('groute-authenticated') === 'true'); }, []);
  if (authenticated === null) return <div className="auth-loading">Loading GRoute...</div>;
  if (!authenticated) return <LoginScreen onAuthenticated={() => setAuthenticated(true)} />;
  return <><AccountCenter onLogout={() => setAuthenticated(false)} /><SOSControl /><CurrentInspector /><IcebergSpeedInspector /><RouteComparisonPanel /><VoyagePromo />{children}</>;
}
