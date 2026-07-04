"""
Automatic Schedule Optimization Service.

Continuously monitors weather changes, rain forecasts, soil moisture,
crop growth stage, and water availability. Automatically reschedules,
delays, skips, or adjusts irrigation when conditions change.
"""
from datetime import date, timedelta
import database as db
import weather_service
import crop_growth_service


def check_and_optimize_schedules(farm_id: int) -> list[dict]:
    """
    Check all upcoming schedules for a farm and optimize them based on
    current conditions. Returns list of changes made.
    """
    farm = db.get_farm(farm_id)
    if not farm:
        return []
    
    today = date.today()
    upcoming_schedules = db.list_schedules(
        farm_id=farm_id,
        date_from=today.isoformat(),
        date_to=(today + timedelta(days=7)).isoformat()
    )
    
    changes = []
    
    # Get current weather forecast
    forecast = weather_service.get_forecast(farm["latitude"], farm["longitude"], days=7)
    
    # Get current crop growth info
    crop_info = crop_growth_service.get_crop_info(farm["crop_type"], farm.get("sowing_date"))
    
    for schedule in upcoming_schedules:
        if schedule["status"] not in ["Scheduled", "Rescheduled"]:
            continue  # Skip already completed, running, or manually changed schedules
        
        if schedule["is_manual"]:
            continue  # Don't modify manually added schedules
        
        schedule_date = date.fromisoformat(schedule["date"])
        weather = weather_service.get_forecast_for_date(forecast, schedule["date"])
        
        if not weather:
            continue
        
        # Check for heavy rain forecast
        precipitation = weather.get("precipitation_mm", 0) or 0
        rain_prob = weather.get("rain_probability", 0) or 0
        heavy_rain_expected = precipitation >= 8 and rain_prob >= 60
        
        if heavy_rain_expected and schedule["status"] == "Scheduled":
            # Skip irrigation due to expected rain
            db.update_schedule(schedule["id"], {
                "status": "Auto Skipped",
                "water_quantity_mm": 0,
                "reason": f"Skipped due to heavy rain forecast ({precipitation}mm expected, {rain_prob}% probability)."
            })
            changes.append({
                "schedule_id": schedule["id"],
                "action": "skipped",
                "reason": "Heavy rain forecast"
            })
            
            # Create notification
            db.create_notification({
                "farm_id": farm_id,
                "type": "schedule_changed",
                "message": f"{farm['name']}: Irrigation on {schedule['date']} auto-skipped due to rain forecast.",
                "severity": "info"
            })
        
        # Check for unexpected dry conditions (no rain, high temp)
        elif precipitation < 2 and rain_prob < 20 and weather.get("temp_max", 30) >= 35:
            # Increase water quantity for hot, dry days
            current_water = schedule.get("water_quantity_mm", 15)
            if current_water < 25:
                new_water = min(30, current_water + 5)
                db.update_schedule(schedule["id"], {
                    "water_quantity_mm": new_water,
                    "reason": f"Increased water quantity due to hot, dry conditions (temp: {weather.get('temp_max')}°C)."
                })
                changes.append({
                    "schedule_id": schedule["id"],
                    "action": "increased_water",
                    "old_quantity": current_water,
                    "new_quantity": new_water,
                    "reason": "Hot, dry conditions"
                })
        
        # Check if growth stage has changed significantly
        current_stage = crop_info["growth_stage"]
        if current_stage != farm["growth_stage"]:
            # Regenerate schedules with new growth stage
            changes.append({
                "schedule_id": schedule["id"],
                "action": "growth_stage_changed",
                "old_stage": farm["growth_stage"],
                "new_stage": current_stage,
                "reason": "Crop growth stage changed"
            })
    
    # Check for low soil moisture warning
    if farm["soil_moisture"] < 30:
        db.create_notification({
            "farm_id": farm_id,
            "type": "low_soil_moisture",
            "message": f"{farm['name']}: Soil moisture is critically low ({farm['soil_moisture']}%). Consider immediate irrigation.",
            "severity": "warning"
        })
    
    # Check for upcoming harvest
    if crop_info.get("days_to_harvest") and crop_info["days_to_harvest"] <= 7:
        db.create_notification({
            "farm_id": farm_id,
            "type": "harvest_approaching",
            "message": f"{farm['name']}: Harvest approaching in {crop_info['days_to_harvest']} days. Reduce irrigation.",
            "severity": "info"
        })
    
    # Check for disease risk increase
    if farm.get("disease_risk") == "high" and rain_prob > 70:
        db.create_notification({
            "farm_id": farm_id,
            "type": "disease_risk",
            "message": f"{farm['name']}: High disease risk with expected rain. Consider fungicide application.",
            "severity": "warning"
        })
    
    # Check for water stress
    if farm["soil_moisture"] < 40 and farm["growth_stage"] in ["flowering", "fruiting"]:
        db.create_notification({
            "farm_id": farm_id,
            "type": "water_stress",
            "message": f"{farm['name']}: Water stress during critical {farm['growth_stage']} stage. Immediate irrigation recommended.",
            "severity": "warning"
        })
    
    # Check for overwatering risk
    if farm["soil_moisture"] > 80 and precipitation > 5:
        db.create_notification({
            "farm_id": farm_id,
            "type": "overwatering_risk",
            "message": f"{farm['name']}: Risk of overwatering with high soil moisture and expected rain.",
            "severity": "warning"
        })
    
    return changes


def optimize_all_farms() -> dict:
    """
    Run optimization for all farms. Returns summary of changes.
    """
    farms = db.list_farms()
    total_changes = []
    
    for farm in farms:
        changes = check_and_optimize_schedules(farm["id"])
        if changes:
            total_changes.extend(changes)
    
    return {
        "farms_checked": len(farms),
        "total_changes": len(total_changes),
        "changes": total_changes
    }
