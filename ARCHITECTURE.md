# Architecture

```mermaid
flowchart LR
  CSV[Historical iceberg CSV] --> N[Normalization and validation]
  O[Open-Meteo Marine] --> F[Feature alignment]
  E[ERA5 CDS] --> F
  C[Copernicus Marine] --> F
  N --> P[Physics baseline / residual ML]
  F --> P
  P --> R[Uncertainty and risk]
  R --> G[Cost grid]
  G --> A[A* / Dijkstra]
  A --> API[FastAPI + WebSocket]
  API --> UI[Next.js + MapLibre]
  AIS[Historical AIS Replay] --> API
```

The backend owns normalized schemas, UTC handling, GeoJSON generation, route cost calculation, and provider status. The frontend only renders API contracts and updates MapLibre sources/layers in place. Raw scientific files belong in `data/raw` and are never loaded wholesale into the browser.
