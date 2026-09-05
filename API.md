# API

All coordinates in GeoJSON are `[longitude, latitude]`; internal timestamps are UTC.

- `GET /api/health`: service and demo status
- `GET /api/icebergs`: current iceberg points and historical CSV tracks
- `GET /api/icebergs/{id}`: normalized iceberg record
- `GET /api/icebergs/{id}/trajectory?horizon_hours=48`: physics prediction and GeoJSON
- `POST /api/predictions/iceberg`: body `{iceberg_id,horizon_hours}`
- `GET /api/sea-ice`: sea-ice GeoJSON grid
- `POST /api/predictions/sea-ice`: persistence forecast response
- `GET /api/weather`: weather context
- `GET /api/marine`: marine context
- `GET /api/vessels`: Historical AIS Replay points and trails
- `POST /api/routes/optimize`: start, destination, vessel, and route mode
- `GET /api/models/status`: model/provider status
- `GET /api/models/metrics`: truthful evaluation status
- `WS /ws/maritime`: throttled replay update channel
