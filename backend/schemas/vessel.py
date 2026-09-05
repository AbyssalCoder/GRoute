from datetime import datetime
from pydantic import BaseModel, Field
from .common import FeatureCollection

class Vessel(BaseModel):
    vessel_id: str
    mmsi: str | None = None
    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    speed: float = 0.0
    course: float = 0.0
    heading: float = 0.0
    destination: str | None = None
    timestamp: datetime
    source: str = "Historical AIS Replay"

class VesselCollection(BaseModel):
    vessels: list[Vessel]
    trails: FeatureCollection
