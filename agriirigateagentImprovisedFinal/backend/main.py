from datetime import date, timedelta

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import database as db
import scheduling_engine
import weather_service
import ai_reasoning
import terrain_service
import crop_growth_service
import schedule_optimizer
from models import (
    FarmCreate, FarmUpdate, ScheduleGenerateRequest, ScheduleUpdate,
    ManualScheduleCreate, VoiceCommandRequest, NotificationCreate,
)

app = FastAPI(title="AgriIrrigate AI Backend - Smart Irrigation Scheduling Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    db.init_db()


@app.get("/")
def root():
    return {"message": "AgriIrrigate Backend is running!", "engine": "Smart Irrigation Scheduling Engine v1"}


# ---------------- Farms ----------------

@app.get("/farms")
def get_farms():
    return db.list_farms()


@app.get("/farms/{farm_id}")
def get_farm(farm_id: int):
    farm = db.get_farm(farm_id)
    if not farm:
        raise HTTPException(404, "Farm not found")
    return farm


@app.post("/farms")
def create_farm(payload: FarmCreate):
    return db.create_farm(payload.model_dump())


@app.patch("/farms/{farm_id}")
def update_farm(farm_id: int, payload: FarmUpdate):
    farm = db.update_farm(farm_id, payload.model_dump(exclude_unset=True))
    if not farm:
        raise HTTPException(404, "Farm not found")
    return farm


# ---------------- Scheduling engine ----------------

@app.post("/schedules/generate")
def generate_schedules(payload: ScheduleGenerateRequest):
    if payload.range not in scheduling_engine.RANGE_DAYS:
        raise HTTPException(400, "range must be one of: today, 7day, 30day")
    try:
        created = scheduling_engine.generate_schedule(payload.farm_id, payload.range)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"count": len(created), "schedules": created}


@app.get("/schedules")
def get_schedules(farm_id: int | None = None, date_from: str | None = None, date_to: str | None = None):
    return db.list_schedules(farm_id=farm_id, date_from=date_from, date_to=date_to)


@app.get("/schedules/{schedule_id}")
def get_schedule(schedule_id: int):
    s = db.get_schedule(schedule_id)
    if not s:
        raise HTTPException(404, "Schedule not found")
    return s


@app.patch("/schedules/{schedule_id}")
def update_schedule(schedule_id: int, payload: ScheduleUpdate):
    existing = db.get_schedule(schedule_id)
    if not existing:
        raise HTTPException(404, "Schedule not found")

    updates = payload.model_dump(exclude_unset=True)
    # if the date or time moved (drag-and-drop / manual edit), mark as Rescheduled
    date_changed = "date" in updates and updates["date"] != existing["date"]
    time_changed = "start_time" in updates and updates["start_time"] != existing["start_time"]
    if (date_changed or time_changed) and "status" not in updates:
        updates["status"] = "Rescheduled"

    if updates.get("status") == "Completed":
        db.add_history({
            "farm_id": existing["farm_id"], "schedule_id": schedule_id,
            "date": updates.get("date", existing["date"]),
            "water_used_mm": updates.get("water_quantity_mm", existing["water_quantity_mm"]),
            "status": "Completed",
        })

    updated = db.update_schedule(schedule_id, updates)
    return updated


@app.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: int):
    ok = db.delete_schedule(schedule_id)
    if not ok:
        raise HTTPException(404, "Schedule not found")
    return {"deleted": True}


@app.post("/schedules/manual")
def create_manual_schedule(payload: ManualScheduleCreate):
    farm = db.get_farm(payload.farm_id)
    if not farm:
        raise HTTPException(404, "Farm not found")
    method = payload.irrigation_method or farm["irrigation_method"]
    sq_m_per_acre = 4046.86
    usage_liters = round(payload.water_quantity_mm * farm["farm_size_acres"] * sq_m_per_acre, 0)
    start_h, start_m = map(int, payload.start_time.split(":"))
    end_minutes = start_h * 60 + start_m + payload.duration_minutes
    end_time = f"{end_minutes // 60:02d}:{end_minutes % 60:02d}"

    record = db.create_schedule({
        "farm_id": payload.farm_id, "date": payload.date,
        "start_time": payload.start_time, "end_time": end_time,
        "duration_minutes": payload.duration_minutes,
        "water_quantity_mm": payload.water_quantity_mm, "irrigation_method": method,
        "estimated_water_usage_liters": usage_liters, "status": "Scheduled",
        "reason": payload.notes or "Manually added by farmer.",
        "confidence_score": 1.0, "is_manual": True,
    })
    return record


# ---------------- Dashboard ----------------

