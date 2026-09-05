# Data sources

## Historical iceberg CSV database

- Provider: existing repository data
- Coverage: approximately 1989 through 2023
- Purpose: historical trajectories and track visualization
- Schema: `date,date_gap,disp,flags,lat,lon,mask,size,vel_angle`
- Mapping: filename becomes track ID; `lat/lon` become geographic position; `disp` is retained as source displacement; date is decoded as year plus day-of-year; gaps are not interpolated without an explicit policy
- Limitation: no environmental drivers, vessel data, units metadata, or provenance file is included

## Open-Meteo Marine

- URL: https://open-meteo.com/
- Purpose: wave, swell, SST, sea-level, and exposed current variables
- Authentication: none for the public API
- Adapter: `backend/data_sources/open_meteo.py`
- Limitation: use a bounded configurable grid and caching in real ingestion; the demo uses local fixtures

## ERA5 / Copernicus CDS

- URL: https://cds.climate.copernicus.eu/
- Purpose: historical wind, temperature, and pressure features
- Variables: 10m U/V wind, 2m temperature, mean sea-level pressure
- Authentication: local CDS configuration or environment, never repository text
- Limitation: downloader is intentionally disabled until credentials and date/area configuration are supplied

## Copernicus Marine

- URL: https://marine.copernicus.eu/
- Purpose: sea-ice concentration and near-surface ocean currents
- Authentication: Copernicus Marine Toolbox login
- Rule: run official `describe` metadata discovery before configuring dataset IDs
- Limitation: adapter does not assume stale IDs and returns NOT CONFIGURED by default

## Sentinel-1 / Copernicus Data Space

- URL: https://documentation.dataspace.copernicus.eu/
- Purpose: bounded SAR scene discovery and future feature extraction
- Limitation: no bulk archive download is performed by this prototype

## AIS

- Provider: Data Docked Vessel Location API, with `AISReplayProvider` fallback
- URL: https://datadocked.com/api-reference#get-vessel-location
- Endpoint: `GET /api/vessels_operations/get-vessel-location`
- Authentication: `x-api-key` header from `DATADOCKED_API_KEY`; never expose it to Next.js
- Configuration: `DATADOCKED_VESSEL_IDS` is a comma-separated list of IMO or MMSI identifiers
- Polling: frontend refreshes normalized positions every 60 seconds; provider documents 100 requests/minute
- Label: Data Docked live AIS when configured, otherwise AIS not configured or Historical AIS Replay in demo mode
- Limitation: the supplied Route Planner page is not a vessel-position feed; ship identifiers are required for location calls
