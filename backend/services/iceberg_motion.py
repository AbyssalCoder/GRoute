from __future__ import annotations

import json
import math
import os
from datetime import datetime, timedelta, timezone
from math import cos, radians, sin
from pathlib import Path
from tempfile import NamedTemporaryFile

from backend.models.iceberg.predictor import IcebergPredictor
from backend.schemas.iceberg import IcebergRecord


def _read_state(path: Path) -> dict[str, IcebergRecord]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return {}
    records = {}
    for item in payload.get("icebergs", []) if isinstance(payload, dict) else []:
        try:
            record = IcebergRecord.model_validate(item)
        except (TypeError, ValueError):
            continue
        records[record.id] = record
    return records


def _write_state(path: Path, records: list[IcebergRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "icebergs": [record.model_dump(mode="json") for record in records],
    }
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2)
        temporary_path = Path(handle.name)
    os.replace(temporary_path, path)


def _advance_record(record: IcebergRecord, now: datetime, predictor: IcebergPredictor) -> IcebergRecord:
    current = record
    if current.speed <= 0 and current.velocity_u == 0 and current.velocity_v == 0:
        speed = 0.12
        heading = (sum(ord(character) for character in current.id) * 17) % 360
        current = current.model_copy(
            update={
                "speed": speed,
                "heading": float(heading),
                "velocity_u": speed * sin(radians(heading)),
                "velocity_v": speed * cos(radians(heading)),
            }
        )
    remaining_seconds = max(0.0, (now - current.timestamp).total_seconds())
    while remaining_seconds > 0:
        step_seconds = min(remaining_seconds, 24 * 60 * 60)
        step_hours = step_seconds / 3600
        forecast_hours = max(1, math.ceil(step_hours))
        forecast = predictor.predict(current, horizon_hours=forecast_hours)
        target = forecast[-1]
        ratio = step_hours / forecast_hours
        latitude = current.latitude + (target.latitude - current.latitude) * ratio
        longitude_delta = ((target.longitude - current.longitude + 540) % 360) - 180
        longitude = ((current.longitude + longitude_delta * ratio + 180) % 360) - 180
        current = current.model_copy(
            update={
                "timestamp": current.timestamp + timedelta(seconds=step_seconds),
                "latitude": latitude,
                "longitude": longitude,
            }
        )
        remaining_seconds -= step_seconds
    return current


def restore_and_advance(records: list[IcebergRecord], predictor: IcebergPredictor, path: Path, now: datetime | None = None) -> list[IcebergRecord]:
    current_time = now or datetime.now(timezone.utc)
    saved = _read_state(path)
    restored = []
    for record in records:
        baseline = saved.get(record.id, record)
        if baseline.timestamp < record.timestamp:
            baseline = record
        restored.append(_advance_record(baseline, current_time, predictor))
    restored.sort(key=lambda record: record.id)
    _write_state(path, restored)
    return restored


def advance_and_save(records: list[IcebergRecord], predictor: IcebergPredictor, path: Path, now: datetime | None = None) -> list[IcebergRecord]:
    current_time = now or datetime.now(timezone.utc)
    advanced = [_advance_record(record, current_time, predictor) for record in records]
    advanced.sort(key=lambda record: record.id)
    _write_state(path, advanced)
    return advanced
