from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    app_env: str = "development"
    demo_mode: bool = False
    open_meteo_base_url: str = "https://marine-api.open-meteo.com/v1/marine"
    open_meteo_weather_base_url: str = "https://api.open-meteo.com/v1/forecast"
    copernicus_marine_dataset_id: str = ""
    copernicus_marine_variables: str = "uo,vo"
    copernicus_marine_username: str = ""
    copernicus_marine_password: str = ""
    copernicus_timeout_seconds: int = 60
    copernicus_marine_product_id: str = ""
    copernicus_marine_dataset_current_6h: str = ""
    copernicus_marine_dataset_current_daily: str = ""
    copernicus_marine_dataset_hourly: str = ""
    copernicus_marine_dataset_daily: str = ""
    copernicus_marine_dataset_merged_uv: str = ""
    copernicus_cds_url: str = ""
    copernicus_cds_key: str = ""
    datadocked_base_url: str = "https://datadocked.com/api/vessels_operations"
    datadocked_api_key: str = ""
    datadocked_vessel_ids: str = ""
    datadocked_area_points: str = "-60,-120,50;-60,-60,50;-60,0,50;-60,60,50;-60,120,50"
    aisstream_api_key: str = ""
    aisstream_url: str = "wss://stream.aisstream.io/v0/stream"
    global_fish_access_token: str = ""
    global_fish_base_url: str = "https://gateway.api.globalfishingwatch.org/v3/4wings/report"
    iceberg_latest_url: str = "https://raw.githubusercontent.com/Joel-hanson/Iceberg-locations/main/api/latest.json"
    iceberg_state_path: Path = ROOT / "data" / "iceberg_motion_state.json"
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    alert_sender_address: str = "aniketsupermails2005@gmail.com"
    alert_receiver_address: str = "deybidisha20@gmail.com"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/oauth/google/callback"
    frontend_url: str = "http://127.0.0.1:3000"
    map_style_url: str = "https://tiles.openfreemap.org/styles/liberty"
    grid_resolution_degrees: float = 1.0
    iceberg_forecast_horizon_hours: int = 48
    safety_buffer_km: float = 10.0
    iceberg_clearance_km: float = 300.0
    vessel_speed_knots: float = 10.0
    fuel_weight: float = 1.0
    iceberg_risk_weight: float = 5.0
    sea_ice_risk_weight: float = 5.0
    weather_risk_weight: float = 2.0
    time_weight: float = 1.0
    model_dir: Path = ROOT / "data" / "models"
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
