'use client';

import React, { useMemo, useState } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import { EventClickArg, EventContentArg } from '@fullcalendar/core';
import { Droplet, CloudRain, CheckCircle2, XCircle, Clock, Trash2, X } from 'lucide-react';
import { api, Schedule } from '../lib/api';

const STATUS_STYLE: Record<string, { color: string; tag: string; label: string }> = {
  Scheduled: { color: 'var(--teal)', tag: 'tag-teal', label: 'Scheduled' },
  Running: { color: 'var(--ochre)', tag: 'tag-ochre', label: 'Running' },
  Completed: { color: 'var(--moss)', tag: 'tag-moss', label: 'Completed' },
  Skipped: { color: 'var(--ink-faint)', tag: 'tag-muted', label: 'Skipped' },
  'Auto Skipped': { color: 'var(--sky)', tag: 'tag-sky', label: 'Auto-skipped (rain)' },
  Rescheduled: { color: 'var(--rust)', tag: 'tag-rust', label: 'Rescheduled' },
};

interface Props {
  schedules: Schedule[];
  farmNameById: Record<number, string>;
  onChanged: () => void;
}

export default function ScheduleCalendar({ schedules, farmNameById, onChanged }: Props) {
  const [selected, setSelected] = useState<Schedule | null>(null);
  const [busy, setBusy] = useState(false);

  const events = useMemo(
    () =>
      schedules.map((s) => {
        const style = STATUS_STYLE[s.status] || STATUS_STYLE.Scheduled;
        const title =
          s.status === 'Auto Skipped'
            ? `Skipped — ${farmNameById[s.farm_id] || 'Farm'}`
            : `${s.water_quantity_mm}mm — ${farmNameById[s.farm_id] || 'Farm'}`;
        return {
          id: String(s.id),
          title,
          date: s.date,
          start: s.start_time ? `${s.date}T${s.start_time}` : s.date,
          end: s.end_time ? `${s.date}T${s.end_time}` : undefined,
          allDay: !s.start_time,
          backgroundColor: 'transparent',
          borderColor: style.color,
          textColor: 'var(--ink)',
          extendedProps: { schedule: s },
        };
      }),
    [schedules, farmNameById]
  );

  async function handleDrop(arg: any) {
    const schedule: Schedule = arg.event.extendedProps.schedule;
    const newDate = arg.event.startStr.slice(0, 10);
    const newTime = arg.event.startStr.length > 10 ? arg.event.startStr.slice(11, 16) : schedule.start_time;
    try {
      await api.updateSchedule(schedule.id, { date: newDate, start_time: newTime ?? undefined });
      onChanged();
    } catch {
      arg.revert();
    }
  }

  function handleEventClick(arg: EventClickArg) {
    setSelected(arg.event.extendedProps.schedule as Schedule);
  }

  async function markComplete() {
    if (!selected) return;
    setBusy(true);
    try {
      await api.updateSchedule(selected.id, { status: 'Completed' });
      setSelected(null);
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  async function skipIt() {
    if (!selected) return;
    setBusy(true);
    try {
      await api.updateSchedule(selected.id, { status: 'Skipped' });
      setSelected(null);
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  async function removeIt() {
    if (!selected) return;
    setBusy(true);
    try {
      await api.deleteSchedule(selected.id);
      setSelected(null);
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  function renderEventContent(arg: EventContentArg) {
    const s: Schedule = arg.event.extendedProps.schedule;
    const style = STATUS_STYLE[s.status] || STATUS_STYLE.Scheduled;
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', padding: '0.1rem 0.2rem', overflow: 'hidden' }}>
        <span className="tick" style={{ background: style.color }} />
        {s.status === 'Auto Skipped' ? (
          <CloudRain size={11} color="var(--sky)" />
        ) : (
          <Droplet size={11} color="var(--teal)" />
        )}
        <span style={{ fontSize: '0.72rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{arg.event.title}</span>
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="fc-theme-agri">
        <FullCalendar
          plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
          initialView="dayGridMonth"
          headerToolbar={{
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay',
          }}
          height="auto"
          events={events}
          editable
          eventDrop={handleDrop}
          eventClick={handleEventClick}
          eventContent={renderEventContent}
          dayMaxEvents={3}
        />
      </div>

      {selected && (
        <div className="modal-overlay" onClick={() => setSelected(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <div>
                <span className={`tag ${(STATUS_STYLE[selected.status] || STATUS_STYLE.Scheduled).tag}`}>
                  {(STATUS_STYLE[selected.status] || STATUS_STYLE.Scheduled).label}
                </span>
                <p className="modal-sub">
                  {farmNameById[selected.farm_id] || 'Farm'} · {selected.date}
                </p>
              </div>
              <button onClick={() => setSelected(null)} className="close-btn"><X size={18} /></button>
            </div>

            {selected.status !== 'Auto Skipped' && selected.start_time && (
              <div className="mono" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: 'var(--ink-muted)', marginBottom: '1rem' }}>
                <Clock size={14} color="var(--teal)" />
                {selected.start_time} – {selected.end_time} ({selected.duration_minutes} min)
              </div>
            )}

            <div className="detail-grid">
              <div className="detail-cell">
                <div className="label">Water quantity</div>
                <div className="value">{selected.water_quantity_mm} mm</div>
              </div>
              <div className="detail-cell">
                <div className="label">Est. usage</div>
                <div className="value">{Math.round(selected.estimated_water_usage_liters).toLocaleString()} L</div>
              </div>
            </div>

            <div className="reasoning-box">
              <div className="label">AI reasoning</div>
              <p>{selected.reason}</p>
              <div className="confidence">Confidence: {Math.round(selected.confidence_score * 100)}%</div>
            </div>

            <div className="btn-row">
              <button disabled={busy} onClick={markComplete} className="btn btn-primary" style={{ flex: 1, justifyContent: 'center' }}>
                <CheckCircle2 size={15} /> Mark complete
              </button>
              <button disabled={busy} onClick={skipIt} className="btn" style={{ flex: 1, justifyContent: 'center' }}>
                <XCircle size={15} /> Skip
              </button>
              <button disabled={busy} onClick={removeIt} className="btn btn-danger">
                <Trash2 size={15} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
