from datetime import datetime, timedelta, timezone
from backend.schemas.marine import SeaIcePoint

def forecast_persistence(latitude: float, longitude: float, concentration: float, horizon_hours: int = 48) -> list[SeaIcePoint]:
    now = datetime.now(timezone.utc)
    return [SeaIcePoint(timestamp=now + timedelta(hours=h), latitude=latitude, longitude=longitude, concentration=concentration, source="persistence baseline") for h in (1, 6, 12, 24, 48) if h <= horizon_hours]
