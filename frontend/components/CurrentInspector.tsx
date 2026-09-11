'use client';

import { createPortal } from 'react-dom';
import { useEffect, useState } from 'react';

type CurrentDetails = { speed_ms?: number; bearing_deg?: number; current_type?: string; source?: string; observed_at?: string } | null;

export default function CurrentInspector() {
  const [current, setCurrent] = useState<CurrentDetails>(null);
  useEffect(() => {
    const update = (event: Event) => setCurrent((event as CustomEvent<CurrentDetails>).detail);
    window.addEventListener('current-hover', update);
    return () => window.removeEventListener('current-hover', update);
  }, []);
  const target = typeof document !== 'undefined' ? document.querySelector('.inspector') : null;
  if (!current || !target) return null;
  return createPortal(<div className="current-inline detail-card" aria-live="polite"><h2>Ocean current</h2><span className="tag">{current.current_type ?? 'LIVE CURRENT'}</span><div className="metric"><span>Speed</span><strong>{Number(current.speed_ms ?? 0).toFixed(3)} m/s</strong></div><div className="metric"><span>Bearing</span><strong>{Number(current.bearing_deg ?? 0).toFixed(1)}°</strong></div><div className="metric"><span>Source</span><strong>{current.source ?? 'Live marine sample'}</strong></div><div className="metric"><span>Observed</span><strong>{current.observed_at ?? '—'}</strong></div></div>, target);
}
