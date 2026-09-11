import heapq
from backend.routing.grid import Cell, CostGrid
from backend.routing.risk import haversine_km

def astar(grid: CostGrid, start: tuple[float,float], destination: tuple[float,float]) -> list[Cell]:
    origin, goal = grid.nearest(start), grid.nearest(destination)
    queue = [(0.0, origin.row, origin.col)]
    came_from: dict[tuple[int,int], tuple[int,int] | None] = {(origin.row, origin.col): None}
    score = {(origin.row, origin.col): 0.0}
    while queue:
        _, row, col = heapq.heappop(queue)
        current = grid.cell(row, col)
        if (row, col) == (goal.row, goal.col):
            path=[]; key=(row,col)
            while key is not None:
                path.append(grid.cell(*key)); key=came_from[key]
            return list(reversed(path))
        for neighbor in grid.neighbors(current):
            leaving_origin = (row, col) == (origin.row, origin.col)
            if not leaving_origin and (grid.is_blocked(neighbor) or grid.segment_crosses_land(current, neighbor)) and (neighbor.row, neighbor.col) != (goal.row, goal.col):
                continue
            key=(neighbor.row, neighbor.col)
            new_score = score[(row,col)] + neighbor.cost
            if new_score < score.get(key, float('inf')):
                score[key] = new_score
                came_from[key] = (row,col)
                # Use a conservative geographic lower bound to guide the search.
                # Environmental and corridor penalties are non-negative, so this
                # remains a lower bound for every route mode.
                distance_lower_bound = haversine_km(current.latitude, current.longitude, destination[0], destination[1]) * 0.5
                priority = new_score + distance_lower_bound
                heapq.heappush(queue, (priority, *key))
    return []
