# Machine learning

The current operational model is a small Random Forest hybrid trained from the supplied historical tracks. Each trajectory step converts east/north drift in metres per second into a geodesic destination using Earth-radius and latitude-dependent longitude conversion. Wind drift is parameterized and added to the physics fallback.

The predictor exposes a model name and increasing uncertainty radius. The intended next model is a small XGBoost or scikit-learn residual learner trained on projected displacement error against the physics baseline. Features should include prior motion, aligned current/wind vectors, waves, SST, pressure, sea ice, and UTC temporal features. Split by time, never by random rows.

The training command writes `data/models/iceberg_random_forest.joblib` and `iceberg_metrics.json`. It uses 290,174 leakage-free samples, ordered chronologically into 70% training, 15% validation, and 15% test. The current holdout is approximately 1.32 km MAE and 5.76 km RMSE for one observed-step displacement. This is a historical-motion result, not a maritime safety accuracy claim. A GRU is optional only after sufficient gap-aware sequences are available. Evaluation should report Haversine endpoint error and horizon-specific MAE/RMSE at 1h, 6h, 12h, 24h, and 48h.

Sea ice uses a persistence baseline in demo mode. Environmental grids should be subset spatially and lazily loaded before adding an ML model.
