from __future__ import annotations
import httpx
from backend.config import get_settings

HOURLY = ["wave_height","wave_direction","wave_period","sea_surface_temperature","ocean_current_velocity","ocean_current_direction"]

async def fetch_marine(latitude: float, longitude: float, start_date: str | None = None, end_date: str | None = None) -> dict:
    settings=get_settings()
    params={"latitude":latitude,"longitude":longitude,"hourly":",".join(HOURLY),"current":",".join(HOURLY),"timezone":"GMT"}
    if start_date: params["start_date"]=start_date
    if end_date: params["end_date"]=end_date
    async with httpx.AsyncClient(timeout=20) as client:
        response=await client.get(settings.open_meteo_base_url,params=params)
        response.raise_for_status()
        payload=response.json()
    if not isinstance(payload,dict) or "hourly" not in payload:
        raise ValueError("Open-Meteo response did not contain hourly data")
    return payload

async def fetch_weather(latitude: float, longitude: float) -> dict:
    settings = get_settings()
    params = {"latitude": latitude, "longitude": longitude, "current": "wind_speed_10m,wind_direction_10m", "timezone": "GMT"}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(settings.open_meteo_weather_base_url, params=params)
        response.raise_for_status()
        payload = response.json()
    return payload.get("current", {})