@app.get("/dashboard/{farm_id}")
def get_dashboard(farm_id: int):
    farm = db.get_farm(farm_id)
    if not farm:
        raise HTTPException(404, "Farm not found")

    today = date.today().isoformat()
    all_schedules = db.list_schedules(farm_id=farm_id)
    upcoming = [s for s in all_schedules if s["date"] >= today and s["status"] == "Scheduled"]
    running = [s for s in all_schedules if s["status"] == "Running"]
    missed = [s for s in all_schedules if s["date"] < today and s["status"] == "Scheduled"]
    completed = [s for s in all_schedules if s["status"] == "Completed"]
    next_task = sorted(upcoming, key=lambda s: (s["date"], s["start_time"] or ""))[:1]
    total_water_liters = sum(s.get("estimated_water_usage_liters") or 0 for s in completed)

    return {
        "farm": farm,
        "upcoming_count": len(upcoming),
        "running_count": len(running),
        "missed_count": len(missed),
        "completed_count": len(completed),
        "total_water_usage_liters": total_water_liters,
        "next_scheduled_task": next_task[0] if next_task else None,
        "notifications": db.list_notifications(farm_id=farm_id, unread_only=True)[:10],
    }


@app.get("/dashboard")
def get_overview_dashboard():
    farms = db.list_farms()
    today = date.today().isoformat()
    overview = []
    for farm in farms:
        schedules = db.list_schedules(farm_id=farm["id"])
        upcoming = [s for s in schedules if s["date"] >= today and s["status"] == "Scheduled"]
        next_task = sorted(upcoming, key=lambda s: (s["date"], s["start_time"] or ""))[:1]
        overview.append({
            "farm": farm,
            "upcoming_count": len(upcoming),
            "next_scheduled_task": next_task[0] if next_task else None,
        })
    return {
        "farms": overview,
        "unread_notifications": db.list_notifications(unread_only=True)[:15],
    }


# ---------------- Weather ----------------

@app.get("/weather/{farm_id}")
def get_weather(farm_id: int, days: int = 16):
    farm = db.get_farm(farm_id)
    if not farm:
        raise HTTPException(404, "Farm not found")
    return weather_service.get_forecast(farm["latitude"], farm["longitude"], days=days)


# ---------------- Terrain ----------------

@app.get("/terrain")
def get_terrain(lat: float, lng: float):
    return terrain_service.get_terrain_data(lat, lng)


# ---------------- Crop Growth ----------------

@app.get("/crop-info/{farm_id}")
def get_crop_info(farm_id: int):
    farm = db.get_farm(farm_id)
    if not farm:
        raise HTTPException(404, "Farm not found")
    return crop_growth_service.get_crop_info(farm["crop_type"], farm.get("sowing_date"))


# ---------------- Schedule Optimization ----------------

@app.post("/optimize/{farm_id}")
def optimize_farm_schedules(farm_id: int):
    farm = db.get_farm(farm_id)
    if not farm:
        raise HTTPException(404, "Farm not found")
    changes = schedule_optimizer.check_and_optimize_schedules(farm_id)
    return {"farm_id": farm_id, "changes": changes}

@app.post("/optimize/all")
def optimize_all_schedules():
    return schedule_optimizer.optimize_all_farms()


# ---------------- Notifications ----------------

@app.get("/notifications")
def get_notifications(farm_id: int | None = None, unread_only: bool = False):
    return db.list_notifications(farm_id=farm_id, unread_only=unread_only)


@app.post("/notifications")
def create_notification(payload: NotificationCreate):
    return db.create_notification(payload.model_dump())


@app.patch("/notifications/{notification_id}/read")
def mark_read(notification_id: int):
    n = db.mark_notification_read(notification_id)
    if not n:
        raise HTTPException(404, "Notification not found")
    return n


# ---------------- Voice scheduler ----------------

@app.post("/voice/command")
def voice_command(payload: VoiceCommandRequest):
    farms = db.list_farms()
    parsed = ai_reasoning.parse_voice_command(payload.text, farms)
    intent = parsed.get("intent")
    farm_id = parsed.get("farm_id")
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    result = {"intent": intent, "farm_id": farm_id, "response_text": parsed.get("response_text", "")}

    if intent == "schedule_irrigation" and farm_id:
        created = scheduling_engine.generate_schedule(farm_id, "7day")
        result["schedules"] = created
    elif intent == "show_schedule":
        result["schedules"] = db.list_schedules(farm_id=farm_id, date_from=today,
                                                  date_to=(date.today() + timedelta(days=7)).isoformat())
    elif intent == "next_irrigation":
        upcoming = [s for s in db.list_schedules(farm_id=farm_id) if s["date"] >= today and s["status"] == "Scheduled"]
        upcoming = sorted(upcoming, key=lambda s: (s["date"], s["start_time"] or ""))
        result["next"] = upcoming[0] if upcoming else None
    elif intent in ("postpone", "cancel_irrigation") and farm_id:
        todays = [s for s in db.list_schedules(farm_id=farm_id, date_from=today, date_to=today)]
        for s in todays:
            if intent == "postpone":
                db.update_schedule(s["id"], {"date": tomorrow, "status": "Rescheduled"})
            else:
                db.update_schedule(s["id"], {"status": "Skipped"})
        result["affected"] = len(todays)

    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
