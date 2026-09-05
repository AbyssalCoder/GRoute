def discover_datasets() -> dict:
    return {"status":"NOT CONFIGURED","note":"Use the official Copernicus Marine Toolbox describe command before selecting dataset IDs."}

def get_sea_ice(*args, **kwargs):
    raise RuntimeError("Copernicus Marine is not configured")

def get_ocean_currents(*args, **kwargs):
    raise RuntimeError("Copernicus Marine is not configured")
