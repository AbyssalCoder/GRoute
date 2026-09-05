'use client';

import { useEffect, useState } from 'react';

const voyageImages = [
  { source: 'https://images.unsplash.com/photo-1483347756197-71ef80e95f73?auto=format&fit=crop&w=600&q=80', alt: 'Iceberg floating in blue water' },
  { source: 'https://images.unsplash.com/photo-1517783999520-f068d7431a60?auto=format&fit=crop&w=600&q=80', alt: 'Open ocean under a blue sky' },
  { source: 'https://images.unsplash.com/photo-1500375592092-40eb2168fd21?auto=format&fit=crop&w=600&q=80', alt: 'Ocean waves rolling across the sea' },
  { source: 'https://images.unsplash.com/photo-1511497584788-876760111969?auto=format&fit=crop&w=600&q=80', alt: 'Clear water flowing over ice' },
  { source: 'https://images.unsplash.com/photo-1544551763-77ef2d0cfc6c?auto=format&fit=crop&w=600&q=80', alt: 'Blue underwater ocean scene' },
  { source: 'https://images.unsplash.com/photo-1439066615861-d1af74d74000?auto=format&fit=crop&w=600&q=80', alt: 'Calm water and distant shoreline' },
];

export default function VoyagePromo() {
  const [imageIndex, setImageIndex] = useState(0);

  useEffect(() => {
    const handleSelection = (event: Event) => {
      const selected = (event as CustomEvent<Record<string, unknown> | null>).detail;
      const identifier = String(selected?.vessel_id ?? selected?.mmsi ?? selected?.name ?? '');
      const hash = Array.from(identifier).reduce((total, character) => total + character.charCodeAt(0), 0);
      setImageIndex(hash % voyageImages.length);
    };
    window.addEventListener('vessel-selected', handleSelection);
    return () => window.removeEventListener('vessel-selected', handleSelection);
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => setImageIndex((current) => (current + 1) % voyageImages.length), 8000);
    return () => window.clearInterval(timer);
  }, []);

  return <aside className="promo-card"><img src={voyageImages[imageIndex].source} alt={voyageImages[imageIndex].alt} /><div><strong>Smarter data<br />for safer voyages.</strong><span>→</span></div></aside>;
}
