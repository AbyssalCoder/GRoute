from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
import csv
from math import cos, radians
import re
import httpx
from backend.schemas.common import FeatureCollection, GeoJSONFeature, GeoJSONGeometry
from backend.schemas.iceberg import IcebergRecord
from backend.schemas.marine import MarinePoint, SeaIcePoint
from backend.schemas.vessel import Vessel, VesselCollection

ROOT = Path(__file__).resolve().parents[2]

def _feature(geometry_type, coordinates, properties=None):
    return GeoJSONFeature(geometry=GeoJSONGeometry(type=geometry_type, coordinates=coordinates), properties=properties or {})

def demo_icebergs() -> list[IcebergRecord]:
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return [IcebergRecord(id="DEMO-A23A", timestamp=now, latitude=-64.4, longitude=-48.2, velocity_u=0.12, velocity_v=0.03, speed=0.13, heading=76, source="DEMO DATA", confidence=0.9), IcebergRecord(id="DEMO-B15", timestamp=now, latitude=-67.0, longitude=-22.0, velocity_u=-0.08, velocity_v=0.04, speed=0.09, heading=296, source="DEMO DATA", confidence=0.86), IcebergRecord(id="DEMO-C19", timestamp=now, latitude=-61.7, longitude=38.0, velocity_u=0.05, velocity_v=-0.03, speed=0.06, heading=121, source="DEMO DATA", confidence=0.82)]

def demo_vessels() -> VesselCollection:
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    vessels=[Vessel(vessel_id="DEMO-VESSEL-01", mmsi="000000001", name="Research Vessel Aurora", latitude=-62.3, longitude=-40.0, speed=10.2, course=92, heading=92, timestamp=now), Vessel(vessel_id="DEMO-VESSEL-02", mmsi="000000002", name="Historical Surveyor", latitude=-65.2, longitude=12.0, speed=7.8, course=180, heading=180, timestamp=now)]
    trails=FeatureCollection(features=[_feature("LineString", [[-48,-63],[-45,-62.7],[-42,-62.5],[-40,-62.3]], {"vessel_id":"DEMO-VESSEL-01","source":"Historical AIS Replay"}), _feature("LineString", [[8,-64.5],[10,-64.8],[12,-65.2]], {"vessel_id":"DEMO-VESSEL-02","source":"Historical AIS Replay"})])
    return VesselCollection(vessels=vessels, trails=trails)

def demo_marine() -> list[MarinePoint]:
    now=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
    return [MarinePoint(timestamp=now,latitude=-64.4,longitude=-48.2,wave_height_m=2.1,wave_period_s=8.5,sea_surface_temperature_c=-0.5,current_speed_ms=0.14,current_direction_deg=72), MarinePoint(timestamp=now,latitude=-67,longitude=-22,wave_height_m=3.4,wave_period_s=10.2,sea_surface_temperature_c=-1.1,current_speed_ms=0.1,current_direction_deg=140)]

def demo_sea_ice() -> list[SeaIcePoint]:
    now=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
    points=[]
    for lat in range(-78,-59,2):
        for lon in range(-180,181,10):
            concentration=max(0.02,min(0.98,0.12 + ((-lat-60)/20)*0.55 + abs(lon % 30)/220))
            points.append(SeaIcePoint(timestamp=now,latitude=lat,longitude=lon,concentration=concentration,source="DEMO DATA"))
    return points

def iceberg_points_geojson(icebergs: list[IcebergRecord]) -> FeatureCollection:
    return FeatureCollection(features=[_feature("Point", [i.longitude,i.latitude], i.model_dump()) for i in icebergs])

def decode_track_date(value: str) -> datetime:
    encoded = int(value)
    year, day_of_year = divmod(encoded, 1000)
    return datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_of_year - 1)

def load_historical_icebergs() -> list[IcebergRecord]:
    records = []
    folder = ROOT / "stats_database_v7.1"
    for path in sorted(folder.glob("*.csv")):
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            continue
        last = rows[-1]
        previous = rows[-2] if len(rows) > 1 else last
        timestamp = decode_track_date(last["date"])
        days = max(1, int(last.get("date_gap") or 1))
        lat_delta = float(last["lat"]) - float(previous["lat"])
        lon_delta = float(last["lon"]) - float(previous["lon"])
        velocity_v = lat_delta * 111_000 / (days * 86400)
        longitude_scale = max(0.1, abs(cos(radians(float(last["lat"])))) )
        velocity_u = lon_delta * 111_000 * longitude_scale / (days * 86400)
        speed = (velocity_u ** 2 + velocity_v ** 2) ** 0.5
        records.append(IcebergRecord(id=path.stem, timestamp=timestamp, latitude=float(last["lat"]), longitude=float(last["lon"]), velocity_u=velocity_u, velocity_v=velocity_v, speed=speed, heading=0.0, source="historical CSV database", confidence=0.7))
    return records

