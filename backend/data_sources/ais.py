from datetime import datetime, timedelta, timezone
from typing import Protocol
import httpx
from backend.config import Settings, get_settings
from backend.services.demo import demo_vessels
from backend.schemas.vessel import Vessel, VesselCollection
from backend.schemas.common import FeatureCollection, GeoJSONFeature, GeoJSONGeometry

class AISProvider(Protocol):
    def get_vessels(self) -> VesselCollection: ...

class AISReplayProvider:
    def get_vessels(self) -> VesselCollection:
        return demo_vessels()

class DataDockedVesselProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._cached: VesselCollection | None = None
        self._cached_at: datetime | None = None
        self.last_error: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.settings.datadocked_api_key and (self.settings.datadocked_vessel_ids.strip() or self.settings.datadocked_area_points.strip()))

    def _area_points(self) -> list[tuple[float, float, float]]:
        points = []
        for value in self.settings.datadocked_area_points.split(';'):
            try:
                latitude, longitude, radius = [float(part.strip()) for part in value.split(',')]
                points.append((latitude, longitude, min(50.0, max(1.0, radius))))
            except ValueError:
                continue
        return points

    @staticmethod
    def _normalize(payload: dict, identifier: str) -> Vessel:
        return Vessel(vessel_id=str(payload.get("imo") or payload.get("mmsi") or identifier), mmsi=str(payload.get("mmsi")) if payload.get("mmsi") else None, name=str(payload.get("name") or identifier), latitude=float(payload["latitude"]), longitude=float(payload["longitude"]), speed=float(payload.get("speed") or 0) / 10, course=float(payload.get("course") or 0), heading=float(payload.get("heading") or payload.get("course") or 0), destination=payload.get("destination"), timestamp=datetime.now(timezone.utc), source="Data Docked live AIS")

    async def get_vessels(self) -> VesselCollection | None:
        if not self.configured:
            return None
        self.last_error = None
        if self._cached and self._cached_at and datetime.now(timezone.utc) - self._cached_at < timedelta(seconds=55):
            return self._cached
        identifiers = [value.strip() for value in self.settings.datadocked_vessel_ids.split(',') if value.strip()]
        headers = {"accept": "application/json", "x-api-key": self.settings.datadocked_api_key}
        vessels = []
        async with httpx.AsyncClient(timeout=15) as client:
            for offset in range(0, len(identifiers), 50):
                batch = identifiers[offset:offset + 50]
                if not batch:
                    continue
                response = await client.get(f"{self.settings.datadocked_base_url}/get-vessels-location-bulk-search", params={"imo_or_mmsi": ','.join(batch)}, headers=headers)
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as error:
                    self.last_error = f"Data Docked bulk lookup returned HTTP {error.response.status_code}"
                    continue
                payload = response.json()
                for item in payload.get("results", []):
                    vessels.append(self._normalize(item, str(item.get("mmsi") or item.get("imo") or "unknown")))
            for latitude, longitude, radius in self._area_points():
                response = await client.get(f"{self.settings.datadocked_base_url}/get-vessels-by-area", params={"latitude": latitude, "longitude": longitude, "circle_radius": radius}, headers=headers)
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as error:
                    self.last_error = f"Data Docked area lookup returned HTTP {error.response.status_code}"
                    continue
                for item in response.json().get("vessels", []):
                    vessel = self._normalize(item, str(item.get("mmsi") or "unknown"))
                    if not any(existing.vessel_id == vessel.vessel_id for existing in vessels):
                        vessels.append(vessel)
        trails = FeatureCollection(features=[GeoJSONFeature(geometry=GeoJSONGeometry(type="LineString", coordinates=[[v.longitude, v.latitude], [v.longitude, v.latitude]]), properties={"vessel_id": v.vessel_id, "source": v.source}) for v in vessels])
        self._cached = VesselCollection(vessels=vessels, trails=trails)
        self._cached_at = datetime.now(timezone.utc)
        return self._cached
