from datetime import timedelta
from math import cos, radians
from backend.routing.astar import astar
from backend.routing.grid import CostGrid
from backend.routing.risk import haversine_km, sea_ice_risk, weather_risk
from backend.models.iceberg.predictor import IcebergPredictor
from backend.schemas.iceberg import IcebergRecord
from backend.schemas.route import RouteRequest, RouteResponse, RouteMetrics, TrackedShip
from backend.schemas.common import FeatureCollection, GeoJSONFeature, GeoJSONGeometry

def _segment_features(coordinates: list[list[float]], speed_knots: float, departure_time) -> FeatureCollection:
    features = []
    elapsed = 0.0
    for start, end in zip(coordinates, coordinates[1:]):
        segment_km = haversine_km(start[1], start[0], end[1], end[0])
        elapsed += segment_km / (speed_knots * 1.852)
        features.append(GeoJSONFeature(geometry=GeoJSONGeometry(type="LineString", coordinates=[start, end]), properties={"kind":"ship", "arrival_hours":round(elapsed, 2), "arrival_days":round(elapsed / 24, 2), "arrival_at":(departure_time + timedelta(hours=elapsed)).isoformat()}))
    return FeatureCollection(features=features)

def _intersecting_icebergs(records: list[IcebergRecord], predictor: IcebergPredictor, coordinates: list[list[float]], travel_hours: float, safety_buffer_km: float, departure_time, environment: dict | None = None) -> FeatureCollection:
    features = []
    horizon = max(1, min(168, int(travel_hours) + 1))
    for record in records:
        current_distance = min(haversine_km(record.latitude, record.longitude, point[1], point[0]) for point in coordinates)
        if current_distance > max(5000, safety_buffer_km * 20):
            continue
        predictions = predictor.predict(record, horizon, environment)
        predictions = [prediction.model_copy(update={"timestamp": departure_time + (prediction.timestamp - record.timestamp)}) for prediction in predictions]
        candidates = []
        for prediction in predictions:
            distance = min(haversine_km(prediction.latitude, prediction.longitude, point[1], point[0]) for point in coordinates)
            if distance <= max(750, safety_buffer_km * 20, prediction.uncertainty_km * 6):
                candidates.append((prediction, distance))
        if not candidates:
            continue
        prediction, distance = min(candidates, key=lambda item: item[1])
        features.append(GeoJSONFeature(geometry=GeoJSONGeometry(type="LineString", coordinates=[[record.longitude, record.latitude]] + [[p.longitude, p.latitude] for p in predictions]), properties={"kind":"iceberg", "iceberg_id":record.id, "arrival_hours":round((prediction.timestamp - departure_time).total_seconds() / 3600, 2), "arrival_days":round((prediction.timestamp - departure_time).total_seconds() / 86400, 2), "arrival_at":prediction.timestamp.isoformat(), "distance_to_ship_route_km":round(distance, 2), "uncertainty_km":round(prediction.uncertainty_km, 2)}))
    features.sort(key=lambda feature: feature.properties.get("distance_to_ship_route_km", float("inf")))
    features = features[:12]
    return FeatureCollection(features=features)

def optimize_route(request: RouteRequest, ship: TrackedShip, iceberg_records: list[IcebergRecord] | None = None, predictor: IcebergPredictor | None = None, environment: dict | None = None) -> RouteResponse:
    start=(request.start.latitude,request.start.longitude); end=(request.destination.latitude,request.destination.longitude)
    routing_environment = dict(environment or {})
    routing_environment["iceberg_clearance_km"] = max(request.vessel.safety_buffer_km * 5, 50)
    routing_environment["iceberg_points"] = []
    if predictor and iceberg_records:
        straight_hours = haversine_km(start[0], start[1], end[0], end[1]) / (request.vessel.speed_knots * 1.852)
        horizon = max(24, min(168, int(straight_hours) + 1))
        midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        for record in iceberg_records:
            if min(haversine_km(record.latitude, record.longitude, point[0], point[1]) for point in (start, midpoint, end)) > 2500:
                continue
            routing_environment["iceberg_points"].append((record.latitude, record.longitude))
            routing_environment["iceberg_points"].extend((prediction.latitude, prediction.longitude) for prediction in predictor.predict(record, horizon, environment)[::12])
    grid=CostGrid(start,end,resolution=0.25,mode=request.mode,environment=routing_environment)
    path=astar(grid,start,end)
    if not path:
        raise ValueError("No water-only route exists between the requested coordinates")
    coordinates=[[request.start.longitude, request.start.latitude]] + [[c.longitude,c.latitude] for c in path] + [[request.destination.longitude, request.destination.latitude]]
    coordinates = [coordinates[index] for index in range(len(coordinates)) if index == 0 or coordinates[index] != coordinates[index - 1]]
    distance=sum(haversine_km(coordinates[i-1][1], coordinates[i-1][0], coordinates[i][1], coordinates[i][0]) for i in range(1,len(coordinates)))
    hours=distance/(request.vessel.speed_knots*1.852)
    ice=sea_ice_risk(float(environment["sea_ice_concentration"])) if environment and environment.get("sea_ice_concentration") is not None else 0.3
    weather=weather_risk(float(environment.get("wave_height_m", 1.2)), float(environment.get("wind_speed_ms", 8))) if environment else (0.22 if request.mode=="fuel" else 0.3)
    fuel=distance*request.vessel.fuel_rate*(1 + weather*0.2 - 0.04)
    explanation={"safest":"Route prioritizes lower sea-ice and iceberg exposure.","fuel":"Route favors lower environmental resistance and fuel cost.","shortest":"Route minimizes travel distance.","balanced":"Route balances travel time, fuel, sea-ice, and iceberg risk."}.get(request.mode,"Route generated with configured cost weights.")
    feature=GeoJSONFeature(geometry=GeoJSONGeometry(type="LineString",coordinates=coordinates),properties={"mode":request.mode,"label":"AI-assisted route recommendation"})
    segments = _segment_features(coordinates, request.vessel.speed_knots, request.departure_time)
    iceberg_routes = _intersecting_icebergs(iceberg_records or [], predictor, coordinates, hours, request.vessel.safety_buffer_km, request.departure_time, environment) if predictor else FeatureCollection()
    return RouteResponse(mode=request.mode,ship=ship,route=feature,ship_route_segments=segments,iceberg_routes=iceberg_routes,metrics=RouteMetrics(distance_km=round(distance,2),travel_time_hours=round(hours,2),fuel_estimate=round(fuel,2),iceberg_risk=ice,sea_ice_risk=ice,weather_risk=weather,explanation=explanation))
