# Setup

1. Install Python 3.13 and Node.js 20+.
2. Install backend packages with `python -m pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and keep `DEMO_MODE=true` for a credential-free run.
4. Start FastAPI with `python -m uvicorn backend.main:app --reload --port 8000`.
5. In a second terminal, run `cd frontend; npm install; npm run dev`.
6. Open `http://localhost:3000` and verify the dashboard banner says `DEMO DATA - NOT LIVE`.

For real data, configure provider credentials outside source control and run provider metadata discovery first. Do not use the supplied credential attachment. Raw downloads should be spatially and temporally subset and stored under ignored data directories.

## Live vessel positions

The Data Docked location endpoint requires IMO or MMSI identifiers. Add these values to your local `.env` without committing them:

```text
DATADOCKED_API_KEY=your-key
DATADOCKED_VESSEL_IDS=imo-or-mmsi-1,imo-or-mmsi-2
```

The backend polls Data Docked server-side and returns normalized vessel positions to the map. The API key never reaches the frontend. The Route Planner API URL alone cannot discover vessels; it calculates port-to-port paths.
