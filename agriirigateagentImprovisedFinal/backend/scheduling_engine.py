"""
Core AI Irrigation Scheduling Engine.

Given a farm and a date range, this walks day-by-day through the weather
forecast, simulates soil moisture depletion/replenishment, and decides
whether each day needs irrigation, should be auto-skipped for rain, or
needs no action. This is the primary feature of the app - everything else
(dashboard, notifications, voice) reads from what this produces.
"""
from datetime import date, timedelta

import database as db
import weather_service
import ai_reasoning
import crop_growth_service

# Crop coefficients (Kc) by growth stage - simplified FAO-56 style values.
CROP_KC = {
    "cotton": {"seedling": 0.35, "vegetative": 0.75, "flowering": 1.15, "fruiting": 1.10, "maturity": 0.6},
    "tomato": {"seedling": 0.4, "vegetative": 0.75, "flowering": 1.15, "fruiting": 1.05, "maturity": 0.6},
    "wheat": {"seedling": 0.3, "vegetative": 0.7, "flowering": 1.1, "fruiting": 1.0, "maturity": 0.4},
    "rice": {"seedling": 1.0, "vegetative": 1.1, "flowering": 1.2, "fruiting": 1.05, "maturity": 0.75},
    "sugarcane": {"seedling": 0.4, "vegetative": 0.9, "flowering": 1.25, "fruiting": 1.1, "maturity": 0.7},
    "default": {"seedling": 0.4, "vegetative": 0.75, "flowering": 1.1, "fruiting": 1.0, "maturity": 0.6},
}

# mm of water delivered per minute, by irrigation method
DELIVERY_RATE_MM_PER_MIN = {"drip": 0.12, "sprinkler": 0.28, "flood": 0.5}

MOISTURE_THRESHOLD = {"seedling": 55, "vegetative": 48, "flowering": 45, "fruiting": 45, "maturity": 35}
SQ_METERS_PER_ACRE = 4046.86
RANGE_DAYS = {"today": 1, "7day": 7, "30day": 30}


def _kc(crop_type: str, stage: str) -> float:
    table = CROP_KC.get(crop_type.lower(), CROP_KC["default"])
    return table.get(stage, table["vegetative"])


def _moisture_threshold(stage: str) -> float:
    return MOISTURE_THRESHOLD.get(stage, 45)


def _round_to_5(minutes: float) -> int:
    return max(5, int(round(minutes / 5.0) * 5))


