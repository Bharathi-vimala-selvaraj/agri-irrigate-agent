const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export type ScheduleStatus =
  | 'Scheduled'
  | 'Running'
  | 'Completed'
  | 'Skipped'
  | 'Auto Skipped'
  | 'Rescheduled';

export interface Farm {
  id: number;
  name: string;
  crop_type: string;
  crop_variety?: string;
  growth_stage: string;
  sowing_date?: string;
  farm_size_acres: number;
  irrigation_method: string;
  soil_type?: string;
  water_source?: string;
  pump_capacity_hp?: number;
  ndvi: number;
  soil_moisture: number;
  disease_risk: string;
  latitude: number;
  longitude: number;
  elevation?: number;
  slope?: number;
  terrain_type?: string;
  drainage_characteristics?: string;
}

export interface Schedule {
  id: number;
  farm_id: number;
  date: string;
  start_time: string | null;
  end_time: string | null;
  duration_minutes: number;
  water_quantity_mm: number;
  irrigation_method: string;
  estimated_water_usage_liters: number;
  status: ScheduleStatus;
  reason: string;
  confidence_score: number;
  weather_considered?: Record<string, unknown>;
  is_manual?: number;
}

export interface Notification {
  id: number;
  farm_id: number | null;
  type: string;
  message: string;
  severity: string;
  is_read: number;
  created_at: string;
}

export interface DashboardSummary {
  farm: Farm;
  upcoming_count: number;
  running_count: number;
  missed_count: number;
  completed_count: number;
  total_water_usage_liters: number;
  next_scheduled_task: Schedule | null;
  notifications: Notification[];
}

export interface WeatherDay {
  date: string;
  temp_max: number;
  temp_min: number;
  precipitation_mm: number;
  rain_probability: number;
  humidity: number;
  et0: number;
}

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    next: { revalidate: 0 },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`API ${res.status} ${path}: ${body}`);
  }
  return res.json();
}

export const api = {
  // Farms
  getFarms: () => req<Farm[]>('/farms'),
  getFarm: (id: number) => req<Farm>(`/farms/${id}`),
  createFarm: (data: Partial<Farm>) =>
    req<Farm>('/farms', { method: 'POST', body: JSON.stringify(data) }),
  updateFarm: (id: number, data: Partial<Farm>) =>
    req<Farm>(`/farms/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  // Schedules
  generateSchedule: (farm_id: number, range: 'today' | '7day' | '30day') =>
    req<{ count: number; schedules: Schedule[] }>('/schedules/generate', {
      method: 'POST',
      body: JSON.stringify({ farm_id, range }),
    }),
  getSchedules: (params?: { farm_id?: number; date_from?: string; date_to?: string }) => {
    const qs = new URLSearchParams();
    if (params?.farm_id) qs.set('farm_id', String(params.farm_id));
    if (params?.date_from) qs.set('date_from', params.date_from);
    if (params?.date_to) qs.set('date_to', params.date_to);
    const query = qs.toString();
    return req<Schedule[]>(`/schedules${query ? `?${query}` : ''}`);
  },
  updateSchedule: (id: number, data: Partial<Schedule>) =>
    req<Schedule>(`/schedules/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteSchedule: (id: number) =>
    req<{ deleted: boolean }>(`/schedules/${id}`, { method: 'DELETE' }),
  createManualSchedule: (data: {
    farm_id: number;
    date: string;
    start_time: string;
    duration_minutes: number;
    water_quantity_mm: number;
    notes?: string;
  }) => req<Schedule>('/schedules/manual', { method: 'POST', body: JSON.stringify(data) }),

  // Dashboard
  getDashboard: (farm_id: number) => req<DashboardSummary>(`/dashboard/${farm_id}`),

  // Weather
  getWeather: (farm_id: number, days = 16) =>
    req<WeatherDay[]>(`/weather/${farm_id}?days=${days}`),

  // Terrain
  getTerrainData: (lat: number, lng: number) =>
    req<{ elevation: number; slope: number; terrain_type: string; drainage_characteristics: string }>(
      `/terrain?lat=${lat}&lng=${lng}`
    ),

  // Notifications
  getNotifications: (params?: { farm_id?: number; unread_only?: boolean }) => {
    const qs = new URLSearchParams();
    if (params?.farm_id) qs.set('farm_id', String(params.farm_id));
    if (params?.unread_only) qs.set('unread_only', 'true');
    const query = qs.toString();
    return req<Notification[]>(`/notifications${query ? `?${query}` : ''}`);
  },
  markNotificationRead: (id: number) =>
    req<Notification>(`/notifications/${id}/read`, { method: 'PATCH' }),

  // Voice
  sendVoiceCommand: (text: string, language = 'en') =>
    req<{ intent: string; farm_id: number | null; response_text: string; schedules?: Schedule[]; next?: Schedule }>(
      '/voice/command',
      { method: 'POST', body: JSON.stringify({ text, language }) }
    ),
};
