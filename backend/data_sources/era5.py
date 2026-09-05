from pathlib import Path
from backend.config import get_settings

def status() -> str:
    return "CONNECTED" if (Path.home()/".cdsapirc").exists() else "NOT CONFIGURED"

def download_era5(*args, **kwargs):
    raise RuntimeError("ERA5 downloader is disabled until CDS is configured; no credentials are read from repository files.")
