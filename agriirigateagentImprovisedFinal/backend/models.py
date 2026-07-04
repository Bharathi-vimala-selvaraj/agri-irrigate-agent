from pydantic import BaseModel, Field
from typing import Optional


class FarmCreate(BaseModel):
    name: str
    crop_type: str
    crop_variety: str | None = None
    growth_stage: str = "vegetative"
    sowing_date: str | None = None
    farm_size_acres: float = 2.0
    irrigation_method: str = "drip"
    soil_type: str = "loam"
    water_source: str = "well"
    pump_capacity_hp: float | None = None
    ndvi: float = 0.65
    soil_moisture: float = 55.0
    disease_risk: str = "low"
    latitude: float = 11.0168
    longitude: float = 76.9558
    elevation: float | None = None
    slope: float | None = None
    terrain_type: str | None = None
    drainage_characteristics: str | None = None


class FarmUpdate(BaseModel):
    name: Optional[str] = None
    crop_type: Optional[str] = None
    crop_variety: Optional[str] = None
    growth_stage: Optional[str] = None
    sowing_date: Optional[str] = None
    farm_size_acres: Optional[float] = None
    irrigation_method: Optional[str] = None
    soil_type: Optional[str] = None
    water_source: Optional[str] = None
    pump_capacity_hp: Optional[float] = None
    ndvi: Optional[float] = None
    soil_moisture: Optional[float] = None
    disease_risk: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation: Optional[float] = None
    slope: Optional[float] = None
    terrain_type: Optional[str] = None
    drainage_characteristics: Optional[str] = None


class ScheduleGenerateRequest(BaseModel):
    farm_id: int
    range: str = Field(description="'today', '7day', or '30day'")


class ScheduleUpdate(BaseModel):
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    water_quantity_mm: Optional[float] = None
    status: Optional[str] = None
    reason: Optional[str] = None


class ManualScheduleCreate(BaseModel):
    farm_id: int
    date: str
    start_time: str
    duration_minutes: int = 30
    water_quantity_mm: float = 15.0
    irrigation_method: Optional[str] = None
    notes: Optional[str] = None


class VoiceCommandRequest(BaseModel):
    text: str
    language: str = "en"


class NotificationCreate(BaseModel):
    farm_id: Optional[int] = None
    type: str
    message: str
    severity: str = "info"
