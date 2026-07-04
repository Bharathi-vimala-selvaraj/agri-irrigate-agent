'use client';

import React from 'react';

interface GaugeProps {
  value: number; // 0-100
  size?: number;
  color: string;
  label: string;
  ticks?: number;
}

/**
 * An analog instrument-panel style arc gauge. This is the page's signature
 * element — used for soil moisture (and reusable for NDVI) so the whole app
 * reads like a real irrigation control panel rather than a generic chart.
 */
export default function Gauge({ value, size = 132, color, label, ticks = 10 }: GaugeProps) {
  const clamped = Math.max(0, Math.min(100, value));
  const startAngle = -220;
  const sweep = 260;
  const r = size / 2 - 14;
  const cx = size / 2;
  const cy = size / 2;

  function polar(angleDeg: number, radius: number) {
    const rad = (angleDeg * Math.PI) / 180;
    return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) };
  }

  function arcPath(fromDeg: number, toDeg: number, radius: number) {
    const start = polar(fromDeg, radius);
    const end = polar(toDeg, radius);
    const largeArc = toDeg - fromDeg > 180 ? 1 : 0;
    return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 1 ${end.x} ${end.y}`;
  }

  const valueAngle = startAngle + (sweep * clamped) / 100;
  const tickMarks = Array.from({ length: ticks + 1 }, (_, i) => {
    const angle = startAngle + (sweep * i) / ticks;
    const outer = polar(angle, r + 6);
    const inner = polar(angle, r - 1);
    return { outer, inner, key: i };
  });

  return (
    <div className="gauge-wrap" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <path d={arcPath(startAngle, startAngle + sweep, r)} fill="none" stroke="var(--line)" strokeWidth={3} strokeLinecap="round" />
        {tickMarks.map((t) => (
          <line key={t.key} x1={t.inner.x} y1={t.inner.y} x2={t.outer.x} y2={t.outer.y} stroke="var(--line)" strokeWidth={1.5} />
        ))}
        <path d={arcPath(startAngle, valueAngle, r)} fill="none" stroke={color} strokeWidth={4} strokeLinecap="round" />
        <circle cx={polar(valueAngle, r).x} cy={polar(valueAngle, r).y} r={4.5} fill={color} />
      </svg>
      <div className="gauge-figure">
        <span className="pct">{Math.round(clamped)}%</span>
        <span className="tag-label">{label}</span>
      </div>
    </div>
  );
}
