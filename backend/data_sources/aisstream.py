from __future__ import annotations
import asyncio
import json
from datetime import datetime, timezone
import websockets
from backend.config import Settings, get_settings
from backend.schemas.common import FeatureCollection, GeoJSONFeature, GeoJSONGeometry
from backend.schemas.vessel import Vessel, VesselCollection

class AISStreamProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._vessels: dict[str, Vessel] = {}
        self._task: asyncio.Task | None = None
        self._first_report = asyncio.Event()
        self.last_error: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.settings.aisstream_api_key)

    def _snapshot(self) -> VesselCollection:
        vessels = list(self._vessels.values())
        trails = FeatureCollection(features=[GeoJSONFeature(geometry=GeoJSONGeometry(type="LineString", coordinates=[[v.longitude, v.latitude], [v.longitude, v.latitude]]), properties={"vessel_id": v.vessel_id, "source": v.source}) for v in vessels])
        return VesselCollection(vessels=vessels, trails=trails)

    async def _consume(self) -> None:
        subscription = {"APIKey": self.settings.aisstream_api_key, "BoundingBoxes": [[[-90, -180], [-30, 180]]], "FilterMessageTypes": ["PositionReport"]}
        retry_delay = 1
        while True:
            try:
                async with websockets.connect(self.settings.aisstream_url, ping_interval=20, ping_timeout=20, max_size=2**20) as socket:
                    await socket.send(json.dumps(subscription))
                    retry_delay = 1
                    async for raw in socket:
                        event = json.loads(raw)
                        metadata = event.get("MetaData", {})
                        report = event.get("Message", {}).get("PositionReport", {})
                        latitude = report.get("Latitude", metadata.get("Latitude"))
                        longitude = report.get("Longitude", metadata.get("Longitude"))
                        if latitude is None or longitude is None:
                            continue
                        vessel_id = str(metadata.get("MMSI") or metadata.get("ShipName") or "unknown")
                        self._vessels[vessel_id] = Vessel(vessel_id=vessel_id, mmsi=str(metadata.get("MMSI")) if metadata.get("MMSI") else None, name=str(metadata.get("ShipName") or vessel_id), latitude=float(latitude), longitude=float(longitude), speed=float(report.get("Sog") or 0), course=float(report.get("Cog") or 0), heading=float(report.get("TrueHeading") or report.get("Cog") or 0), timestamp=datetime.now(timezone.utc), source="AISStream live AIS")
                        self._first_report.set()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.last_error = f"AISStream connection failed: {type(error).__name__}"
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)

    async def get_vessels(self) -> VesselCollection:
        if not self.configured:
            return self._snapshot()
        started = self._task is None or self._task.done()
        if started:
            self._task = asyncio.create_task(self._consume())
            try:
                await asyncio.wait_for(self._first_report.wait(), timeout=20)
            except asyncio.TimeoutError:
                pass
        return self._snapshot()

    async def close(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