def generate_schedule(farm_id: int, range_key: str) -> list[dict]:
    farm = db.get_farm(farm_id)
    if not farm:
        raise ValueError(f"Farm {farm_id} not found")

    days = RANGE_DAYS.get(range_key, 7)
    today = date.today()
    date_from = today.isoformat()
    date_to = (today + timedelta(days=days - 1)).isoformat()

    # Clear previously auto-generated (not manual, not already running/completed)
    # entries in this window so regeneration doesn't duplicate.
    db.delete_schedules_for_farm_in_range(farm_id, date_from, date_to, only_status="Scheduled")
    db.delete_schedules_for_farm_in_range(farm_id, date_from, date_to, only_status="Auto Skipped")

    forecast = weather_service.get_forecast(farm["latitude"], farm["longitude"], days=days)
    
    # Get dynamic crop growth information
    crop_info = crop_growth_service.get_crop_info(farm["crop_type"], farm.get("sowing_date"))
    stage = crop_info["growth_stage"]
    crop = farm["crop_type"]
    method = farm["irrigation_method"]
    kc = _kc(crop, stage)
    threshold = _moisture_threshold(stage)
    delivery_rate = DELIVERY_RATE_MM_PER_MIN.get(method, 0.2)
    
    # Adjust threshold based on terrain slope (steeper slopes drain faster)
    slope = farm.get("slope", 0)
    if slope > 10:
        threshold -= 2  # Lower threshold for steep slopes (faster drainage)
    elif slope < 2:
        threshold += 2  # Higher threshold for flat areas (poor drainage)
    
    # Adjust water quantity based on soil type
    soil_type = farm.get("soil_type", "loam").lower()
    soil_adjustment = 1.0
    if soil_type == "sandy":
        soil_adjustment = 1.3  # Sandy soil needs more water
    elif soil_type == "clay":
        soil_adjustment = 0.8  # Clay soil retains water better
    
    # Update farm's growth stage if it has changed
    if stage != farm["growth_stage"]:
        db.update_farm(farm_id, {"growth_stage": stage})

    soil_moisture = farm["soil_moisture"]
    created = []

    for i in range(days):
        day = today + timedelta(days=i)
        weather = weather_service.get_forecast_for_date(forecast, day.isoformat())
        if not weather:
            continue

        et0 = weather.get("et0") or 4.0
        daily_need = et0 * kc
        precipitation = weather.get("precipitation_mm", 0) or 0
        rain_prob = weather.get("rain_probability", 0) or 0
        heavy_rain_expected = precipitation >= 8 and rain_prob >= 60

        # Deplete moisture by crop water use, replenish by rainfall.
        # Tuned so a single irrigation event covers several days before the
        # next is due (matches real drip/sprinkler cycles), rather than
        # triggering every single day.
        soil_moisture -= daily_need * 1.3
        soil_moisture += precipitation * 2.0
        soil_moisture = max(5.0, min(95.0, soil_moisture))

        needs_irrigation = soil_moisture < threshold

        if not needs_irrigation:
            continue  # no action needed this day - table stays sparse, as intended

        if heavy_rain_expected:
            decision = {
                "status": "Auto Skipped",
                "water_quantity_mm": 0,
                "soil_moisture_low": True,
                "confidence_score": min(0.97, 0.6 + rain_prob / 150),
            }
            reasoning = ai_reasoning.generate_reasoning(
                farm["name"], crop, stage, decision, weather, farm["disease_risk"]
            )
            record = db.create_schedule({
                "farm_id": farm_id, "date": day.isoformat(),
                "start_time": None, "end_time": None, "duration_minutes": 0,
                "water_quantity_mm": 0, "irrigation_method": method,
                "estimated_water_usage_liters": 0, "status": "Auto Skipped",
                "reason": reasoning, "confidence_score": decision["confidence_score"],
                "weather_considered": weather,
            })
            created.append(record)
            if i == 0:
                db.create_notification({
                    "farm_id": farm_id, "type": "schedule_changed",
                    "message": f"{farm['name']}: irrigation auto-skipped, rain expected.",
                    "severity": "info",
                })
        else:
            # apply a multi-day supply in one pass so the field isn't watered daily
            water_mm = round(min(35, max(12, daily_need * 3.5 * soil_adjustment)), 1)
            duration = _round_to_5(water_mm / delivery_rate)
            start_hour, start_min = (5, 30) if weather.get("temp_max", 30) >= 36 else (6, 0)
            start_dt_minutes = start_hour * 60 + start_min
            end_dt_minutes = start_dt_minutes + duration
            start_time = f"{start_dt_minutes // 60:02d}:{start_dt_minutes % 60:02d}"
            end_time = f"{end_dt_minutes // 60:02d}:{end_dt_minutes % 60:02d}"
            # 1 mm of water over 1 m2 = 1 liter
            usage_liters = round(water_mm * farm["farm_size_acres"] * SQ_METERS_PER_ACRE, 0)

            decision = {
                "status": "Scheduled", "water_quantity_mm": water_mm,
                "soil_moisture_low": True,
                "confidence_score": round(max(0.65, 0.95 - rain_prob / 250), 2),
            }
            reasoning = ai_reasoning.generate_reasoning(
                farm["name"], crop, stage, decision, weather, farm["disease_risk"]
            )
            record = db.create_schedule({
                "farm_id": farm_id, "date": day.isoformat(),
                "start_time": start_time, "end_time": end_time, "duration_minutes": duration,
                "water_quantity_mm": water_mm, "irrigation_method": method,
                "estimated_water_usage_liters": usage_liters, "status": "Scheduled",
                "reason": reasoning, "confidence_score": decision["confidence_score"],
                "weather_considered": weather,
            })
            created.append(record)
            soil_moisture = min(95.0, soil_moisture + water_mm * 1.5)

            if i == 0 and farm["disease_risk"] in ("medium", "high"):
                db.create_notification({
                    "farm_id": farm_id, "type": "disease_risk",
                    "message": f"{farm['name']}: {farm['disease_risk']} disease risk - "
                               f"consider drip over sprinkler to limit leaf wetness.",
                    "severity": "warning",
                })

    # persist the simulated end-state moisture back onto the farm record
    db.update_farm(farm_id, {"soil_moisture": round(soil_moisture, 1)})

    if soil_moisture < 30:
        db.create_notification({
            "farm_id": farm_id, "type": "low_soil_moisture",
            "message": f"{farm['name']}: soil moisture projected to drop below 30% - "
                       f"monitor closely.",
            "severity": "warning",
        })

    return created
