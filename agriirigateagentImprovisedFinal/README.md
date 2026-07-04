# AgriIrrigate AI — Smart Irrigation Scheduling Engine

An AI-powered virtual irrigation manager. Instead of one-off recommendations,
it generates, tracks, and continuously updates full irrigation **schedules**
(today / 7-day / 30-day) per farm, with reasoning attached to every decision.

## Stack

| Piece               | Tech                                   | Key needed? |
|---------------------|-----------------------------------------|-------------|
| Frontend            | Next.js 16, React, Tailwind, FullCalendar, Leaflet, Recharts | No |
| Backend             | FastAPI                                | No |
| Database            | **SQLite** (local file, auto-created)  | No |
| Weather             | Open-Meteo                             | No |
| AI reasoning / voice NLU | Groq (Llama 3.3 70B) — optional    | Optional, free tier |

Everything runs with **zero signups**. If you don't set a `GROQ_API_KEY`, the
backend automatically falls back to a rule-based reasoning generator and a
keyword-based voice command parser, so the app is fully functional out of
the box. Add a free key later from https://console.groq.com to get richer,
LLM-generated reasoning text and multilingual (Tamil/Hindi) voice parsing.

## Project structure

```
backend/
  main.py               FastAPI app & routes
  database.py            SQLite storage layer (agriirrigate.db is created here)
  models.py               Pydantic request/response schemas
  scheduling_engine.py     Core AI scheduling logic (the primary feature)
  weather_service.py        Open-Meteo integration (keyless)
  ai_reasoning.py             Groq integration + rule-based fallback
  requirements.txt
  .env.example

frontend/
  app/
    page.tsx                Main app shell (Dashboard / Schedule / Map / Voice tabs)
    layout.tsx
    globals.css
    lib/api.ts               Typed API client
    components/
      Dashboard.tsx           Farm overview, stats, alerts
      ScheduleCalendar.tsx     FullCalendar view: drag-drop, edit, complete, delete
      AddManualSchedule.tsx    Manual irrigation entry modal
      FarmMap.tsx               Leaflet satellite map, farms colored by NDVI
  package.json
  tsconfig.json
```

## Running it locally

### One-command startup

From the project root, run:

```bash
npm install
npm run dev
```

This starts both the backend and frontend together.

### 1. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt
cp .env.example .env        # optionally paste in a GROQ_API_KEY
python main.py               # or: uvicorn main:app --reload --port 8000
```

The first run creates `backend/agriirrigate.db` automatically and seeds two
demo farms (Cotton, Tomato). The API is now at http://localhost:8000
(interactive docs at http://localhost:8000/docs).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000. If your backend runs somewhere other than
`localhost:8000`, set `NEXT_PUBLIC_API_URL` in a `frontend/.env.local` file.

## What to try first

1. Open the **Schedule** tab and click **Next 7 Days** — the engine pulls a
   real weather forecast for the farm's coordinates and generates a full
   schedule with reasoning for each entry.
2. Click any calendar event to see the AI's reasoning and confidence score,
   mark it complete, skip it, or delete it. Drag events to a new date/time —
   this auto-marks them "Rescheduled".
3. Try the **Voice** tab (Chrome recommended) — say "Schedule irrigation for
   tomorrow" or "What is my next irrigation?".
4. Check the **Satellite Map** tab for a farm-health overview colored by NDVI.

## Moving off SQLite later

Every other module talks to the database exclusively through the functions
in `database.py`. To move to a hosted Postgres/Supabase later, you only need
to rewrite that one file — no other backend or frontend code changes.
