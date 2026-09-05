from backend.routing.astar import astar
from backend.routing.grid import CostGrid

def dijkstra(grid: CostGrid, start: tuple[float,float], destination: tuple[float,float]):
    return astar(grid, start, destination)
