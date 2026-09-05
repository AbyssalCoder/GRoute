'use client';

import { useEffect, useState } from 'react';

const voyageImages = [
  'https://images.unsplash.com/photo-1494412574643-ff11b0a5c1c3?auto=format&fit=crop&w=600&q=80',
  'https://images.unsplash.com/photo-1544551763-46a013bb70d5?auto=format&fit=crop&w=600&q=80',
  'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=600&q=80',
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

  return <aside className="promo-card"><img src={voyageImages[imageIndex]} alt="Container vessel at sea" /><div><strong>Smarter data<br />for safer voyages.</strong><span>→</span></div></aside>;
}
