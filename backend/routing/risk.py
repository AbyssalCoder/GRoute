from math import exp
from typing import Iterable
from backend.schemas.iceberg import IcebergPrediction

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, cos, radians, sin, sqrt
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 6371.0088 * 2 * asin(sqrt(a))

def iceberg_risk(latitude: float, longitude: float, predictions: Iterable[IcebergPrediction], safety_buffer_km: float = 10) -> float:
    risk = 0.0
    for prediction in predictions:
        distance = haversine_km(latitude, longitude, prediction.latitude, prediction.longitude)
        sigma = max(safety_buffer_km, prediction.uncertainty_km)
        risk = max(risk, exp(-(distance * distance) / (2 * sigma * sigma)) * prediction.confidence)
    return min(1.0, risk)

def sea_ice_risk(concentration: float, max_safe: float = 0.65) -> float:
    if concentration <= max_safe:
        return concentration * 0.35
    return min(1.0, 0.35 + (concentration - max_safe) / max(1e-6, 1 - max_safe) * 0.65)

def weather_risk(wave_height_m: float, wind_speed_ms: float = 8) -> float:
    return min(1.0, 0.45 * min(1, wave_height_m / 6) + 0.55 * min(1, wind_speed_ms / 25))