def _decode_dms_coordinate(value: object, dms_value: str | None = None) -> float:
    if dms_value:
        match = re.fullmatch(r"\s*(\d+)\s+(\d+)'\s*([NSEW])\s*", dms_value)
        if not match:
            raise ValueError(f"Invalid DMS coordinate: {dms_value}")
        degrees, minutes = int(match.group(1)), int(match.group(2))
        if minutes >= 60:
            raise ValueError(f"Invalid degrees/minutes coordinate: {dms_value}")
        sign = -1 if match.group(3) in "SW" else 1
        return sign * (degrees + minutes / 60)
    numeric = float(value)
    sign = -1 if numeric < 0 else 1
    absolute = abs(numeric)
    degrees = int(absolute) // 100
    minutes = absolute - degrees * 100
    if minutes >= 60:
        raise ValueError(f"Invalid degrees/minutes coordinate: {value}")
    return sign * (degrees + minutes / 60)

def _parse_observation_date(value: str) -> datetime:
    return datetime.strptime(value, "%m/%d/%y").replace(tzinfo=timezone.utc)

def load_latest_icebergs(url: str) -> list[IcebergRecord]:
    response = httpx.get(url, timeout=15.0)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and isinstance(payload.get("icebergs"), list):
        snapshots = [(None, payload["icebergs"])]
        active_ids = None
    elif isinstance(payload, dict):
        snapshots = []
        for date_key, items in payload.items():
            if not isinstance(items, list):
                continue
            try:
                snapshot_date = _parse_observation_date(str(date_key))
            except (TypeError, ValueError):
                continue
            snapshots.append((snapshot_date, items))
        if not snapshots:
            return []
        latest_snapshot_date = max(snapshot_date for snapshot_date, _ in snapshots if snapshot_date is not None)
        latest_items = next(items for snapshot_date, items in snapshots if snapshot_date == latest_snapshot_date)
        active_ids = {
            str(item.get("iceberg", "")).strip().lower()
            for item in latest_items
            if isinstance(item, dict) and str(item.get("iceberg", "")).strip()
        }
    else:
        return []

    records_by_id: dict[str, IcebergRecord] = {}
    for _, items in sorted(snapshots, key=lambda snapshot: snapshot[0] or datetime.min.replace(tzinfo=timezone.utc)):
        for item in items:
            if not isinstance(item, dict):
                continue
            identifier = str(item.get("iceberg", "")).strip().lower()
            if not identifier or (active_ids is not None and identifier not in active_ids):
                continue
            try:
                record = IcebergRecord(
                    id=identifier,
                    timestamp=_parse_observation_date(str(item["recent_observation"])),
                    latitude=_decode_dms_coordinate(item["lattitude"], item.get("dms_lattitude")),
                    longitude=_decode_dms_coordinate(item["longitude"], item.get("dms_longitude")),
                    source=url,
                    confidence=0.85,
                )
            except (KeyError, TypeError, ValueError):
                continue
            previous = records_by_id.get(identifier)
            if previous is None or record.timestamp >= previous.timestamp:
                records_by_id[identifier] = record
    return sorted(records_by_id.values(), key=lambda record: record.id)

def sea_ice_geojson(points: list[SeaIcePoint]) -> FeatureCollection:
    features=[]
    for p in points:
        d=0.8
        features.append(_feature("Polygon", [[[p.longitude-d,p.latitude-d],[p.longitude+d,p.latitude-d],[p.longitude+d,p.latitude+d],[p.longitude-d,p.latitude+d],[p.longitude-d,p.latitude-d]]], {"concentration":p.concentration,"source":p.source}))
    return FeatureCollection(features=features)

@lru_cache(maxsize=1)
def load_csv_tracks(limit: int | None = None) -> FeatureCollection:
    folder=ROOT / "stats_database_v7.1"
    features=[]
    paths = sorted(folder.glob("*.csv"))
    for path in paths if limit is None else paths[:limit]:
        coords=[]
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                coords.append([float(row["lon"]),float(row["lat"])])
        if len(coords)>1:
            stride = max(1, len(coords) // 200)
            coords = coords[::stride]
            features.append(_feature("LineString", coords, {"iceberg_id":path.stem,"source":"historical CSV database"}))
    return FeatureCollection(features=features)
