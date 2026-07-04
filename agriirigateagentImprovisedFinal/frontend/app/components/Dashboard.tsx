'use client';

import React from 'react';
import { Droplet, CheckCircle2, Bell, Leaf } from 'lucide-react';
import { DashboardSummary, Farm } from '../lib/api';
import Gauge from './Gauge';

interface Props {
  farm: Farm;
  summary: DashboardSummary | null;
  loading: boolean;
}

export default function Dashboard({ farm, summary, loading }: Props) {
  if (loading || !summary) {
    return (
      <div className="panel panel-pad schedule-empty">
        Reading field instruments…
      </div>
    );
  }

  const next = summary.next_scheduled_task;

  return (
    <div>
      <div className="panel hero-panel">
        <div className="hero-left">
          <Gauge value={farm.soil_moisture} color="var(--teal)" label="soil moisture" />
          <div className="hero-copy">
            <span className="eyebrow">{next ? 'Next scheduled task' : 'Field status'}</span>
            {next ? (
              <>
                <h2>
                  Irrigate {farm.name.split(' - ')[0]} with {next.water_quantity_mm}mm
                  {next.start_time ? ` at ${next.start_time}` : ''} on {next.date}
                </h2>
                <p>{next.reason}</p>
              </>
            ) : (
              <>
                <h2>No irrigation currently scheduled</h2>
                <p>
                  Soil moisture is within the healthy range for {farm.growth_stage} {farm.crop_type.toLowerCase()}.
                </p>
              </>
            )}
          </div>
        </div>
        <div className="hero-meta">
          <div className="block">
            <div className="figure">{farm.ndvi.toFixed(2)}</div>
            <div className="label">NDVI</div>
          </div>
          {next && (
            <div className="block">
              <div className="figure">{Math.round(next.confidence_score * 100)}%</div>
              <div className="label">Confidence</div>
            </div>
          )}
        </div>
      </div>

      <div className="panel ledger">
        <LedgerCell label="Upcoming" value={summary.upcoming_count} color="var(--teal)" />
        <LedgerCell label="Running" value={summary.running_count} color="var(--ochre)" />
        <LedgerCell label="Missed" value={summary.missed_count} color="var(--rust)" />
        <LedgerCell label="Completed" value={summary.completed_count} color="var(--moss)" />
      </div>

      <div className="split-row">
        <div className="panel panel-pad">
          <div className="panel-title"><Leaf size={14} /> Water usage, completed</div>
          <div className="big-figure">{Math.round(summary.total_water_usage_liters).toLocaleString()} L</div>
          <div className="big-figure-note">Across all completed irrigation events</div>
        </div>

        <div className="panel panel-pad">
          <div className="panel-title"><Bell size={14} /> Active alerts</div>
          {summary.notifications.length === 0 ? (
            <p className="empty-note">Nothing needs attention right now.</p>
          ) : (
            <ul className="alert-list">
              {summary.notifications.slice(0, 5).map((n) => (
                <li key={n.id}>
                  <span className="tick" style={{ background: n.severity === 'warning' ? 'var(--ochre)' : 'var(--sky)' }} />
                  {n.message}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function LedgerCell({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="ledger-cell">
      <div className="figure">{value}</div>
      <div className="label"><span className="tick" style={{ background: color }} /> {label}</div>
    </div>
  );
}
