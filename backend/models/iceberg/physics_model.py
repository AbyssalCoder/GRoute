from datetime import datetime, timedelta, timezone
from math import cos, exp, pi, radians
from backend.schemas.iceberg import IcebergPrediction, IcebergRecord

EARTH_KM = 6371.0088


def destination(latitude: float, longitude: float, east_km: float, north_km: float) -> tuple[float, float]:
    lat_delta = north_km / EARTH_KM * 180 / pi
    lon_delta = east_km / (EARTH_KM * max(cos(radians(latitude)), 0.1)) * 180 / pi
    return max(-90, min(90, latitude + lat_delta)), ((longitude + lon_delta + 180) % 360) - 180


def predict_physics(record: IcebergRecord, hours: int = 48, step_hours: int = 1, current_u: float = 0.12, current_v: float = 0.03, wind_u: float = 0.02, wind_v: float = 0.01, wind_drift_factor: float = 0.03) -> list[IcebergPrediction]:
    lat, lon = record.latitude, record.longitude
    timestamp = record.timestamp.astimezone(timezone.utc)
    predictions = []
    for hour in range(step_hours, hours + 1, step_hours):
        dt = step_hours * 3600
        east_ms = current_u + wind_u * wind_drift_factor
        north_ms = current_v + wind_v * wind_drift_factor
        lat, lon = destination(lat, lon, east_ms * dt / 1000, north_ms * dt / 1000)
        uncertainty = 1.5 + 0.35 * hour
        predictions.append(IcebergPrediction(timestamp=timestamp + timedelta(hours=hour), latitude=lat, longitude=lon, uncertainty_km=uncertainty, confidence=max(0.35, exp(-hour / 72))))
    return predictions
