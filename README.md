# Antarctic Maritime AI Decision Support System

A research and decision-support prototype for Antarctic iceberg movement, sea-ice context, maritime risk, vessel replay, and AI-assisted route recommendations. It is not autonomous navigation and does not guarantee safety.

## Quick start

Backend (PowerShell):

```powershell
C:/Users/Aniket/AppData/Local/Programs/Python/Python313/python.exe -m uvicorn backend.main:app --reload --port 8000
```

Frontend (second terminal):

```powershell
cd frontend
npm run dev
```

Open http://localhost:3000. Demo mode is enabled by default and does not require credentials.

## Data

The existing `stats_database_v7.1` CSV files are preserved as historical iceberg tracks. They use `YYYYDDD` dates and the fields documented in [DATA_SOURCES.md](DATA_SOURCES.md). Demo mode uses deterministic synthetic environmental fixtures and the CSV tracks for visualization. Real ERA5, Copernicus Marine, Sentinel, and Open-Meteo adapters are configured through environment variables and degrade gracefully when unavailable.

Copy `.env.example` to `.env`; never copy credentials from repository notes. `Creds.txt` is ignored and is not read by the application.

## Commands

```powershell
python -m backend.cli ingest
python -m backend.cli preprocess
python -m backend.cli train-iceberg
python -m backend.cli train-sea-ice
python -m backend.cli evaluate
python -m backend.cli predict
python -m backend.cli route
```

## Status

The shipped baseline is a physics-driven iceberg predictor, persistence sea-ice baseline, uncertainty corridor, and A* route optimizer. The ML model status is intentionally `ML model unavailable - physics baseline active` until environmental features are downloaded, chronologically split, trained, and evaluated. See [ML.md](ML.md), [ROUTING.md](ROUTING.md), and [SETUP.md](SETUP.md).
