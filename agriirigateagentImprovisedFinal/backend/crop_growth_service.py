"""
Dynamic Crop Growth Tracking Service.

Calculates crop age, determines growth stages automatically based on
crop-specific rules, and provides water requirement estimates.
"""
from datetime import date, timedelta
from typing import Optional

# Crop-specific growth stage definitions (days after sowing)
# Format: {crop_type: {stage_name: day_range}}
CROP_GROWTH_STAGES = {
    "rice": {
        "seedling": (0, 20),
        "vegetative": (21, 45),
        "tillering": (46, 70),
        "flowering": (71, 100),
        "grain_filling": (101, 130),
        "maturity": (131, 160),
    },
    "wheat": {
        "seedling": (0, 15),
        "vegetative": (16, 40),
        "tillering": (41, 60),
        "flowering": (61, 85),
        "grain_filling": (86, 110),
        "maturity": (111, 130),
    },
    "cotton": {
        "seedling": (0, 25),
        "vegetative": (26, 60),
        "flowering": (61, 100),
        "fruiting": (101, 140),
        "maturity": (141, 180),
    },
    "tomato": {
        "seedling": (0, 20),
        "vegetative": (21, 45),
        "flowering": (46, 70),
        "fruiting": (71, 100),
        "maturity": (101, 120),
    },
    "sugarcane": {
        "seedling": (0, 30),
        "vegetative": (31, 90),
        "tillering": (91, 150),
        "grand_growth": (151, 270),
        "maturity": (271, 360),
    },
    "maize": {
        "seedling": (0, 15),
        "vegetative": (16, 40),
        "flowering": (41, 65),
        "grain_filling": (66, 90),
        "maturity": (91, 110),
    },
    "potato": {
        "seedling": (0, 15),
        "vegetative": (16, 40),
        "tuber_initiation": (41, 60),
        "tuber_bulking": (61, 90),
        "maturity": (91, 110),
    },
    "soybean": {
        "seedling": (0, 15),
        "vegetative": (16, 40),
        "flowering": (41, 65),
        "pod_filling": (66, 90),
        "maturity": (91, 110),
    },
    "groundnut": {
        "seedling": (0, 15),
        "vegetative": (16, 35),
        "flowering": (36, 60),
        "pod_development": (61, 85),
        "maturity": (86, 105),
    },
}

# Default growth stages for unknown crops
DEFAULT_GROWTH_STAGES = {
    "seedling": (0, 20),
    "vegetative": (21, 50),
    "flowering": (51, 80),
    "fruiting": (81, 110),
    "maturity": (111, 140),
}

# Crop water requirements (mm per day) by growth stage
CROP_WATER_REQUIREMENTS = {
    "rice": {
        "seedling": 4.0, "vegetative": 6.0, "tillering": 8.0, 
        "flowering": 10.0, "grain_filling": 8.0, "maturity": 5.0
    },
    "wheat": {
        "seedling": 3.0, "vegetative": 4.5, "tillering": 5.5,
        "flowering": 6.0, "grain_filling": 5.0, "maturity": 3.0
    },
    "cotton": {
        "seedling": 3.5, "vegetative": 5.0, "flowering": 7.0,
        "fruiting": 6.5, "maturity": 4.0
    },
    "tomato": {
        "seedling": 3.0, "vegetative": 4.5, "flowering": 6.0,
        "fruiting": 5.5, "maturity": 3.5
    },
    "sugarcane": {
        "seedling": 4.0, "vegetative": 6.0, "tillering": 8.0,
        "grand_growth": 10.0, "maturity": 6.0
    },
    "maize": {
        "seedling": 3.0, "vegetative": 4.5, "flowering": 6.0,
        "grain_filling": 5.0, "maturity": 3.0
    },
    "potato": {
        "seedling": 3.0, "vegetative": 4.5, "tuber_initiation": 5.5,
        "tuber_bulking": 6.0, "maturity": 3.5
    },
    "soybean": {
        "seedling": 3.0, "vegetative": 4.0, "flowering": 5.5,
        "pod_filling": 5.0, "maturity": 3.0
    },
    "groundnut": {
        "seedling": 3.0, "vegetative": 4.0, "flowering": 5.0,
        "pod_development": 4.5, "maturity": 3.0
    },
}

DEFAULT_WATER_REQUIREMENTS = {
    "seedling": 3.0, "vegetative": 4.5, "flowering": 6.0,
    "fruiting": 5.5, "maturity": 3.5
}


def calculate_crop_age(sowing_date: str) -> Optional[int]:
    """
    Calculate crop age in days from sowing date.
    Returns None if sowing date is not provided or invalid.
    """
    if not sowing_date:
        return None
    
    try:
        sowing = date.fromisoformat(sowing_date)
        today = date.today()
        age = (today - sowing).days
        return max(0, age)
    except ValueError:
        return None


def determine_growth_stage(crop_type: str, crop_age: Optional[int]) -> str:
    """
    Determine the current growth stage based on crop type and age.
    Returns 'vegetative' as default if age is unknown.
    """
    if crop_age is None:
        return "vegetative"
    
    crop_type_lower = crop_type.lower()
    stages = CROP_GROWTH_STAGES.get(crop_type_lower, DEFAULT_GROWTH_STAGES)
    
    for stage, (start_day, end_day) in stages.items():
        if start_day <= crop_age <= end_day:
            return stage
    
    # If age exceeds all defined stages, return maturity
    if crop_age > max(end_day for _, end_day in stages.values()):
        return "maturity"
    
    # If age is before first stage, return seedling
    return "seedling"


def get_crop_water_requirement(crop_type: str, growth_stage: str) -> float:
    """
    Get water requirement (mm per day) for a crop at a specific growth stage.
    """
    crop_type_lower = crop_type.lower()
    requirements = CROP_WATER_REQUIREMENTS.get(crop_type_lower, DEFAULT_WATER_REQUIREMENTS)
    return requirements.get(growth_stage, DEFAULT_WATER_REQUIREMENTS.get(growth_stage, 4.5))


def estimate_harvest_date(crop_type: str, sowing_date: str) -> Optional[str]:
    """
    Estimate harvest date based on crop type and sowing date.
    Returns None if sowing date is not provided.
    """
    if not sowing_date:
        return None
    
    try:
        sowing = date.fromisoformat(sowing_date)
        crop_type_lower = crop_type.lower()
        stages = CROP_GROWTH_STAGES.get(crop_type_lower, DEFAULT_GROWTH_STAGES)
        
        # Get the maximum days for maturity
        max_days = max(end_day for _, end_day in stages.values())
        harvest_date = sowing + timedelta(days=max_days)
        
        return harvest_date.isoformat()
    except ValueError:
        return None


def get_crop_info(crop_type: str, sowing_date: Optional[str] = None) -> dict:
    """
    Get comprehensive crop information including age, growth stage,
    water requirement, and estimated harvest date.
    """
    crop_age = calculate_crop_age(sowing_date) if sowing_date else None
    growth_stage = determine_growth_stage(crop_type, crop_age)
    water_requirement = get_crop_water_requirement(crop_type, growth_stage)
    harvest_date = estimate_harvest_date(crop_type, sowing_date) if sowing_date else None
    
    return {
        "crop_type": crop_type,
        "sowing_date": sowing_date,
        "crop_age_days": crop_age,
        "growth_stage": growth_stage,
        "daily_water_requirement_mm": water_requirement,
        "estimated_harvest_date": harvest_date,
        "days_to_harvest": None if not harvest_date or not crop_age else max(0, 
            (date.fromisoformat(harvest_date) - date.today()).days),
    }
