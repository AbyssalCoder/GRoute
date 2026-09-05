import asyncio
import secrets
import smtplib
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from email.message import EmailMessage
from urllib.parse import urlencode
import httpx
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.config import get_settings
from backend.data_sources.ais import AISReplayProvider, DataDockedVesselProvider
from backend.data_sources.aisstream import AISStreamProvider
from backend.data_sources.global_fishing_watch import GlobalFishingWatchProvider
from backend.models.iceberg.predictor import IcebergPredictor
from backend.models.iceberg.random_forest_model import load_artifact
from backend.schemas.common import FeatureCollection, GeoJSONFeature, GeoJSONGeometry, Position
from backend.schemas.iceberg import IcebergRecord, IcebergTrajectory
from backend.schemas.marine import ModelStatus
from backend.schemas.route import RouteRequest, TrackedShip
from backend.services.demo import demo_icebergs, demo_marine, demo_sea_ice, iceberg_points_geojson, load_latest_icebergs, load_historical_icebergs, sea_ice_geojson
from backend.services.routing_service import optimize_route
from backend.services.environment import fetch_route_environment_samples
from backend.services.iceberg_motion import advance_and_save, restore_and_advance

settings = get_settings()

motion_task: asyncio.Task | None = None

async def _iceberg_motion_loop():
    global icebergs
    while True:
        await asyncio.sleep(60)
        icebergs = advance_and_save(icebergs, predictor, settings.iceberg_state_path)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    global icebergs, motion_task
    icebergs = restore_and_advance(icebergs, predictor, settings.iceberg_state_path)
    motion_task = asyncio.create_task(_iceberg_motion_loop())
    try:
        yield
    finally:
        if motion_task:
            motion_task.cancel()
            try:
                await motion_task
            except asyncio.CancelledError:
                pass
        icebergs = advance_and_save(icebergs, predictor, settings.iceberg_state_path)

app = FastAPI(title="GRoute", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):(3000|3001)$", allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

if settings.demo_mode:
    icebergs = demo_icebergs()
else:
    try:
        icebergs = load_latest_icebergs(settings.iceberg_latest_url)
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        print(f"Latest iceberg feed unavailable: {exc}")
        icebergs = []
predictor = IcebergPredictor(ml_available=True)
ais_provider = AISReplayProvider()
datadocked_provider = DataDockedVesselProvider(settings)
aisstream_provider = AISStreamProvider(settings)
global_fish_provider = GlobalFishingWatchProvider(settings)

def merge_vessels(*collections):
    merged = {}
    for collection in collections:
        for vessel in collection.vessels if collection else []:
            merged[vessel.mmsi or vessel.vessel_id] = vessel
    return list(merged.values())

def record_for(identifier: str) -> IcebergRecord:
    for record in icebergs:
        if record.id == identifier:
            return record
    raise HTTPException(status_code=404, detail="Iceberg not found")

def prediction_geojson(record: IcebergRecord, horizon: int) -> FeatureCollection:
    predictions = predictor.predict(record, horizon)
    line = [[record.longitude, record.latitude]] + [[p.longitude,p.latitude] for p in predictions]
    uncertainty = []
    for p in predictions:
        uncertainty.append([p.longitude,p.latitude])
    return FeatureCollection(features=[GeoJSONFeature(geometry=GeoJSONGeometry(type="LineString",coordinates=line),properties={"iceberg_id":record.id,"model":predictor.model_name,"kind":"prediction"}), GeoJSONFeature(geometry=GeoJSONGeometry(type="LineString",coordinates=uncertainty),properties={"iceberg_id":record.id,"kind":"uncertainty_centerline"})])

@app.get("/api/health")
def health():
    return {"status":"ok","demo_mode":settings.demo_mode,"timestamp":datetime.now(timezone.utc).isoformat()}

def _deliver_sos_email(payload: dict) -> dict:
    if not settings.smtp_host:
        return {"status": "not_configured", "detail": "SMTP is not configured. Add SMTP_HOST and SMTP credentials to send email alerts."}
    vessel = payload.get("vessel") or {}
    nearby = payload.get("nearby_icebergs") or []
    message = EmailMessage()
    message["Subject"] = f"GRoute SOS: {vessel.get('name') or vessel.get('id') or 'Tracked vessel'}"
    message["From"] = settings.alert_sender_address
    message["To"] = settings.alert_receiver_address
    message.set_content(
        "GRoute emergency maritime alert\n\n"
        f"Description: {payload.get('description') or 'No description provided.'}\n"
        f"Vessel: {vessel.get('name') or vessel.get('id') or 'Unknown'}\n"
        f"Position: {vessel.get('latitude')}, {vessel.get('longitude')}\n"
        f"Nearby icebergs ({len(nearby)}):\n"
        + "\n".join(f"- {item.get('id', 'Unknown')}: {item.get('latitude')}, {item.get('longitude')}" for item in nearby)
    )
    if settings.smtp_port == 465:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    return {"status": "sent", "detail": f"Alert sent to {settings.alert_receiver_address}."}

