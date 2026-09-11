'use client';

import { createPortal } from 'react-dom';
import { useEffect, useState } from 'react';

type Comparison = {
  mode: string;
  distance_km: number;
  travel_time_hours: number;
  fuel_estimate: number;
  fuel_saved_vs_shortest: number;
  fuel_savings_percent: number;
  kilometers_saved_vs_shortest: number;
  distance_reduction_percent: number;
  reasons: string[];
};

type Context = { route?: { mode?: string; comparison?: Comparison[]; comparison_baseline?: string; metrics?: { reasons?: string[] } } | null };

const labels: Record<string, string> = { fuel: 'Fuel efficient', shortest: 'Shortest', safest: 'Safety optimized', balanced: 'Balanced' };

export default function RouteComparisonPanel() {
  const [route, setRoute] = useState<Context['route']>(null);
  useEffect(() => {
    const update = (event: Event) => setRoute((event as CustomEvent<Context>).detail.route ?? null);
    window.addEventListener('maritime-context', update);
    return () => window.removeEventListener('maritime-context', update);
  }, []);
  const target = typeof document !== 'undefined' ? document.querySelector('.inspector') : null;
  if (!route?.comparison?.length || !target) return null;
  const selected = route.comparison.find((item) => item.mode === route.mode);
  return createPortal(<div className="route-comparison" aria-live="polite"><p className="eyebrow">Route comparison</p><p className="comparison-note">Savings are measured against the shortest route.</p><div className="comparison-list">{route.comparison.map((item) => <div className={`comparison-row ${item.mode === route.mode ? 'selected' : ''}`} key={item.mode} role="button" tabIndex={0} onClick={() => window.dispatchEvent(new CustomEvent('route-mode-selected', { detail: item.mode }))} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') window.dispatchEvent(new CustomEvent('route-mode-selected', { detail: item.mode })); }}><strong>{labels[item.mode] ?? item.mode}</strong><span>{item.distance_km.toFixed(1)} km · {item.fuel_estimate.toFixed(1)} fuel</span><small>{item.fuel_saved_vs_shortest >= 0 ? `${item.fuel_saved_vs_shortest.toFixed(1)} fuel saved` : `${Math.abs(item.fuel_saved_vs_shortest).toFixed(1)} more fuel`} · {item.kilometers_saved_vs_shortest >= 0 ? `${item.kilometers_saved_vs_shortest.toFixed(1)} km shorter` : `${Math.abs(item.kilometers_saved_vs_shortest).toFixed(1)} km longer`}</small></div>)}</div>{selected && <div className="route-reasons"><p className="eyebrow">Why {labels[selected.mode] ?? selected.mode}</p>{selected.reasons.slice(0, 3).map((reason) => <span key={reason}>{reason}</span>)}</div>}</div>, target);
}
