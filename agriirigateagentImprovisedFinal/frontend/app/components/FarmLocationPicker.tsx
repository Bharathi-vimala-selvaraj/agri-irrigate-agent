'use client';

import React, { useEffect, useRef, useState } from 'react';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { MapPin, Check, X } from 'lucide-react';

interface FarmLocationPickerProps {
  initialLat: number;
  initialLng: number;
  onLocationSelect: (lat: number, lng: number) => void;
  onClose: () => void;
}

export default function FarmLocationPicker({ initialLat, initialLng, onLocationSelect, onClose }: FarmLocationPickerProps) {
  const [position, setPosition] = useState<[number, number]>([initialLat, initialLng]);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);

  useEffect(() => {
    delete (L.Icon.Default.prototype as any)._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
      iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
      shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
    });
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined' || !containerRef.current) {
      return;
    }

    if (mapRef.current) {
      mapRef.current.remove();
      mapRef.current = null;
    }

    const map = L.map(containerRef.current, {
      center: position,
      zoom: 10,
      scrollWheelZoom: true,
      zoomControl: true,
    });

    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      attribution: '&copy; Esri World Imagery',
    }).addTo(map);

    const marker = L.marker(position, {
      draggable: true,
    });

    marker.on('dragend', () => {
      const latlng = marker.getLatLng();
      setPosition([latlng.lat, latlng.lng]);
    });

    marker.addTo(map);

    map.on('click', (event) => {
      const { lat, lng } = event.latlng;
      setPosition([lat, lng]);
      marker.setLatLng([lat, lng]);
    });

    mapRef.current = map;
    markerRef.current = marker;

    return () => {
      map.remove();
      mapRef.current = null;
      markerRef.current = null;
    };
  }, [position[0], position[1]]);

  const handleSelectClick = () => {
    onLocationSelect(position[0], position[1]);
  };

  return (
    <div className="modal-overlay">
      <div className="modal-card">
        <div className="modal-header">
          <div>
            <h2>Select Farm Location</h2>
            <p>Click the map to choose the farm location.</p>
          </div>
          <button onClick={onClose} className="icon-button" aria-label="Close picker">
            <X size={18} />
          </button>
        </div>

        <div className="map-picker">
          <div ref={containerRef} className="leaflet-container" style={{ height: '420px', width: '100%' }} />
        </div>

        <div className="modal-actions">
          <div className="location-preview">
            <MapPin size={16} />
            <span>{position[0].toFixed(6)}, {position[1].toFixed(6)}</span>
          </div>
          <button onClick={handleSelectClick} className="btn btn-primary">
            <Check size={16} /> Save location
          </button>
        </div>
      </div>
    </div>
  );
}
