# Routing

The cost grid combines fuel, iceberg risk, sea-ice risk, weather/wave risk, and travel time. A* is the primary optimizer and Dijkstra is the fallback contract. Route modes change the relative weights: shortest, fuel, safest, and balanced.

Iceberg risk uses a Gaussian overlap function:

`risk = confidence * exp(-distance_km^2 / (2 * sigma_km^2))`

where `sigma_km` is the larger of prediction uncertainty and vessel safety buffer. Sea-ice risk increases smoothly above the configured vessel threshold. The fuel estimate is a transparent prototype calculation based on route distance, vessel fuel rate, and an environmental factor; it is not naval architecture.

The UI labels outputs as AI-assisted route recommendations. It does not claim collision avoidance, certified safety, or quantum computing.
