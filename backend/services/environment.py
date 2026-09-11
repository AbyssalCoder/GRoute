from __future__ import annotations

import asyncio
from math import atan2, degrees, hypot
from backend.data_sources.copernicus_marine import configured, get_ocean_currents
from backend.data_sources.open_meteo import fetch_marine, fetch_weather
from backend.config import get_settings

async def fetch_route_environment(latitude: float, longitude: float) -> dict:
    marine, weather = await asyncio.gather(fetch_marine(latitude, longitude), fetch_weather(latitude, longitude))
    current = marine.get("current", {})
    result = {
        "wave_height_m": float(current.get("wave_height", 0) or 0),
        "wave_period_s": float(current.get("wave_period", 0) or 0),
        "current_speed_ms": float(current.get("ocean_current_velocity", 0) or 0),
        "current_direction_deg": float(current.get("ocean_current_direction", 0) or 0),
        "wind_speed_ms": float(weather.get("wind_speed_10m", 0) or 0),
        "wind_direction_deg": float(weather.get("wind_direction_10m", 0) or 0),
        "sea_ice_concentration": None,
        "source": "Open-Meteo marine + weather; sea ice unavailable",
    }
    if configured():
        try:
            copernicus = await asyncio.wait_for(asyncio.to_thread(get_ocean_currents, latitude, longitude), timeout=min(get_settings().copernicus_timeout_seconds, 5))
            result = _merge_copernicus(result, copernicus)
        except Exception as exc:
            result["copernicus_error"] = f"{type(exc).__name__}: {exc}".strip()
    return result


def _merge_copernicus(result: dict, values: dict) -> dict:
    sea_ice = next((values.get(key) for key in ("siconc", "sea_ice_concentration", "ice_concentration") if values.get(key) is not None), None)
    if sea_ice is not None:
        sea_ice_value = float(sea_ice)
        result["sea_ice_concentration"] = max(0.0, min(1.0, sea_ice_value / 100 if sea_ice_value > 1 else sea_ice_value))
    east = next((values.get(key) for key in ("uo", "eastward_sea_water_velocity") if values.get(key) is not None), None)
    north = next((values.get(key) for key in ("vo", "northward_sea_water_velocity") if values.get(key) is not None), None)
    if east is not None and north is not None:
        result["current_speed_ms"] = hypot(float(east), float(north))
        result["current_direction_deg"] = (degrees(atan2(float(east), float(north))) + 360) % 360
    result["source"] = f"{result['source']} + {values.get('source', 'Copernicus Marine')}"
    return result

async def fetch_route_environment_samples(points: list[tuple[float, float]]) -> dict:
    samples = await asyncio.gather(*(fetch_route_environment(latitude, longitude) for latitude, longitude in points))
    numeric_keys = ("wave_height_m", "wave_period_s", "current_speed_ms", "current_direction_deg", "wind_speed_ms", "wind_direction_deg")
    result = {key: sum(sample[key] for sample in samples) / len(samples) for key in numeric_keys}
    result["sea_ice_concentration"] = next((sample["sea_ice_concentration"] for sample in samples if sample.get("sea_ice_concentration") is not None), None)
    result["source"] = " | ".join(sorted({sample.get("source", "Unknown") for sample in samples}))
    return result