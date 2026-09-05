from __future__ import annotations

import asyncio
from backend.data_sources.open_meteo import fetch_marine, fetch_weather

async def fetch_route_environment(latitude: float, longitude: float) -> dict:
    marine, weather = await asyncio.gather(fetch_marine(latitude, longitude), fetch_weather(latitude, longitude))
    current = marine.get("current", {})
    return {
        "wave_height_m": float(current.get("wave_height", 0) or 0),
        "wave_period_s": float(current.get("wave_period", 0) or 0),
        "current_speed_ms": float(current.get("ocean_current_velocity", 0) or 0),
        "current_direction_deg": float(current.get("ocean_current_direction", 0) or 0),
        "wind_speed_ms": float(weather.get("wind_speed_10m", 0) or 0),
        "wind_direction_deg": float(weather.get("wind_direction_10m", 0) or 0),
        "sea_ice_concentration": None,
        "source": "Open-Meteo marine + weather; sea ice unavailable",
    }

async def fetch_route_environment_samples(points: list[tuple[float, float]]) -> dict:
    samples = await asyncio.gather(*(fetch_route_environment(latitude, longitude) for latitude, longitude in points))
    numeric_keys = ("wave_height_m", "wave_period_s", "current_speed_ms", "current_direction_deg", "wind_speed_ms", "wind_direction_deg")
    result = {key: sum(sample[key] for sample in samples) / len(samples) for key in numeric_keys}
    result["sea_ice_concentration"] = next((sample["sea_ice_concentration"] for sample in samples if sample.get("sea_ice_concentration") is not None), None)
    result["source"] = "Open-Meteo marine + weather sampled along route; sea ice unavailable"
    return result