@app.post("/api/alerts/sos")
async def send_sos_alert(payload: dict):
    try:
        return await asyncio.to_thread(_deliver_sos_email, payload)
    except (OSError, smtplib.SMTPException) as exc:
        raise HTTPException(status_code=502, detail=f"SOS email delivery failed: {exc}") from exc

@app.get("/api/auth/google")
def google_auth_start():
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google SSO is not configured.")
    state = secrets.token_urlsafe(32)
    query = urlencode({"client_id": settings.google_client_id, "redirect_uri": settings.google_redirect_uri, "response_type": "code", "scope": "openid email profile", "state": state, "access_type": "offline", "prompt": "select_account"})
    response = RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{query}")
    response.set_cookie("groute_oauth_state", state, httponly=True, secure=False, samesite="lax", max_age=600)
    return response

@app.get("/api/auth/oauth/google/callback")
@app.get("/api/v1/auth/oauth/google/callback")
async def google_auth_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        return RedirectResponse(f"{settings.frontend_url}/?sso=error")
    if not code or not state or state != request.cookies.get("groute_oauth_state"):
        raise HTTPException(status_code=400, detail="Invalid Google OAuth state.")
    async with httpx.AsyncClient(timeout=15) as client:
        token_response = await client.post("https://oauth2.googleapis.com/token", data={"code": code, "client_id": settings.google_client_id, "client_secret": settings.google_client_secret, "redirect_uri": settings.google_redirect_uri, "grant_type": "authorization_code"})
        token_response.raise_for_status()
        access_token = token_response.json().get("access_token")
        if not access_token:
            raise HTTPException(status_code=502, detail="Google did not return an access token.")
        profile_response = await client.get("https://openidconnect.googleapis.com/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"})
        profile_response.raise_for_status()
    response = RedirectResponse(f"{settings.frontend_url}/?sso=success")
    response.delete_cookie("groute_oauth_state")
    return response

@app.get("/api/icebergs")
def get_icebergs():
    return {"demo":settings.demo_mode,"source":settings.iceberg_latest_url if not settings.demo_mode else "DEMO DATA","count":len(icebergs),"features":iceberg_points_geojson(icebergs).model_dump()["features"],"historical_tracks":FeatureCollection().model_dump()}

@app.get("/api/iceberg-tracks")
def get_iceberg_tracks():
    return FeatureCollection().model_dump()

@app.get("/api/icebergs/{identifier}")
def get_iceberg(identifier: str):
    return record_for(identifier)

@app.get("/api/icebergs/{identifier}/trajectory")
def get_trajectory(identifier: str, horizon_hours: int = Query(48, ge=1, le=168)):
    record=record_for(identifier); predictions=predictor.predict(record,horizon_hours)
    return IcebergTrajectory(iceberg_id=identifier,model=predictor.model_name,predictions=predictions,geojson=prediction_geojson(record,horizon_hours))

@app.post("/api/predictions/iceberg")
def predict_iceberg(payload: dict):
    identifier=str(payload.get("iceberg_id","")); horizon=int(payload.get("horizon_hours",48))
    return get_trajectory(identifier,horizon)

@app.get("/api/sea-ice")
def get_sea_ice():
    if not settings.demo_mode:
        return {"model":"not configured","demo":False,"source":"Copernicus Marine not configured","geojson":FeatureCollection().model_dump()}
    points=demo_sea_ice()
    return {"model":"persistence_baseline","demo":settings.demo_mode,"geojson":sea_ice_geojson(points).model_dump()}

@app.post("/api/predictions/sea-ice")
def predict_sea_ice():
    return get_sea_ice()

@app.get("/api/marine")
def get_marine():
    if not settings.demo_mode:
        return {"source":"Open-Meteo adapter available","points":[]}
    return {"source":"DEMO DATA" if settings.demo_mode else "Open-Meteo adapter available","points":[p.model_dump(mode="json") for p in demo_marine()]}

@app.get("/api/weather")
def get_weather():
    if not settings.demo_mode:
        return {"source":"ERA5 / Open-Meteo not configured","status":"not configured","points":[]}
    return {"source":"DEMO DATA","status":"available","wind_u_ms":4.2,"wind_v_ms":-2.1,"wave_height_m":2.1}

