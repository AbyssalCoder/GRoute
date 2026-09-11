from fastapi.testclient import TestClient
from backend.main import app
from datetime import datetime, timedelta, timezone
from backend.models.iceberg.physics_model import destination
from backend.models.iceberg.predictor import IcebergPredictor
from backend.routing.risk import iceberg_risk
from backend.services.routing_service import optimize_route
from backend.routing.grid import CostGrid
from backend.services.iceberg_motion import restore_and_advance
from backend.schemas.iceberg import IcebergRecord
from backend.services.demo import load_latest_icebergs
from backend.schemas.route import RouteRequest, TrackedShip

client=TestClient(app)

def test_health():
    response=client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_demo_layers_and_geojson():
    ice=client.get('/api/icebergs').json()
    assert ice['features'][0]['geometry']['type'] == 'Point'
    assert ice['features'][0]['geometry']['coordinates'][0] != ice['features'][0]['geometry']['coordinates'][1]
    assert client.get('/api/sea-ice').json()['geojson']['type'] == 'FeatureCollection'
    assert client.get('/api/vessels').json()['source'] in ('AISStream live AIS', 'AIS not configured', 'Data Docked area lookup returned HTTP 400')

def test_prediction_uncertainty():
    iceberg_id=client.get('/api/icebergs').json()['features'][0]['properties']['id']
    response=client.get(f'/api/icebergs/{iceberg_id}/trajectory?horizon_hours=48')
    assert response.status_code == 200
    predictions=response.json()['predictions']
    assert len(predictions) == 48
    assert predictions[-1]['uncertainty_km'] > predictions[0]['uncertainty_km']

def test_route():
    request=RouteRequest(vessel_id='123456789',start={'latitude':-62,'longitude':-50},destination={'latitude':-66,'longitude':-20},departure_time='2026-09-04T00:00:00Z',mode='balanced')
    response=optimize_route(request, TrackedShip(vessel_id='123456789',name='Aurora',latitude=-62,longitude=-50), [], None)
    assert response.route.geometry.type == 'LineString'
    assert response.ship_route_segments.features[0].properties['kind'] == 'ship'
    assert response.ship_route_segments.features[0].properties['arrival_hours'] > 0
    assert response.iceberg_routes.features == []

def test_route_modes_produce_distinct_paths():
    routes = []
    for mode in ('balanced', 'safest', 'fuel', 'shortest'):
        request = RouteRequest(vessel_id='123456789',start={'latitude':-62,'longitude':-50},destination={'latitude':-66,'longitude':-20},departure_time='2026-09-04T00:00:00Z',mode=mode)
        response = optimize_route(request, TrackedShip(vessel_id='123456789',name='Aurora',latitude=-62,longitude=-50), [], None)
        routes.append(tuple(tuple(point) for point in response.route.geometry.coordinates))
    assert len(set(routes)) == 4

def test_grid_uses_300_km_iceberg_clearance():
    grid = CostGrid((-62, -50), (-66, -20), resolution=0.25, environment={'iceberg_points': [(-62, -50)], 'iceberg_clearance_km': 300})
    assert grid.is_blocked(grid.nearest((-62, -50)))

def test_physics_conversion():
    lat,lon=destination(-65,0,100,0)
    assert lat == -65
    assert lon > 0

def test_historical_icebergs_keep_only_latest_snapshot_members(monkeypatch):
    payload = {
        '01/01/26': [
            {'iceberg': 'A23A', 'recent_observation': '01/01/26', 'lattitude': -6500, 'longitude': -4000},
            {'iceberg': 'stale', 'recent_observation': '01/01/26', 'lattitude': -6600, 'longitude': -4100},
        ],
        '02/01/26': [
            {'iceberg': 'a23a', 'recent_observation': '01/20/26', 'lattitude': -6510, 'longitude': -4010},
            {'iceberg': 'new', 'recent_observation': '01/25/26', 'lattitude': -6700, 'longitude': -4200},
        ],
    }

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return payload

    monkeypatch.setattr('backend.services.demo.httpx.get', lambda url, timeout: FakeResponse())

    records = load_latest_icebergs('https://example.test/icebergs.json')

    assert [record.id for record in records] == ['a23a', 'new']
    assert records[0].timestamp.isoformat() == '2026-01-20T00:00:00+00:00'

def test_iceberg_motion_restores_and_advances_from_saved_state(tmp_path):
    now = datetime(2026, 9, 5, 12, tzinfo=timezone.utc)
    record = IcebergRecord(id='move-me', timestamp=now - timedelta(hours=2), latitude=-65, longitude=-20, velocity_v=1.0)
    predictor = IcebergPredictor(ml_available=False)
    state_path = tmp_path / 'iceberg_motion_state.json'

    first = restore_and_advance([record], predictor, state_path, now)
    second = restore_and_advance([record], predictor, state_path, now + timedelta(hours=1))

    assert state_path.exists()
    assert first[0].latitude > record.latitude
    assert second[0].latitude > first[0].latitude
    assert second[0].timestamp == now + timedelta(hours=1)

def test_sos_alert_reports_missing_smtp_configuration(monkeypatch):
    monkeypatch.setattr('backend.main.settings.smtp_host', '')
    response = client.post('/api/alerts/sos', json={'vessel': {'name': 'Test Vessel', 'latitude': -60, 'longitude': -30}, 'nearby_icebergs': [], 'description': 'Test alert'})
    assert response.status_code == 200
    assert response.json()['status'] == 'not_configured'
