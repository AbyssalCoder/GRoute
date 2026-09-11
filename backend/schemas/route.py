from datetime import datetime
from pydantic import BaseModel, Field
from .common import FeatureCollection, Position, GeoJSONFeature

class VesselConfig(BaseModel):
    speed_knots: float = Field(default=10, gt=0, le=40)
    ice_class: str = "research"
    fuel_rate: float = Field(default=1.0, gt=0)
    max_safe_ice_concentration: float = Field(default=0.65, ge=0, le=1)
    safety_buffer_km: float = Field(default=10, ge=0)

class TrackedShip(BaseModel):
    vessel_id: str
    name: str
    latitude: float
    longitude: float
    destination: str | None = None

class RouteRequest(BaseModel):
    vessel_id: str = Field(min_length=3)
    start: Position = Position(latitude=-66, longitude=-54)
    destination: Position
    departure_time: datetime
    mode: str = "balanced"
    vessel: VesselConfig = VesselConfig()
    safety_weight: float = Field(default=0.6, ge=0, le=1)

class RouteMetrics(BaseModel):
    distance_km: float
    travel_time_hours: float
    fuel_estimate: float
    iceberg_risk: float
    sea_ice_risk: float
    weather_risk: float
    explanation: str
    reasons: list[str] = Field(default_factory=list)

class RouteComparison(BaseModel):
    mode: str
    distance_km: float
    travel_time_hours: float
    fuel_estimate: float
    fuel_saved_vs_shortest: float
    fuel_savings_percent: float
    kilometers_saved_vs_shortest: float
    distance_reduction_percent: float
    reasons: list[str] = Field(default_factory=list)

class RouteResponse(BaseModel):
    mode: str
    ship: TrackedShip
    route: GeoJSONFeature
    ship_route_segments: FeatureCollection
    iceberg_routes: FeatureCollection
    metrics: RouteMetrics
    comparison_baseline: str = "shortest"
    comparison: list[RouteComparison] = Field(default_factory=list)
