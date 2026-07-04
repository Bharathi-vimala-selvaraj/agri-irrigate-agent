'use client';

import React, { useEffect, useMemo, useRef } from 'react';
import L from 'leaflet';
import { Farm } from '../lib/api';

function ndviColor(ndvi: number): string {
  if (ndvi >= 0.6) return '#a0bd68';
  if (ndvi >= 0.4) return '#dcac48';
  return '#cd6249';
}

export default function LeafletMap({ farms }: { farms: Farm[] }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);

  const center = useMemo<[number, number]>(() => {
    if (!farms.length) {
      return [0, 0];
    }

    return [farms[0].latitude, farms[0].longitude];
  }, [farms]);

  useEffect(() => {
    if (typeof window === 'undefined' || !containerRef.current || !farms.length) {
      return;
    }

    if (mapRef.current) {
      mapRef.current.remove();
      mapRef.current = null;
    }

    const map = L.map(containerRef.current, {
      center,
      zoom: 13,
      scrollWheelZoom: true,
      zoomControl: true,
    });

    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      attribution: '&copy; Esri World Imagery',
    }).addTo(map);

    farms.forEach((farm) => {
      const color = ndviColor(farm.ndvi);
      L.circleMarker([farm.latitude, farm.longitude], {
        radius: 16,
        color,
        fillColor: color,
        fillOpacity: 0.5,
        weight: 2,
      })
        .bindPopup(`
          <div class="map-popup">
            <div class="name">${farm.name}</div>
            <div class="row">${farm.crop_type} · ${farm.growth_stage}</div>
            <div class="row">NDVI ${farm.ndvi.toFixed(2)} · Moisture ${farm.soil_moisture.toFixed(0)}%</div>
            <div class="row">Disease risk: ${farm.disease_risk}</div>
          </div>
        `)
        .addTo(map);
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [center, farms]);

  return <div ref={containerRef} className="leaflet-container" style={{ height: '500px', width: '100%' }} />;
}
