from __future__ import annotations
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

ROOT = Path(__file__).resolve().parents[3]
FEATURE_NAMES = ["latitude", "longitude", "north_delta_km", "east_delta_km", "gap_days", "disp_km", "size", "flags", "mask", "day_sin", "day_cos"]


def decode_date(value: str) -> datetime:
    encoded = int(value)
    year, day = divmod(encoded, 1000)
    return datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day - 1)


def _features(row: dict[str, str], previous: dict[str, str]) -> list[float]:
    latitude = float(row["lat"])
    longitude = float(row["lon"])
    previous_latitude = float(previous["lat"])
    previous_longitude = float(previous["lon"])
    date = decode_date(row["date"])
    gap_days = max(1, int(row.get("date_gap") or 1))
    north_delta = (latitude - previous_latitude) * 111.195
    east_delta = (longitude - previous_longitude) * 111.195 * max(0.1, np.cos(np.radians(latitude)))
    return [latitude, longitude, north_delta, east_delta, float(gap_days), float(row.get("disp") or 0), float(row.get("size") or 0), float(row.get("flags") or 0), float(row.get("mask") or 0), float(np.sin(2 * np.pi * date.timetuple().tm_yday / 365.25)), float(np.cos(2 * np.pi * date.timetuple().tm_yday / 365.25))]


def build_training_table(data_dir: Path | None = None) -> tuple[np.ndarray, np.ndarray, list[datetime]]:
    folder = data_dir or ROOT / "stats_database_v7.1"
    samples: list[tuple[datetime, list[float], list[float]]] = []
    for path in sorted(folder.glob("*.csv")):
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        for previous, row, following in zip(rows, rows[1:], rows[2:]):
            gap_days = max(1, int(row.get("date_gap") or 1))
            if gap_days > 7:
                continue
            features = _features(row, previous)
            latitude = float(following["lat"])
            longitude = float(following["lon"])
            current_latitude = float(row["lat"])
            current_longitude = float(row["lon"])
            target = [(latitude - current_latitude) * 111.195, (longitude - current_longitude) * 111.195 * max(0.1, np.cos(np.radians(current_latitude)))]
            samples.append((decode_date(row["date"]), features, target))
    samples.sort(key=lambda sample: sample[0])
    return np.asarray([sample[1] for sample in samples], dtype=np.float32), np.asarray([sample[2] for sample in samples], dtype=np.float32), [sample[0] for sample in samples]


def train_model(data_dir: Path | None = None, model_dir: Path | None = None) -> dict[str, Any]:
    X, y, timestamps = build_training_table(data_dir)
    if len(X) < 100:
        raise ValueError("Not enough valid historical samples to train")
    train_end = int(len(X) * 0.70)
    validation_end = int(len(X) * 0.85)
    model = RandomForestRegressor(n_estimators=80, max_depth=18, min_samples_leaf=3, random_state=42, n_jobs=-1)
    model.fit(X[:train_end], y[:train_end])
    validation_prediction = model.predict(X[train_end:validation_end])
    test_prediction = model.predict(X[validation_end:])
    test_error = np.sqrt(np.mean((test_prediction - y[validation_end:]) ** 2, axis=1))
    metrics = {"model_name": "iceberg_random_forest_motion_v1", "algorithm": "RandomForestRegressor", "samples": int(len(X)), "split": {"train": train_end, "validation": validation_end - train_end, "test": len(X) - validation_end}, "validation_mae_km": float(mean_absolute_error(y[train_end:validation_end], validation_prediction)), "test_mae_km": float(mean_absolute_error(y[validation_end:], test_prediction)), "test_rmse_km": float(mean_squared_error(y[validation_end:], test_prediction) ** 0.5), "test_endpoint_error_km": float(np.mean(test_error)), "features": FEATURE_NAMES, "trained_through": timestamps[train_end - 1].isoformat(), "tested_from": timestamps[validation_end].isoformat(), "scientific_note": "Historical-motion model only; wind, current, wave, and sea-ice features were unavailable in the supplied CSV database."}
    target_dir = model_dir or ROOT / "data" / "models"
    target_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURE_NAMES, "metrics": metrics}, target_dir / "iceberg_random_forest.joblib")
    (target_dir / "iceberg_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def load_artifact(model_dir: Path | None = None) -> dict[str, Any] | None:
    artifact = (model_dir or ROOT / "data" / "models") / "iceberg_random_forest.joblib"
    if not artifact.exists():
        return None
    return joblib.load(artifact)


def predict_daily_motion(model: Any, latitude: float, longitude: float, north_delta_km: float, east_delta_km: float, timestamp: datetime, speed_km: float = 0.0) -> tuple[float, float]:
    day = timestamp.timetuple().tm_yday
    features = np.asarray([[latitude, longitude, north_delta_km, east_delta_km, 1.0, speed_km, 0.0, 0.0, 0.0, np.sin(2 * np.pi * day / 365.25), np.cos(2 * np.pi * day / 365.25)]], dtype=np.float32)
    north, east = model.predict(features)[0]
    return float(north), float(east)
