'use client';

import React, { useState } from 'react';
import { Plus, X } from 'lucide-react';
import { api } from '../lib/api';

export default function AddManualSchedule({ farmId, onAdded }: { farmId: number; onAdded: () => void }) {
  const [open, setOpen] = useState(false);
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [time, setTime] = useState('06:00');
  const [duration, setDuration] = useState(30);
  const [water, setWater] = useState(15);
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    try {
      await api.createManualSchedule({
        farm_id: farmId,
        date,
        start_time: time,
        duration_minutes: duration,
        water_quantity_mm: water,
        notes: 'Manually added by farmer.',
      });
      setOpen(false);
      onAdded();
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button onClick={() => setOpen(true)} className="btn">
        <Plus size={15} /> Add manual irrigation
      </button>

      {open && (
        <div className="modal-overlay" onClick={() => setOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3>Add manual irrigation</h3>
              <button onClick={() => setOpen(false)} className="close-btn"><X size={18} /></button>
            </div>
            <div className="field">
              <label>Date</label>
              <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
            <div className="field">
              <label>Start time</label>
              <input type="time" value={time} onChange={(e) => setTime(e.target.value)} />
            </div>
            <div className="field field-row">
              <div>
                <label>Duration (min)</label>
                <input type="number" value={duration} onChange={(e) => setDuration(Number(e.target.value))} />
              </div>
              <div>
                <label>Water (mm)</label>
                <input type="number" value={water} onChange={(e) => setWater(Number(e.target.value))} />
              </div>
            </div>
            <button disabled={busy} onClick={submit} className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', marginTop: '0.5rem' }}>
              {busy ? 'Adding…' : 'Add to schedule'}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
