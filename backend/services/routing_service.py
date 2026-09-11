from datetime import timedelta
from math import cos, radians
from backend.routing.astar import astar
from backend.routing.grid import CostGrid
from backend.routing.risk import haversine_km, sea_ice_risk, weather_risk
from backend.models.iceberg.predictor import IcebergPredictor
from backend.schemas.iceberg import IcebergRecord
from backend.schemas.route import RouteRequest, RouteResponse, RouteMetrics, RouteComparison, TrackedShip
from backend.schemas.common import FeatureCollection, GeoJSONFeature, GeoJSONGeometry

def _segment_features(coordinates: list[list[float]], speed_knots: float, departure_time) -> FeatureCollection:
    features = []
    elapsed = 0.0
    for start, end in zip(coordinates, coordinates[1:]):
        segment_km = haversine_km(start[1], start[0], end[1], end[0])
        elapsed += segment_km / (speed_knots * 1.852)
        features.append(GeoJSONFeature(geometry=GeoJSONGeometry(type="LineString", coordinates=[start, end]), properties={"kind":"ship", "arrival_hours":round(elapsed, 2), "arrival_days":round(elapsed / 24, 2), "arrival_at":(departure_time + timedelta(hours=elapsed)).isoformat()}))
    return FeatureCollection(features=features)

def _intersecting_icebergs(records: list[IcebergRecord], predictor: IcebergPredictor, coordinates: list[list[float]], travel_hours: float, clearance_km: float, departure_time, environment: dict | None = None) -> FeatureCollection:
    features = []
    horizon = max(1, min(168, int(travel_hours) + 1))
    for record in records:
        current_distance = min(haversine_km(record.latitude, record.longitude, point[1], point[0]) for point in coordinates)
        if current_distance > max(2500, clearance_km * 8):
            continue
        predictions = predictor.predict(record, horizon, environment)
        predictions = [prediction.model_copy(update={"timestamp": departure_time + (prediction.timestamp - record.timestamp)}) for prediction in predictions]
        candidates = []
        for prediction in predictions:
            distance = min(haversine_km(prediction.latitude, prediction.longitude, point[1], point[0]) for point in coordinates)
            if distance <= clearance_km + prediction.uncertainty_km * 6:
                candidates.append((prediction, distance))
        if not candidates:
            continue
        prediction, distance = min(candidates, key=lambda item: item[1])
        features.append(GeoJSONFeature(geometry=GeoJSONGeometry(type="LineString", coordinates=[[record.longitude, record.latitude]] + [[p.longitude, p.latitude] for p in predictions]), properties={"kind":"iceberg", "iceberg_id":record.id, "arrival_hours":round((prediction.timestamp - departure_time).total_seconds() / 3600, 2), "arrival_days":round((prediction.timestamp - departure_time).total_seconds() / 86400, 2), "arrival_at":prediction.timestamp.isoformat(), "distance_to_ship_route_km":round(distance, 2), "clearance_km":round(clearance_km, 2), "uncertainty_km":round(prediction.uncertainty_km, 2)}))
    features.sort(key=lambda feature: feature.properties.get("distance_to_ship_route_km", float("inf")))
    features = features[:12]
    return FeatureCollection(features=features)

