from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.config import get_settings


def _provided(value: str) -> bool:
    return bool(value and not value.strip().upper().startswith("YOUR_"))


def _current_dataset(settings) -> str:
    return settings.copernicus_marine_dataset_id or settings.copernicus_marine_dataset_current_6h or settings.copernicus_marine_dataset_current_daily or settings.copernicus_marine_dataset_merged_uv


def discover_datasets() -> dict:
    settings = get_settings()
    if not _provided(settings.copernicus_marine_username) or not _provided(settings.copernicus_marine_password):
        return {"status": "NOT CONFIGURED", "note": "Copernicus Marine credentials are missing."}
    dataset_id = _current_dataset(settings)
    if not dataset_id:
        return {"status": "CREDENTIALS PRESENT", "note": "Set a Copernicus current dataset ID."}
    return {"status": "CONFIGURED", "dataset_id": dataset_id, "variables": settings.copernicus_marine_variables.split(",")}


def configured() -> bool:
    return discover_datasets()["status"] == "CONFIGURED"


def _fetch_point_sync(latitude: float, longitude: float) -> dict[str, Any]:
    settings = get_settings()
    import copernicusmarine

    dataset_id = _current_dataset(settings)
    variables = [item.strip() for item in settings.copernicus_marine_variables.split(",") if item.strip()]
    now = datetime.now(timezone.utc)
    dataset = copernicusmarine.open_dataset(
        dataset_id=dataset_id,
        username=settings.copernicus_marine_username,
        password=settings.copernicus_marine_password,
        minimum_longitude=longitude - 0.1,
        maximum_longitude=longitude + 0.1,
        minimum_latitude=latitude - 0.1,
        maximum_latitude=latitude + 0.1,
        start_datetime=now.strftime("%Y-%m-%d"),
        end_datetime=now.strftime("%Y-%m-%d"),
        variables=variables,
    )
    values: dict[str, Any] = {}
    for variable in variables:
        if variable in dataset:
            values[variable] = float(dataset[variable].mean(skipna=True).values)
    values["source"] = f"Copernicus Marine: {dataset_id}"
    return values

def get_sea_ice(*args, **kwargs):
    return _fetch_point_sync(*args, **kwargs)

def get_ocean_currents(*args, **kwargs):
    return _fetch_point_sync(*args, **kwargs)
