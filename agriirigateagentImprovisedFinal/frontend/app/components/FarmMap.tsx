'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { Farm } from '../lib/api';

const LeafletMap = dynamic(
  () => import('./LeafletMap').then((mod) => mod.default),
  { ssr: false, loading: () => <div className="schedule-empty">Loading map…</div> }
);

export default function FarmMap({ farms }: { farms: Farm[] }) {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    delete (L.Icon.Default.prototype as any)._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
      iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
      shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
    });
    setIsClient(true);
  }, []);

  if (!farms.length) {
    return <div className="schedule-empty">No farms yet.</div>;
  }

  if (!isClient) {
    return <div className="schedule-empty">Loading map…</div>;
  }

  return <LeafletMap farms={farms} />;
}
