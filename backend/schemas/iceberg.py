from datetime import datetime
from pydantic import BaseModel, Field
from .common import FeatureCollection, Position

class IcebergRecord(BaseModel):
    id: str
    timestamp: datetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    velocity_u: float = 0.0
    velocity_v: float = 0.0
    speed: float = 0.0
    heading: float = 0.0
    source: str = "demo"
    confidence: float = Field(default=0.8, ge=0, le=1)

class IcebergPrediction(BaseModel):
    timestamp: datetime
    latitude: float
    longitude: float
    uncertainty_km: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)

class IcebergTrajectory(BaseModel):
    iceberg_id: str
    model: str
    predictions: list[IcebergPrediction]
    geojson: FeatureCollection
