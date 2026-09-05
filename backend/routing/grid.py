from dataclasses import dataclass
from math import ceil, floor
from backend.routing.risk import haversine_km, sea_ice_risk, weather_risk
from global_land_mask import globe

@dataclass(frozen=True)
class Cell:
    row: int
    col: int
    latitude: float
    longitude: float
    cost: float

class CostGrid:
    def __init__(self, start: tuple[float,float], destination: tuple[float,float], resolution: float = 1.0, mode: str = "balanced", environment: dict | None = None) -> None:
        self.resolution = resolution
        self.min_lat = floor(min(start[0], destination[0]) - 3)
        self.max_lat = ceil(max(start[0], destination[0]) + 3)
        self.min_lon = floor(min(start[1], destination[1]) - 3)
        self.max_lon = ceil(max(start[1], destination[1]) + 3)
        self.rows = max(2, int((self.max_lat-self.min_lat)/resolution)+1)
        self.cols = max(2, int((self.max_lon-self.min_lon)/resolution)+1)
        self.mode = mode
        self.environment = environment or {}

    def cell(self, row: int, col: int) -> Cell:
        lat = self.min_lat + row * self.resolution
        lon = self.min_lon + col * self.resolution
        ice_concentration = self.environment.get("sea_ice_concentration")
        ice = sea_ice_risk(float(ice_concentration)) if ice_concentration is not None else sea_ice_risk(max(0, min(1, 0.28 + (abs(lat)+lon % 17) / 100)))
        wave = weather_risk(float(self.environment.get("wave_height_m", 1.2)), float(self.environment.get("wind_speed_ms", 8)))
        current_factor = 1 + min(0.35, float(self.environment.get("current_speed_ms", 0)) / 2)
        fuel = 1 + max(0, 0.25 - abs(lat + 65) / 100)
        weights = {"shortest": (1.0, 0.0, 0.0), "fuel": (1.15, 0.35, 0.25), "safest": (1.0, 6.0, 3.0), "balanced": (1.0, 3.0, 1.5)}.get(self.mode, (1.0, 3.0, 1.5))
        step_km = haversine_km(lat, lon, self.min_lat + max(0, row - 1) * self.resolution, self.min_lon + max(0, col - 1) * self.resolution) or 1.0
        cost = step_km * (weights[0] * fuel * current_factor + weights[1] * ice + weights[2] * wave)
        return Cell(row, col, lat, lon, cost)

    def is_land(self, cell: Cell) -> bool:
        return bool(globe.is_land(cell.latitude, cell.longitude))

    def is_blocked(self, cell: Cell) -> bool:
        if self.is_land(cell):
            return True
        clearance = float(self.environment.get("iceberg_clearance_km", 50))
        return any(haversine_km(cell.latitude, cell.longitude, point[0], point[1]) <= clearance for point in self.environment.get("iceberg_points", []))

    def segment_crosses_land(self, start: Cell, end: Cell) -> bool:
        for index in range(1, 10):
            fraction = index / 10
            latitude = start.latitude + (end.latitude - start.latitude) * fraction
            longitude = start.longitude + (end.longitude - start.longitude) * fraction
            if bool(globe.is_land(latitude, longitude)):
                return True
        return False

    def neighbors(self, cell: Cell):
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
            row, col = cell.row + dr, cell.col + dc
            if 0 <= row < self.rows and 0 <= col < self.cols:
                yield self.cell(row, col)

    def nearest(self, position: tuple[float,float]) -> Cell:
        row = round((position[0]-self.min_lat)/self.resolution)
        col = round((position[1]-self.min_lon)/self.resolution)
        return self.cell(max(0,min(self.rows-1,row)), max(0,min(self.cols-1,col)))