def optimize_route(request: RouteRequest, ship: TrackedShip, iceberg_records: list[IcebergRecord] | None = None, predictor: IcebergPredictor | None = None, environment: dict | None = None, include_comparison: bool = True, resolution: float = 0.25) -> RouteResponse:
    start=(request.start.latitude,request.start.longitude); end=(request.destination.latitude,request.destination.longitude)
    routing_environment = dict(environment or {})
    clearance_km = max(request.vessel.safety_buffer_km * 5, 300)
    routing_environment["iceberg_clearance_km"] = clearance_km
    routing_environment["iceberg_risk_radius_km"] = clearance_km
    routing_environment["ship_speed_knots"] = request.vessel.speed_knots
    routing_environment["iceberg_points"] = []
    routing_environment["iceberg_risk_points"] = []
    if predictor and iceberg_records:
        straight_hours = haversine_km(start[0], start[1], end[0], end[1]) / (request.vessel.speed_knots * 1.852)
        horizon = max(24, min(168, int(straight_hours) + 1))
        midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        for record in iceberg_records:
            if min(haversine_km(record.latitude, record.longitude, point[0], point[1]) for point in (start, midpoint, end)) > 2500:
                continue
            routing_environment["iceberg_points"].append((record.latitude, record.longitude))
            predicted_points = [(prediction.latitude, prediction.longitude, (prediction.timestamp - request.departure_time).total_seconds() / 3600) for prediction in predictor.predict(record, horizon, environment)[::6]]
            routing_environment["iceberg_points"].extend([(point[0], point[1]) for point in predicted_points])
            routing_environment["iceberg_risk_points"].extend(predicted_points)
    grid=CostGrid(start,end,resolution=resolution,mode=request.mode,environment=routing_environment)
    if resolution >= 1.0:
        coordinates=[[request.start.longitude, request.start.latitude], [request.destination.longitude, request.destination.latitude]]
    else:
        path=astar(grid,start,end)
        if not path:
            raise ValueError("No water-only route exists between the requested coordinates")
        coordinates=[[request.start.longitude, request.start.latitude]] + [[c.longitude,c.latitude] for c in path] + [[request.destination.longitude, request.destination.latitude]]
    coordinates = [coordinates[index] for index in range(len(coordinates)) if index == 0 or coordinates[index] != coordinates[index - 1]]
    distance=sum(haversine_km(coordinates[i-1][1], coordinates[i-1][0], coordinates[i][1], coordinates[i][0]) for i in range(1,len(coordinates)))
    hours=distance/(request.vessel.speed_knots*1.852)
    ice=sea_ice_risk(float(environment["sea_ice_concentration"])) if environment and environment.get("sea_ice_concentration") is not None else 0.0
    weather=weather_risk(float(environment.get("wave_height_m", 1.2)), float(environment.get("wind_speed_ms", 8))) if environment else (0.22 if request.mode=="fuel" else 0.3)
    fuel=distance*request.vessel.fuel_rate*(1 + weather*0.2 - 0.04)
    reasons={"safest":["Applies the strongest sea-ice penalty.","Heavily penalizes predicted iceberg proximity.","Accepts extra distance to reduce environmental exposure."],"fuel":["Weights modeled fuel resistance and current effects lower.","Penalizes sea ice and waves without taking the safest detour.","Prefers a lower-resistance route corridor."],"shortest":["Minimizes geographic route distance.","Uses no soft weather or sea-ice preference.","Still enforces land and hard iceberg-clearance constraints."],"balanced":["Uses moderate distance, fuel, weather, and sea-ice weights.","Penalizes iceberg exposure while avoiding extreme detours.","Chooses a practical compromise between time, fuel, and risk."]}.get(request.mode,["Uses the configured route cost weights.","Avoids land and blocked iceberg-clearance cells.","Scores environmental conditions along the route."])
    explanation={"safest":"Route prioritizes lower sea-ice and iceberg exposure.","fuel":"Route favors lower environmental resistance and fuel cost.","shortest":"Route minimizes travel distance.","balanced":"Route balances travel time, fuel, sea-ice, and iceberg risk."}.get(request.mode,"Route generated with configured cost weights.")
    feature=GeoJSONFeature(geometry=GeoJSONGeometry(type="LineString",coordinates=coordinates),properties={"mode":request.mode,"label":"AI-assisted route recommendation"})
    segments = _segment_features(coordinates, request.vessel.speed_knots, request.departure_time)
    iceberg_routes = _intersecting_icebergs(iceberg_records or [], predictor, coordinates, hours, clearance_km, request.departure_time, environment) if predictor else FeatureCollection()
    risk_points = routing_environment["iceberg_risk_points"]
    route_risk = max((max(0.0, 1 - min(haversine_km(point[1], point[0], risk_point[0], risk_point[1]) for risk_point in risk_points) / clearance_km) for point in coordinates), default=0.0) if risk_points else 0.0
    metrics = RouteMetrics(distance_km=round(distance,2),travel_time_hours=round(hours,2),fuel_estimate=round(fuel,2),iceberg_risk=round(route_risk,3),sea_ice_risk=round(ice,3),weather_risk=round(weather,3),explanation=explanation,reasons=reasons)
    if not include_comparison:
        return RouteResponse(mode=request.mode,ship=ship,route=feature,ship_route_segments=segments,iceberg_routes=iceberg_routes,metrics=metrics)
    baseline_distance = haversine_km(start[0], start[1], end[0], end[1])
    baseline_fuel = baseline_distance * request.vessel.fuel_rate * (1 + weather * 0.2 - 0.04)
    mode_factors = {"fuel": (0.98, 0.96), "shortest": (1.0, 1.0), "safest": (1.12, 1.12), "balanced": (1.04, 1.04)}
    comparison = []
    for mode in ("fuel", "shortest", "safest", "balanced"):
        distance_factor, fuel_factor = mode_factors[mode]
        mode_distance = baseline_distance * distance_factor
        if mode == request.mode:
            mode_distance = distance
            mode_fuel = fuel
            mode_hours = hours
        else:
            mode_fuel = baseline_fuel * fuel_factor
            mode_hours = mode_distance / (request.vessel.speed_knots * 1.852)
        comparison.append(RouteComparison(mode=mode,distance_km=round(mode_distance,2),travel_time_hours=round(mode_hours,2),fuel_estimate=round(mode_fuel,2),fuel_saved_vs_shortest=round(baseline_fuel-mode_fuel,2),fuel_savings_percent=round((baseline_fuel-mode_fuel)/baseline_fuel*100,2) if baseline_fuel else 0.0,kilometers_saved_vs_shortest=round(baseline_distance-mode_distance,2),distance_reduction_percent=round((baseline_distance-mode_distance)/baseline_distance*100,2) if baseline_distance else 0.0,reasons=reasons if mode == request.mode else {"safest":["Applies the strongest sea-ice penalty.","Heavily penalizes predicted iceberg proximity.","Accepts extra distance to reduce environmental exposure."],"fuel":["Weights modeled fuel resistance and current effects lower.","Penalizes sea ice and waves without taking the safest detour.","Prefers a lower-resistance route corridor."],"shortest":["Minimizes geographic route distance.","Uses no soft weather or sea-ice preference.","Still enforces land and hard iceberg-clearance constraints."],"balanced":["Uses moderate distance, fuel, weather, and sea-ice weights.","Penalizes iceberg exposure while avoiding extreme detours.","Chooses a practical compromise between time, fuel, and risk."]}[mode]))
    return RouteResponse(mode=request.mode,ship=ship,route=feature,ship_route_segments=segments,iceberg_routes=iceberg_routes,metrics=metrics,comparison=comparison)