@app.get("/api/vessels")
async def get_vessels():
    global_fish_provider.start_refresh()
    gfw_vessels = global_fish_provider.cached()
    if aisstream_provider.configured:
        stream_vessels = await aisstream_provider.get_vessels()
        combined = merge_vessels(gfw_vessels, stream_vessels)
        if combined:
            source = "AISStream live AIS + Global Fishing Watch presence" if gfw_vessels and gfw_vessels.vessels else "AISStream live AIS"
            return {"source":source,"demo":False,"vessels":[v.model_dump(mode="json") for v in combined],"trails":stream_vessels.trails.model_dump(mode="json")}
    if gfw_vessels and gfw_vessels.vessels:
        return {"source":"Global Fishing Watch presence","demo":False,**gfw_vessels.model_dump(mode="json")}
    if datadocked_provider.configured:
        try:
            live_vessels = await datadocked_provider.get_vessels()
            if live_vessels and live_vessels.vessels:
                return {"source":"Data Docked live AIS","demo":False,**live_vessels.model_dump(mode="json")}
        except Exception:
            pass
    if not settings.demo_mode:
        return {"source":aisstream_provider.last_error or datadocked_provider.last_error or "AIS not configured","demo":False,"vessels":[],"trails":FeatureCollection().model_dump()}
    return {"source":"Historical AIS Replay","demo":settings.demo_mode,**ais_provider.get_vessels().model_dump(mode="json")}

@app.post("/api/routes/optimize")
async def route(request: RouteRequest):
    global_fish_provider.start_refresh()
    gfw_vessels = global_fish_provider.cached()
    stream_vessels = await aisstream_provider.get_vessels() if aisstream_provider.configured else None
    try:
        live_vessels = await datadocked_provider.get_vessels() if datadocked_provider.configured else None
    except Exception:
        live_vessels = None
    candidates = (stream_vessels.vessels if stream_vessels else []) + (gfw_vessels.vessels if gfw_vessels else []) + (live_vessels.vessels if live_vessels else [])
    tracked = next((vessel for vessel in candidates if vessel.vessel_id == request.vessel_id or vessel.mmsi == request.vessel_id), None)
    if tracked is None and settings.demo_mode:
        replay = ais_provider.get_vessels()
        tracked = next((vessel for vessel in replay.vessels if vessel.vessel_id == request.vessel_id or vessel.mmsi == request.vessel_id), None)
    if tracked is None:
        raise HTTPException(status_code=503, detail="Vessel not found. Configure DATADOCKED_API_KEY and DATADOCKED_AREA_POINTS, or provide a known IMO/MMSI in DATADOCKED_VESSEL_IDS.")
    ship = TrackedShip(vessel_id=tracked.vessel_id, name=tracked.name, latitude=tracked.latitude, longitude=tracked.longitude, destination=tracked.destination)
    request = request.model_copy(update={"start": Position(latitude=tracked.latitude, longitude=tracked.longitude)})
    try:
        midpoint = ((tracked.latitude + request.destination.latitude) / 2, (tracked.longitude + request.destination.longitude) / 2)
        environment = await fetch_route_environment_samples([(tracked.latitude, tracked.longitude), midpoint, (request.destination.latitude, request.destination.longitude)])
    except Exception:
        environment = {"source": "Environmental services unavailable; historical model fallback active"}
    try:
        return optimize_route(request, ship, icebergs, predictor, environment)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

@app.get("/api/models/status", response_model=ModelStatus)
def model_status():
    return ModelStatus(iceberg_model=predictor.model_name if predictor.ml_available else "ML model unavailable - physics baseline active",sea_ice_model="Not configured" if not settings.demo_mode else "Persistence baseline active",route_optimizer="A* primary; Dijkstra fallback",data_sources={"ERA5":"NOT CONFIGURED","Copernicus Marine":"NOT CONFIGURED","Sentinel-1":"NOT CONFIGURED","Open-Meteo":"AVAILABLE","AIS":"Historical AIS Replay" if settings.demo_mode else "NOT CONFIGURED"})

@app.get("/api/models/metrics")
def model_metrics():
    artifact = load_artifact()
    return {"status":"trained" if artifact else "Model not trained","iceberg":artifact["metrics"] if artifact else {},"sea_ice":{},"note":"Metrics are chronological holdout errors for historical motion; they are not a safety guarantee."}

@app.websocket("/ws/maritime")
async def maritime_socket(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"type":"status","message":"Historical AIS Replay","demo":settings.demo_mode})
    try:
        while True:
            await websocket.receive_text()
            await websocket.send_json({"type":"vessels","data":await get_vessels()})
    except Exception:
        await websocket.close()
