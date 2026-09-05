from __future__ import annotations

from datetime import datetime, timedelta, timezone
import httpx

from backend.config import Settings, get_settings
from backend.schemas.common import FeatureCollection
from backend.schemas.vessel import Vessel, VesselCollection


class GlobalFishingWatchProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._cache: VesselCollection | None = None
        self._cached_at: datetime | None = None
        self._task = None
        self.last_error: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.settings.global_fish_access_token)

    def cached(self) -> VesselCollection | None:
        return self._cache

    def start_refresh(self) -> None:
        if self.configured and (self._task is None or self._task.done()):
            import asyncio
            self._task = asyncio.create_task(self.get_vessels())

    async def get_vessels(self) -> VesselCollection:
        now = datetime.now(timezone.utc)
        if self._cache and self._cached_at and (now - self._cached_at).total_seconds() < 900:
            return self._cache
        if not self.configured:
            return VesselCollection(vessels=[], trails=FeatureCollection())

        params = {
            "format": "JSON",
            "group-by": "VESSEL_ID",
            "temporal-resolution": "ENTIRE",
            "datasets[0]": "public-global-presence:latest",
            "date-range": f"{(now - timedelta(days=7)).date().isoformat()},{now.date().isoformat()}",
            "spatial-aggregation": "false",
            "spatial-resolution": "LOW",
        }
        polygon = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [[[-180, -90], [180, -90], [180, -30], [-180, -30], [-180, -90]]]}}]}
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.post(self.settings.global_fish_base_url, params=params, json={"geojson": polygon}, headers={"Authorization": f"Bearer {self.settings.global_fish_access_token}"})
                if response.is_error:
                    self.last_error = f"Global Fishing Watch request failed: HTTP {response.status_code}"
                response.raise_for_status()
                entries = response.json().get("entries", [])
            vessels: list[Vessel] = []
            for entry in entries:
                if entry.get("lat") is None or entry.get("lon") is None:
                    continue
                mmsi = str(entry["mmsi"]) if entry.get("mmsi") else None
                vessel_id = mmsi or str(entry.get("vesselId") or entry.get("shipName") or "unknown")
                vessels.append(Vessel(vessel_id=vessel_id, mmsi=mmsi, name=str(entry.get("shipName") or vessel_id), latitude=float(entry["lat"]), longitude=float(entry["lon"]), speed=0, course=0, heading=0, timestamp=now, source="Global Fishing Watch presence"))
            self._cache = VesselCollection(vessels=vessels, trails=FeatureCollection())
            self._cached_at = now
            self.last_error = None
            return self._cache
        except Exception as error:
            if not self.last_error:
                self.last_error = f"Global Fishing Watch request failed: {type(error).__name__}"
            return self._cache or VesselCollection(vessels=[], trails=FeatureCollection())