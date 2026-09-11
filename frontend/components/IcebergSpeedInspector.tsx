'use client';

import { createPortal } from 'react-dom';
import { useEffect, useState } from 'react';

type IcebergDetails = { __kind?: string; speed?: number; velocity_u?: number; velocity_v?: number } | null;

export default function IcebergSpeedInspector() {
  const [iceberg, setIceberg] = useState<IcebergDetails>(null);
  useEffect(() => {
    const update = (event: Event) => setIceberg((event as CustomEvent<IcebergDetails>).detail);
    window.addEventListener('iceberg-selected', update);
    return () => window.removeEventListener('iceberg-selected', update);
  }, []);
  const card = typeof document !== 'undefined' ? document.querySelector('.inspector .detail-card') : null;
  if (!iceberg || iceberg.__kind !== 'iceberg' || !card) return null;
  const speed = Number(iceberg.speed ?? Math.hypot(iceberg.velocity_u ?? 0, iceberg.velocity_v ?? 0));
  return createPortal(<div className="iceberg-speed metric"><span>Iceberg speed</span><strong>{speed.toFixed(3)} km/day</strong></div>, card);
}
