from backend.models.iceberg.physics_model import predict_physics
from backend.models.iceberg.random_forest_model import load_artifact, predict_daily_motion
from backend.schemas.iceberg import IcebergRecord, IcebergPrediction
from datetime import timedelta
from math import atan2, cos, exp, radians, sin, sqrt

def _environmental_drift(environment: dict | None) -> tuple[float, float]:
    if not environment:
        return 0.0, 0.0
    speed = float(environment.get("current_speed_ms", 0) or 0)
    direction = radians(float(environment.get("current_direction_deg", 0) or 0))
    wind_speed = float(environment.get("wind_speed_ms", 0) or 0) * 0.03
    wind_direction = radians(float(environment.get("wind_direction_deg", 0) or 0))
    return (speed * cos(direction) + wind_speed * cos(wind_direction)) * 86400 / 1000, (speed * sin(direction) + wind_speed * sin(wind_direction)) * 86400 / 1000

def _cap_lifetime_displacement(origin_lat: float, origin_lon: float, latitude: float, longitude: float, max_km: float = 2500.0) -> tuple[float, float]:
    earth_radius = 6371.0088
    lat1, lat2 = radians(origin_lat), radians(latitude)
    delta_lat, delta_lon = radians(latitude - origin_lat), radians(longitude - origin_lon)
    haversine = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    distance = 2 * earth_radius * atan2(sqrt(haversine), sqrt(max(0.0, 1 - haversine)))
    if distance <= max_km:
        return latitude, longitude
    bearing = atan2(sin(delta_lon) * cos(lat2), cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(delta_lon))
    capped_lat = origin_lat + (max_km * cos(bearing)) / 111.195
    capped_lon = origin_lon + (max_km * sin(bearing)) / (111.195 * max(0.1, abs(cos(radians(capped_lat)))))
    return max(-90, min(90, capped_lat)), ((capped_lon + 180) % 360) - 180

class IcebergPredictor:
    def __init__(self, ml_available: bool = True) -> None:
        self.artifact = load_artifact() if ml_available else None
        self.ml_available = self.artifact is not None

    @property
    def model_name(self) -> str:
        return "iceberg_hybrid_v1" if self.ml_available else "physics_baseline_v1"

    def predict(self, record: IcebergRecord, horizon_hours: int = 48, environment: dict | None = None) -> list[IcebergPrediction]:
        if not self.artifact:
            return predict_physics(record, hours=horizon_hours)
        lat, lon = record.latitude, record.longitude
        timestamp = record.timestamp
        north_delta = record.velocity_v * 86400 / 1000
        east_delta = record.velocity_u * 86400 / 1000
        environmental_north, environmental_east = _environmental_drift(environment)
        predictions = []
        for hour in range(1, horizon_hours + 1):
            if hour % 24 == 1 and hour > 1:
                north_delta, east_delta = predict_daily_motion(self.artifact["model"], lat, lon, north_delta, east_delta, timestamp, record.speed * 86400 / 1000)
                north_delta += environmental_north
                east_delta += environmental_east
            long_range_decay = exp(-max(0, hour - 720) / 2160)
            lat += north_delta * long_range_decay / 111.195 / 24
            lon += east_delta * long_range_decay / (111.195 * max(0.1, abs(cos(radians(lat)))) * 24)
            lat, lon = _cap_lifetime_displacement(record.latitude, record.longitude, lat, lon)
            timestamp += timedelta(hours=1)
            predictions.append(IcebergPrediction(timestamp=timestamp, latitude=max(-90, min(90, lat)), longitude=((lon + 180) % 360) - 180, uncertainty_km=1.2 + 0.2 * hour, confidence=max(0.4, exp(-hour / 96))))
        return predictions
