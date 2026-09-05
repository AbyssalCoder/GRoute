from datetime import datetime
from pydantic import BaseModel, Field

class MarinePoint(BaseModel):
    timestamp: datetime
    latitude: float
    longitude: float
    wave_height_m: float = Field(ge=0)
    wave_period_s: float = Field(ge=0)
    sea_surface_temperature_c: float
    current_speed_ms: float = Field(ge=0)
    current_direction_deg: float = Field(ge=0, lt=360)

class SeaIcePoint(BaseModel):
    timestamp: datetime
    latitude: float
    longitude: float
    concentration: float = Field(ge=0, le=1)
    source: str

class ModelStatus(BaseModel):
    iceberg_model: str
    sea_ice_model: str
    route_optimizer: str
    data_sources: dict[str, str]
