'use client';

import React, { useCallback, useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { Mic, MapPin, CalendarDays, LayoutDashboard, Loader2, Bell, Sparkles } from 'lucide-react';
import { api, Farm, Schedule, DashboardSummary, Notification } from './lib/api';
import Dashboard from './components/Dashboard';
const ScheduleCalendar = dynamic(() => import('./components/ScheduleCalendar'), { ssr: false });
const AddManualSchedule = dynamic(() => import('./components/AddManualSchedule'), { ssr: false });
const FarmLocationPicker = dynamic(() => import('./components/FarmLocationPicker'), { ssr: false });
const FarmMap = dynamic(() => import('./components/FarmMap'), { ssr: false });

type Tab = 'dashboard' | 'schedule' | 'map' | 'voice';

const VOICE_LANGS = [
  { code: 'en', label: 'English', bcp47: 'en-US' },
  { code: 'ta', label: 'தமிழ்', bcp47: 'ta-IN' },
  { code: 'hi', label: 'हिन्दी', bcp47: 'hi-IN' },
];

export default function AgriIrrigate() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [farms, setFarms] = useState<Farm[]>([]);
  const [selectedFarmId, setSelectedFarmId] = useState<number | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState<string | null>(null);

  const [voiceLang, setVoiceLang] = useState('en');
  const [listening, setListening] = useState(false);
  const [processingVoice, setProcessingVoice] = useState(false);
  const [voiceLog, setVoiceLog] = useState<{ role: 'you' | 'ai'; text: string }[]>([]);
  const [showLocationPicker, setShowLocationPicker] = useState(false);
  const [editingFarmId, setEditingFarmId] = useState<number | null>(null);

  const selectedFarm = farms.find((f) => f.id === selectedFarmId) || null;
  const farmNameById = Object.fromEntries(farms.map((f) => [f.id, f.name]));

  const loadFarms = useCallback(async () => {
    const list = await api.getFarms();
    setFarms(list);
    if (list.length && selectedFarmId === null) setSelectedFarmId(list[0].id);
  }, [selectedFarmId]);

  const loadFarmData = useCallback(async (farmId: number) => {
    setLoading(true);
    try {
      const [dash, sched, notifs] = await Promise.all([
        api.getDashboard(farmId),
        api.getSchedules({ farm_id: farmId }),
        api.getNotifications({ farm_id: farmId }),
      ]);
      setSummary(dash);
      setSchedules(sched);
      setNotifications(notifs);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadFarms(); }, [loadFarms]);
  useEffect(() => { if (selectedFarmId !== null) loadFarmData(selectedFarmId); }, [selectedFarmId, loadFarmData]);

  async function generate(range: 'today' | '7day' | '30day') {
    if (!selectedFarmId) return;
    setGenerating(range);
    try {
      await api.generateSchedule(selectedFarmId, range);
      await loadFarmData(selectedFarmId);
    } finally {
      setGenerating(null);
    }
  }

  function refresh() {
    if (selectedFarmId !== null) loadFarmData(selectedFarmId);
  }

  async function handleLocationSelect(lat: number, lng: number) {
    if (editingFarmId === null) return;
    try {
      await api.updateFarm(editingFarmId, { latitude: lat, longitude: lng });
      await loadFarms();
      // Fetch terrain data for the new location
      await fetchTerrainData(editingFarmId, lat, lng);
      // Weather will be automatically fetched when the farm data is loaded
      if (selectedFarmId === editingFarmId) {
        refresh();
      }
    } catch (error) {
      console.error('Failed to update farm location:', error);
    }
  }

  async function fetchTerrainData(farmId: number, lat: number, lng: number) {
    try {
      const terrain = await api.getTerrainData(lat, lng);
      await api.updateFarm(farmId, {
        elevation: terrain.elevation,
        slope: terrain.slope,
        terrain_type: terrain.terrain_type,
        drainage_characteristics: terrain.drainage_characteristics,
      });
    } catch (error) {
      console.error('Failed to fetch terrain data:', error);
    }
  }

  function openLocationPicker(farmId: number) {
    setEditingFarmId(farmId);
    setShowLocationPicker(true);
  }

  function speak(text: string, lang: string) {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = VOICE_LANGS.find((l) => l.code === lang)?.bcp47 || 'en-US';
    window.speechSynthesis.speak(utterance);
  }

  async function handleVoiceText(text: string) {
    setVoiceLog((log) => [...log, { role: 'you', text }]);
    setProcessingVoice(true);
    try {
      const result = await api.sendVoiceCommand(text, voiceLang);
      setVoiceLog((log) => [...log, { role: 'ai', text: result.response_text }]);
      speak(result.response_text, voiceLang);
      refresh();
    } catch (error) {
      console.error('Voice command error:', error);
      setVoiceLog((log) => [...log, { role: 'ai', text: 'Sorry, I could not process your command. Please try again.' }]);
    } finally {
      setProcessingVoice(false);
    }
  }

  function startVoice() {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Voice recognition is not supported in this browser. Try Chrome, or type your command instead.');
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = VOICE_LANGS.find((l) => l.code === voiceLang)?.bcp47 || 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => setListening(true);
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognition.onresult = (event: any) => handleVoiceText(event.results[0][0].transcript);
    recognition.start();
  }

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div>
      <header className="topbar contour-field">
        <div className="shell topbar-inner">
          <div className="wordmark">
            <h1>AgriIrrigate</h1>
            <span className="eyebrow">Scheduling Engine</span>
          </div>
          <div className="topbar-right">
            {unreadCount > 0 && (
              <div className="bell-count"><Bell size={14} /> {unreadCount}</div>
            )}
            <select
              value={selectedFarmId ?? ''}
              onChange={(e) => setSelectedFarmId(Number(e.target.value))}
              className="farm-select"
            >
              {farms.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
            </select>
          </div>
        </div>
      </header>

      <div className="shell" style={{ paddingBottom: '4rem' }}>
        <div className="tabs">
          <TabButton icon={<LayoutDashboard size={15} />} label="Dashboard" active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')} />
          <TabButton icon={<CalendarDays size={15} />} label="Schedule" active={activeTab === 'schedule'} onClick={() => setActiveTab('schedule')} />
          <TabButton icon={<MapPin size={15} />} label="Satellite Map" active={activeTab === 'map'} onClick={() => setActiveTab('map')} />
          <TabButton icon={<Mic size={15} />} label="Voice" active={activeTab === 'voice'} onClick={() => setActiveTab('voice')} />
        </div>

        {!selectedFarm ? (
          <div className="schedule-empty">Loading farms…</div>
        ) : (
          <>
            {activeTab === 'dashboard' && (
              <Dashboard farm={selectedFarm} summary={summary} loading={loading} />
            )}

            {activeTab === 'schedule' && (
              <div>
                <div className="schedule-toolbar">
                  <div className="btn-row">
                    <GenButton label="Today" busy={generating === 'today'} onClick={() => generate('today')} />
                    <GenButton label="Next 7 Days" busy={generating === '7day'} onClick={() => generate('7day')} />
                    <GenButton label="Next 30 Days" busy={generating === '30day'} onClick={() => generate('30day')} />
                  </div>
                  <AddManualSchedule farmId={selectedFarm.id} onAdded={refresh} />
                </div>

                <div className="panel schedule-panel">
                  {loading ? (
                    <div className="schedule-empty">Loading schedule…</div>
                  ) : schedules.length === 0 ? (
                    <div className="schedule-empty">No schedule yet. Generate one with the buttons above.</div>
                  ) : (
                    <ScheduleCalendar schedules={schedules} farmNameById={farmNameById} onChanged={refresh} />
                  )}
                </div>
              </div>
            )}

            {activeTab === 'map' && (
              <div>
                <div className="section-title"><MapPin size={18} /> Satellite crop health map</div>
                <div className="map-frame">
                  <FarmMap farms={farms} />
                </div>
                {selectedFarm && (
                  <div style={{ marginTop: '1rem', textAlign: 'center' }}>
                    <button onClick={() => openLocationPicker(selectedFarm.id)} className="btn">
                      <MapPin size={14} /> Update Farm Location
                    </button>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'voice' && (
              <div className="voice-shell">
                <div className="lang-row">
                  {VOICE_LANGS.map((l) => (
                    <button
                      key={l.code}
                      onClick={() => setVoiceLang(l.code)}
                      className={`lang-pill ${voiceLang === l.code ? 'active' : ''}`}
                    >
                      {l.label}
                    </button>
                  ))}
                </div>

                <div className="voice-dial-wrap">
                  <button onClick={startVoice} disabled={listening || processingVoice} className={`voice-dial ${listening ? 'listening' : ''}`}>
                    {listening || processingVoice ? <Loader2 size={40} className="animate-spin" /> : '🎤'}
                  </button>
                  <p className="voice-hint">
                    {listening ? 'Listening…' : processingVoice ? 'Processing…' : 'Tap and speak a command'}
                  </p>
                  <p className="voice-sub">
                    Try: "Schedule irrigation for tomorrow", "Postpone today's irrigation", "What is my next irrigation?"
                  </p>
                </div>

                {voiceLog.length > 0 && (
                  <div className="voice-log">
                    {voiceLog.map((entry, i) => (
                      <div key={i} className={`chat-bubble ${entry.role}`}>
                        {entry.role === 'ai' && <Sparkles size={14} color="var(--teal)" style={{ flexShrink: 0, marginTop: '0.2rem' }} />}
                        {entry.text}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {showLocationPicker && selectedFarm && (
        <FarmLocationPicker
          onLocationSelect={handleLocationSelect}
          initialLat={selectedFarm.latitude}
          initialLng={selectedFarm.longitude}
          onClose={() => setShowLocationPicker(false)}
        />
      )}
    </div>
  );
}

function TabButton({ icon, label, active, onClick }: { icon: React.ReactNode; label: string; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={`tab ${active ? 'active' : ''}`}>
      {icon} {label}
    </button>
  );
}

function GenButton({ label, busy, onClick }: { label: string; busy: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} disabled={busy} className="btn">
      {busy && <Loader2 size={14} className="animate-spin" />}
      {busy ? 'Generating…' : label}
    </button>
  );
}
