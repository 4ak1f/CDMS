from dotenv import load_dotenv
load_dotenv()

from backend.flow_detection import CrowdFlowDetector
from backend.report_generator import generate_incident_report
from backend.email_alerts import send_danger_alert
from backend.sms_alerts import send_sms_alert, send_surge_sms, get_sms_status
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.detector import detect_people
from backend.density import estimate_density
from backend.alerts import generate_alert, get_recent_alerts
from backend.database import init_db, log_detection, get_all_detections, get_thresholds, save_thresholds
from backend.crowd_model import (
    load_model, generate_density_map,
    generate_heatmap, overlay_heatmap,
    analyze_zones, draw_zones
)
from backend.database import (init_db, log_detection, get_all_detections,
    get_thresholds, save_thresholds, store_feedback, get_feedback_stats,
    get_all_feedback, log_incident, get_incidents, clear_detections,
    archive_old_detections, save_zone_config, get_zone_config,
    get_location_config, save_location_config)
import cv2
import numpy as np
import base64
import json
import os
import asyncio
import time
import urllib.request
from backend.database import init_db, log_detection, get_all_detections, get_thresholds, save_thresholds, store_feedback, get_feedback_stats, get_all_feedback
from backend.calibration import (get_full_scene_params, update_params_for_scene,
                                 load_scene_params, get_scene_learning_summary)
from backend.supabase_sync import (
    sync_detection, sync_feedback, sync_incident,
    bulk_archive_and_clear, get_cloud_stats, is_connected as supabase_connected
)
from backend.camera_session import (
    create_session, get_session, join_session, leave_session,
    update_camera, get_session_cameras, get_session_aggregate, list_all_sessions
)
from backend.webrtc_handler import handle_offer, close_camera
from backend.scheduler import (
    init_scheduler, start_schedule, stop_schedule, get_schedule_config,
    update_heartbeat, enable_deadman, disable_deadman, get_deadman_status
)
from backend.anomaly_detector import (
    analyze_for_anomalies, get_recent_anomalies,
    get_anomaly_stats, get_crowd_flow_state, record_count
)
from backend.auth import (
    init_auth_tables, login, create_user, get_all_users,
    verify_token, update_user_role, deactivate_user, get_user_by_id
)
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

app = FastAPI(title="CDMS - Crowd Disaster Management System")

security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    return verify_token(credentials.credentials)

def require_auth(user = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def require_admin(user = Depends(get_current_user)):
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

_current_session = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/mobile", StaticFiles(directory="pwa"), name="pwa")

# Serve React build
if os.path.exists("frontend-react/dist"):
    app.mount("/assets", StaticFiles(
        directory="frontend-react/dist/assets"), name="react-assets")

init_db()
init_auth_tables()

# Ensure Supabase anomalies table exists
def _setup_anomalies_table():
    from backend.supabase_sync import get_client
    client = get_client()
    if not client:
        return {"status": "skipped", "reason": "Supabase not configured"}
    try:
        client.table("anomalies").select("id").limit(1).execute()
        return {"status": "ok", "message": "Anomalies table ready"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

_anomaly_setup = _setup_anomalies_table()
print(f"📊 Anomaly detection: {_anomaly_setup.get('status', 'unknown')}")

print("🚀 Loading crowd counting model...")
crowd_model, model_device = load_model()
from backend.model_ensemble import CrowdEnsemble
ensemble = CrowdEnsemble(crowd_model, model_device)
flow_detector = CrowdFlowDetector()
print("✅ System ready!")
init_scheduler(None)  # analyze_frame_for_camera defined later; scheduler re-init on first use


def process_frame(frame, crowd_mode="auto"):
    """
    Full processing pipeline for a single frame.
    Returns: annotated_frame, density_result, zones, alert, flow_result, confidence
    """
    frame_start = time.time()

    # Get unified scene parameters (fingerprint-based if learned, else scene-type)
    scene_params_data = get_full_scene_params(frame)
    scene_conf        = scene_params_data["conf"]
    scene_iou         = scene_params_data["iou"]
    scene_type        = scene_params_data["scene_type"]

    h, w = frame.shape[:2]

    # Step 1: Primary engine — custom trained model (also returns fingerprint)
    density_map, model_count, confidence, scene_fingerprint = generate_density_map(crowd_model, model_device, frame)

    # Step 2: YOLO detection (uses scene-learned conf/iou)
    _, yolo_count, detections = detect_people(
        frame,
        conf_override=scene_conf,
        iou_override=scene_iou
    )

    # Step 3: Ensemble prediction
    ensemble_result = ensemble.predict(
        frame, yolo_count, model_count, confidence, crowd_mode
    )

    # Step 3b: Scene-type-aware final count — fixes sparse overcounting
    # ensemble_result["count"] is the density/blend estimate; YOLO is used as sanity anchor
    scaled_density_count = ensemble_result["count"]
    if yolo_count is not None and yolo_count > 0:
        if scene_type and ("dense" in scene_type or "mega" in scene_type):
            # Dense/mega: never let YOLO cap the density model
            # YOLO only sees foreground — density model sees the full crowd
            if scaled_density_count > yolo_count * 5:
                # Density model says much more than YOLO — trust density
                final_count = scaled_density_count
            else:
                # Moderate disagreement — weight toward density model
                final_count = (scaled_density_count * 0.85) + (yolo_count * 0.15)
        elif scene_type and "sparse" in scene_type:
            if yolo_count <= 3:
                # Very sparse: trust YOLO completely
                final_count = yolo_count
            elif yolo_count <= 10:
                # Sparse: heavily weight YOLO
                final_count = (scaled_density_count * 0.15) + (yolo_count * 0.85)
            else:
                final_count = (scaled_density_count * 0.3) + (yolo_count * 0.7)
        else:
            # Moderate: balanced blend
            final_count = (scaled_density_count * 0.6) + (yolo_count * 0.4)
    else:
        final_count = scaled_density_count
    # Proper rounding: never promote a sub-0.5 count to 1 (avoids 0→1 false positives)
    final_count = int(final_count + 0.5) if final_count >= 0.5 else 0

        # Step 4: Heatmap + zones (must happen before drawing boxes)
    heatmap = generate_heatmap(density_map, frame.shape)
    heatmap_frame = overlay_heatmap(frame, heatmap, alpha=0.45)
    zones = analyze_zones(density_map, frame.shape, grid_rows=3, grid_cols=3)
    annotated_frame = draw_zones(heatmap_frame, zones)

        # Step 5: Crowd flow detection
    flow_result, annotated_frame = flow_detector.detect_flow(annotated_frame)

        # Step 6: Draw bounding boxes for sparse crowds (no text labels)
    if ensemble_result["method"].startswith("YOLO"):
            for det in detections:
                x1, y1, x2, y2 = det["bbox"]
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    # Step 7: Risk classification with thresholds
    thresholds    = get_thresholds()
    danger_label  = thresholds["danger_label"]
    warning_label = thresholds["warning_label"]

    # Confidence weighting — low confidence detections get dampened for alert decisions
    conf_min_val, conf_max_val = confidence  # tuple from generate_density_map
    conf_range = max(conf_max_val - conf_min_val, 1)
    raw_confidence = 1.0 - min(conf_range / max(final_count, 1), 1.0)
    confidence_weight = 0.6 + (0.4 * raw_confidence)
    effective_count = round(final_count * confidence_weight)

    density_result = estimate_density(effective_count, w, h, thresholds)
    density_result["person_count"] = int(final_count)  # restore original count
    density_result["confidence_score"] = round(raw_confidence * 100, 1)
    density_result["confidence_weight"] = round(confidence_weight, 2)
    density_result["effective_count"] = effective_count

    # Override if surge detected
    if flow_result.get("surge_detected"):
        density_result["risk_level"] = danger_label
        density_result["color"]      = "red"
        density_result["message"]    = f"ALERT: {danger_label} — Surge detected!"
        flow_state_info = get_crowd_flow_state()
        send_surge_sms(
            person_count=int(final_count),
            rate=abs(flow_state_info.get("rate_per_min", 0)),
            location=get_location_config().get("name", "Main Location")
        )

    # Step 8: (text overlay removed — UI displays all info)
    risk = density_result["risk_level"]

    # Step 9: Alert, log, report, email
    alert = generate_alert(density_result)
    log_detection(
        int(final_count),
        density_result["density_score"],
        density_result["risk_level"],
        density_result["message"]
    )

    # Auto-archive to Supabase every 100 detections
    all_dets = get_all_detections(limit=101)
    if len(all_dets) >= 100:
        print(f"📦 100 detections reached — archiving to Supabase cloud...")
        archive_result = bulk_archive_and_clear(all_dets)
        if archive_result["error"] is None:
            clear_detections()
            print(f"✅ Local DB cleared after cloud archive ({archive_result['synced']} records)")
        else:
            print(f"⚠️  Archive failed, keeping local data: {archive_result['error']}")

    # Sync this detection to cloud in real-time
    sync_detection({
        "timestamp":         density_result.get("timestamp", ""),
        "person_count":      density_result.get("person_count", 0),
        "density_score":     density_result.get("density_score", 0.0),
        "risk_level":        density_result.get("risk_level", "SAFE"),
        "scene_type":        density_result.get("scene_type", "unknown"),
        "scene_fingerprint": density_result.get("scene_fingerprint", "unknown"),
        "message":           density_result.get("message", ""),
    })

    # Log incidents separately for WARNING/DANGER only
    if risk in ["WARNING", "DANGER", "OVERCROWDED"]:
        log_incident(int(final_count), density_result["density_score"],
                    risk, density_result["message"], zones)
        sync_incident({
            "person_count":  int(final_count),
            "density_score": density_result.get("density_score", 0),
            "risk_level":    risk,
            "message":       density_result.get("message", ""),
        })
    if risk in ["DANGER", "OVERCROWDED"]:
        report_path, _ = generate_incident_report(
            trigger_event="Automated detection",
            person_count=int(final_count),
            risk_level=risk,
            density_score=density_result["density_score"],
            zone_data=zones,
            flow_data=flow_result
        )
        send_danger_alert(
            int(final_count),
            density_result["density_score"],
            risk,
            density_result["message"],
            report_path
        )
        loc_cfg = get_location_config()
        sms_result = send_sms_alert(
            person_count=int(final_count),
            risk_level=risk,
            message=density_result.get("message", ""),
            scene_type=scene_type or "unknown",
            location=loc_cfg.get("name", "Main Location")
        )
        if sms_result.get("sent"):
            print(f"📱 SMS alert sent for {risk} event")
    density_result["scene_fingerprint"] = scene_fingerprint
    density_result["scene_type"] = scene_type
    inference_ms = round((time.time() - frame_start) * 1000)
    return annotated_frame, density_result, zones, alert, flow_result, confidence, inference_ms


@app.get("/")
async def serve_root():
    return FileResponse("frontend-react/dist/index.html")



@app.post("/analyze/image")
async def analyze_image(
    file: UploadFile = File(...),
    mode: str = "auto",
    camera_id: str = "",
    session_code: str = "",
):
    contents = await file.read()
    np_arr   = np.frombuffer(contents, np.uint8)
    frame    = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if frame is None:
        return JSONResponse({"error": "Invalid image file"}, status_code=400)

    annotated_frame, density_result, zones, alert, flow_result, confidence, inference_ms = process_frame(frame, mode)
    update_heartbeat()

    # If called from a phone camera, update its session entry automatically
    if camera_id and session_code:
        update_camera(session_code, camera_id, {
            "person_count":      density_result.get("person_count", 0),
            "risk_level":        density_result.get("risk_level", "SAFE"),
            "scene_type":        density_result.get("scene_type", "unknown"),
            "scene_fingerprint": density_result.get("scene_fingerprint", "unknown"),
            "active":            True,
        })

    location_cfg = get_location_config()
    max_cap = location_cfg["max_capacity"]
    img_person_count = density_result.get("person_count", 0)
    capacity_pct = round(img_person_count / max(max_cap, 1) * 100, 1)
    capacity_status = "normal"
    if capacity_pct >= location_cfg["critical_pct"] * 100:
        capacity_status = "critical"
    elif capacity_pct >= location_cfg["warning_pct"] * 100:
        capacity_status = "warning"
    elif capacity_pct >= location_cfg["caution_pct"] * 100:
        capacity_status = "caution"

    anomaly    = analyze_for_anomalies(density_result["person_count"])
    flow_state = get_crowd_flow_state()

    _, buffer = cv2.imencode(".jpg", annotated_frame)
    img_base64 = base64.b64encode(buffer).decode("utf-8")

    return {
        "person_count":    density_result["person_count"],
        "density_score":   density_result["density_score"],
        "risk_level":      density_result["risk_level"],
        "color":           density_result["color"],
        "message":         density_result["message"],
        "confidence_min":  confidence[0],
        "confidence_max":  confidence[1],
        "alert":             alert,
        "inference_ms":      inference_ms,
        "scene_fingerprint": density_result.get("scene_fingerprint"),
        "scene_type":        density_result.get("scene_type"),
        "confidence_score":  density_result.get("confidence_score", 0),
        "confidence_weight": density_result.get("confidence_weight", 1.0),
        "effective_count":   density_result.get("effective_count", 0),
        "capacity_pct":      capacity_pct,
        "capacity_status":   capacity_status,
        "max_capacity":      max_cap,
        "anomaly":           anomaly,
        "crowd_flow":        flow_state,
        "flow_direction":    flow_result.get("direction", "Unknown"),
        "flow_speed":        float(flow_result.get("speed", 0) or 0),
        "flow_state":        flow_result.get("state", "STABLE"),
        "surge_detected":    bool(flow_result.get("surge_detected", False)),
        "flow_vectors":      flow_result.get("vector_count", 0),
        "zones": [{
            "zone":    z["zone"],
            "count":   z["count"],
            "risk":    z["risk"],
            "density": z["density"]
        } for z in zones],
        "annotated_image": img_base64
    }


@app.post("/analyze/video")
async def analyze_video(file: UploadFile = File(...), mode: str = "auto"):
    os.makedirs("uploads", exist_ok=True)
    video_path = f"uploads/{file.filename}"

    with open(video_path, "wb") as f:
        f.write(await file.read())

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        return JSONResponse({"error": "Could not open video file."}, status_code=400)

    frame_results = []
    frame_num     = 0
    max_frames    = 20

    while cap.isOpened() and len(frame_results) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        frame_num += 1
        if frame_num % 30 != 0:
            continue
        frame = cv2.resize(frame, (640, 360))
        _, density_result, zones, _, _, _, _ = process_frame(frame, mode)
        frame_results.append(density_result)

    cap.release()

    if not frame_results:
        return JSONResponse({"error": "Could not process video"}, status_code=400)
    update_heartbeat()

    counts     = [r["person_count"] for r in frame_results]
    scores     = [r["density_score"] for r in frame_results]
    risk_levels = [r["risk_level"] for r in frame_results]

    overall_risk = "SAFE"
    if any(r in ["DANGER", "OVERCROWDED"] for r in risk_levels):
        overall_risk = "OVERCROWDED"
    elif "WARNING" in risk_levels:
        overall_risk = "WARNING"

    location_cfg = get_location_config()
    max_cap = location_cfg["max_capacity"]
    peak_count = max(counts)
    capacity_pct = round(peak_count / max(max_cap, 1) * 100, 1)
    capacity_status = "normal"
    if capacity_pct >= location_cfg["critical_pct"] * 100:
        capacity_status = "critical"
    elif capacity_pct >= location_cfg["warning_pct"] * 100:
        capacity_status = "warning"
    elif capacity_pct >= location_cfg["caution_pct"] * 100:
        capacity_status = "caution"

    anomaly    = analyze_for_anomalies(peak_count)
    flow_state = get_crowd_flow_state()

    return {
        "frames_analyzed":  len(frame_results),
        "avg_person_count": round(sum(counts) / len(counts), 1),
        "max_person_count": peak_count,
        "avg_density_score": round(sum(scores) / len(scores), 4),
        "max_density_score": round(max(scores), 4),
        "overall_risk":     overall_risk,
        "danger_frames":    sum(1 for r in risk_levels if r in ["DANGER", "OVERCROWDED"]),
        "warning_frames":   risk_levels.count("WARNING"),
        "safe_frames":      risk_levels.count("SAFE"),
        "capacity_pct":     capacity_pct,
        "capacity_status":  capacity_status,
        "max_capacity":     max_cap,
        "anomaly":          anomaly,
        "crowd_flow":       flow_state,
        "flow_direction":   flow_state.get("direction", "Unknown"),
        "flow_speed":       flow_state.get("rate_per_min", 0),
        "flow_state":       "STABLE",
        "surge_detected":   False,
        "flow_vectors":     0,
    }


@app.websocket("/ws/webcam")
async def webcam_stream(websocket: WebSocket):
    await websocket.accept()
    print("📹 Webcam stream connected")
    try:
        while True:
            data       = await websocket.receive_text()
            payload    = json.loads(data)
            img_data   = base64.b64decode(payload["frame"])
            crowd_mode = payload.get("mode", "auto")
            np_arr     = np.frombuffer(img_data, np.uint8)
            frame      = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            annotated_frame, density_result, zones, alert, flow_result, confidence, inference_ms = process_frame(frame, crowd_mode)
            update_heartbeat()
            record_count(density_result["person_count"])
            ws_anomaly  = analyze_for_anomalies(density_result["person_count"])
            ws_flow     = get_crowd_flow_state()

            _, buffer  = cv2.imencode(".jpg", annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            result_b64 = base64.b64encode(buffer).decode("utf-8")

            total_count = density_result["person_count"]
            if zones and total_count > 0:
                raw_total = sum(z.get("count", 0) for z in zones)
                if raw_total > 0:
                    for z in zones:
                        z["count"] = max(0, round((z.get("count", 0) / raw_total) * total_count))

            await websocket.send_json({
                "frame":          result_b64,
                "person_count":   density_result["person_count"],
                "density_score":  density_result["density_score"],
                "risk_level":     density_result["risk_level"],
                "message":        density_result["message"],
                "confidence_min": confidence[0],
                "confidence_max": confidence[1],
                "alert":             alert is not None,
                "inference_ms":      inference_ms,
                "scene_fingerprint": density_result.get("scene_fingerprint"),
                "scene_type":        density_result.get("scene_type", "unknown"),
                "confidence_score":  density_result.get("confidence_score", 0),
                "effective_count":   density_result.get("effective_count", 0),
                "anomaly":           ws_anomaly,
                "crowd_flow":        ws_flow,
                "flow_direction":    flow_result.get("direction", "Unknown"),
                "flow_speed":        float(flow_result.get("speed", 0)),
                "surge_detected":    flow_result.get("surge_detected", False),
                "flow_state":        flow_result.get("state", "STABLE"),
                "zones": [{
                    "zone":  z["zone"],
                    "count": z["count"],
                    "risk":  z["risk"]
                } for z in zones]
            })

    except WebSocketDisconnect:
        print("📹 Webcam stream disconnected")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data    = await websocket.receive_text()
            payload = json.loads(data)
            img_data   = base64.b64decode(payload["frame"])
            crowd_mode = payload.get("mode", "auto")
            np_arr  = np.frombuffer(img_data, np.uint8)
            frame   = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is None:
                await websocket.send_json({"error": "invalid frame"})
                continue
            try:
                annotated, density_result, zones, alert, flow_result, confidence, inference_ms = process_frame(frame, crowd_mode)
                analyze_for_anomalies(density_result.get("person_count", 0))
                total_count = density_result.get("person_count", 0)
                if zones and total_count > 0:
                    raw_total = sum(z.get("count", 0) for z in zones)
                    if raw_total > 0:
                        for z in zones:
                            z["count"] = max(0, round((z.get("count", 0) / raw_total) * total_count))
                _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                await websocket.send_json({
                    "person_count":      density_result.get("person_count", 0),
                    "risk_level":        density_result.get("risk_level", "SAFE"),
                    "density_score":     density_result.get("density_score", 0),
                    "message":           density_result.get("message", ""),
                    "scene_type":        density_result.get("scene_type", "unknown"),
                    "scene_fingerprint": density_result.get("scene_fingerprint", "unknown"),
                    "confidence_score":  density_result.get("confidence_score", 0),
                    "flow_direction":    flow_result.get("direction", "Unknown"),
                    "flow_speed":        float(flow_result.get("speed", 0)),
                    "surge_detected":    flow_result.get("surge_detected", False),
                    "frame":             frame_b64,
                    "inference_ms":      inference_ms,
                })
            except Exception as e:
                await websocket.send_json({"error": str(e), "person_count": 0, "risk_level": "SAFE"})
    except WebSocketDisconnect:
        print("📷 Webcam /ws disconnected")
    except Exception as e:
        print(f"WebSocket /ws error: {e}")


@app.get("/history")
def get_history():
    return get_all_detections(limit=50)


@app.get("/alerts")
def get_alerts():
    return {"alerts": get_recent_alerts(limit=20)}


@app.get("/stats")
def get_stats():
    detections = get_all_detections(limit=200)

    if not detections:
        return {
            "total_detections": 0,
            "total_alerts": 0,
            "avg_crowd": 0,
            "peak_crowd": 0,
            "risk_distribution": {"SAFE": 0, "WARNING": 0, "DANGER": 0},
            "recent_counts": [],
            "recent_timestamps": []
        }

    risk_dist = {"SAFE": 0, "WARNING": 0, "DANGER": 0}
    for d in detections:
        risk = d["risk_level"]
        if risk in ["DANGER", "OVERCROWDED"]:
            risk_dist["DANGER"] = risk_dist.get("DANGER", 0) + 1
        elif risk == "WARNING":
            risk_dist["WARNING"] = risk_dist.get("WARNING", 0) + 1
        else:
            risk_dist["SAFE"] = risk_dist.get("SAFE", 0) + 1

    recent = detections[:20]
    return {
        "total_detections": len(detections),
        "total_alerts":     sum(1 for d in detections if d["risk_level"] in ["WARNING", "DANGER", "OVERCROWDED"]),
        "avg_crowd":        round(sum(d["person_count"] for d in detections) / len(detections), 1),
        "peak_crowd":       max(d["person_count"] for d in detections),
        "risk_distribution": risk_dist,
        "recent_counts":    [d["person_count"] for d in reversed(recent)],
        "recent_timestamps": [d["timestamp"] for d in reversed(recent)]
    }


@app.get("/reports")
def list_reports():
    reports_dir = "logs/reports"
    if not os.path.exists(reports_dir):
        return {"reports": []}
    files = sorted(os.listdir(reports_dir), reverse=True)
    return {"reports": [f for f in files if f.endswith('.pdf')]}


@app.get("/reports/download/{filename}")
def download_report(filename: str):
    from fastapi.responses import FileResponse
    filepath = f"logs/reports/{filename}"
    if not os.path.exists(filepath):
        return JSONResponse({"error": "Report not found"}, status_code=404)
    return FileResponse(filepath, media_type='application/pdf', filename=filename)


@app.post("/reports/generate")
async def manual_report():
    detections = get_all_detections(limit=1)
    if not detections:
        return JSONResponse({"error": "No detection data available"}, status_code=400)
    latest = detections[0]
    report_path, filename = generate_incident_report(
        trigger_event="Manual report request",
        person_count=latest["person_count"],
        risk_level=latest["risk_level"],
        density_score=latest["density_score"]
    )
    return {"message": "Report generated", "filename": filename}


@app.get("/thresholds")
def get_threshold_settings():
    return get_thresholds()


@app.post("/thresholds")
async def update_thresholds(request: Request):
    body    = await request.json()
    warning = float(body.get("warning_threshold", 2.0))
    danger  = float(body.get("danger_threshold",  5.0))

    if warning <= 0 or danger <= 0 or warning >= danger:
        return JSONResponse(
            {"error": "Invalid thresholds. Warning must be less than danger and both must be positive."},
            status_code=400
        )

    save_thresholds(warning, danger)
    return {"message": "Thresholds updated", "warning": warning, "danger": danger}
@app.post("/feedback")
async def submit_feedback(request: Request):
    """
    Accepts user correction of crowd count.
    Stores for model calibration and future retraining.
    """
    body        = await request.json()
    predicted   = int(body.get("predicted_count", 0))
    actual      = int(body.get("actual_count", 0))
    scene       = body.get("scene_type", "unknown")
    fingerprint = body.get("scene_fingerprint", "unknown")

    if actual < 0:
        return JSONResponse({"error": "Invalid count"}, status_code=400)

    # Store general feedback for scene-type calibration
    store_feedback(predicted, actual, scene)
    sync_feedback(predicted, actual, scene, fingerprint)

    # Update fingerprint-specific learned parameters
    learned = None
    if fingerprint and fingerprint != "unknown":
        from backend.calibration import update_params_for_scene
        learned = update_params_for_scene(fingerprint, predicted, actual)
        print(f"🧠 Scene '{fingerprint}': pred={predicted} actual={actual} → scale={learned['scale']:.2f}")
    else:
        print(f"⚠️  Feedback received without scene fingerprint — general feedback stored only")

    return {
        "status": "ok",
        "message": "Feedback received and model updated",
        "scene_fingerprint": fingerprint,
        "corrections_so_far": learned["corrections"] if learned else 0,
        "current_scale": round(learned["scale"], 2) if learned else 1.0,
        "impact": f"Scale adjusted to {learned['scale']:.2f} for this scene" if learned else "General feedback stored"
    }


@app.get("/feedback")
def get_feedback():
    """Returns all stored feedback entries."""
    return {
        "feedback": get_all_feedback(limit=50),
        "stats":    get_feedback_stats()
    }


@app.get("/calibration")
def get_calibration_stats():
    """Returns calibration statistics per scene type plus per-scene learned params."""
    stats         = get_feedback_stats()
    scene_summary = get_scene_learning_summary()
    return {
        "scene_calibrations":    stats,
        "total_feedback_samples": sum(v["sample_count"] for v in stats.values()),
        "scene_learning":         scene_summary,
        "total_scenes_learned":   len(scene_summary),
        "converged_scenes":       sum(1 for s in scene_summary if s["status"] == "converged"),
    }


@app.post("/calibration/reset-scene/{fingerprint}")
async def reset_scene_params(fingerprint: str, admin=Depends(require_admin)):
    """Reset learned params for a specific scene fingerprint."""
    from backend.calibration import load_scene_params, save_scene_params
    params = load_scene_params()
    if fingerprint in params:
        del params[fingerprint]
        save_scene_params(params)
        return {"status": "ok", "message": f"Reset params for {fingerprint}"}
    return {"status": "not_found"}


@app.post("/calibration/reset-all")
async def reset_all_scene_params(admin=Depends(require_admin)):
    """Reset ALL learned scene params."""
    from backend.calibration import save_scene_params
    save_scene_params({})
    return {"status": "ok", "message": "All scene params reset"}
@app.post("/logs/clear")
def clear_logs():
    """Clears all detection history from database."""
    import sqlite3
    conn = sqlite3.connect("logs/cdms.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM detections")
    conn.commit()
    conn.close()
    # Also clear the log file
    with open("logs/alerts.log", "w") as f:
        f.write("")
    return {"message": "Logs cleared successfully"}

@app.get("/incidents")
def get_incident_log():
    return get_incidents(limit=50)

@app.post("/logs/clear")
def clear_logs():
    clear_detections()
    if os.path.exists("logs/alerts.log"):
        open("logs/alerts.log", "w").close()
    return {"message": "Logs cleared"}

@app.post("/logs/archive")
def archive_logs():
    deleted = archive_old_detections(days=30)
    return {"message": f"Archived {deleted} records older than 30 days"}

@app.get("/zones/config")
def get_zones():
    return get_zone_config()

@app.post("/zones/config")
async def save_zones(request: Request):
    body = await request.json()
    save_zone_config(body)
    return {"message": "Zone config saved"}


@app.get("/learning/status")
def get_learning_status():
    from backend.calibration import load_scene_params
    scene_params = load_scene_params()
    return {
        "scenes_learned": len(scene_params),
        "scene_details":  {
            fp: {
                "corrections": p["corrections"],
                "current_conf": p["conf"],
                "current_iou":  p["iou"],
                "current_scale": p["scale"],
                "avg_recent_ratio": round(
                    sum(h["ratio"] for h in p["history"][-5:]) /
                    max(len(p["history"][-5:]), 1), 2
                ) if p["history"] else 1.0
            }
            for fp, p in scene_params.items()
        },
        "how_it_works": (
            "Each unique visual scene gets its own parameter profile. "
            "When corrected, only that scene profile updates. "
            "Next time the same scene appears, learned parameters apply immediately."
        )
    }


def _format_uptime(seconds: int) -> str:
    d, rem = divmod(seconds, 86400)
    h, m = divmod(rem, 3600)
    m = m // 60
    if d: return f"{d}d {h}h {m}m"
    if h: return f"{h}h {m}m"
    return f"{m}m"


@app.get("/system/stats")
def get_system_stats():
    import psutil
    import torch as _torch
    uptime_s = round(time.time() - psutil.boot_time())
    mae_val = None
    try:
        ck = _torch.load(
            "model_training/checkpoints/best_model.pth",
            map_location="cpu", weights_only=False
        )
        mae_val = round(float(ck.get("best_mae", 0)), 2)
    except Exception:
        pass
    return {
        "cpu_percent":    round(psutil.cpu_percent(interval=0.1), 1),
        "memory_percent": round(psutil.virtual_memory().percent, 1),
        "memory_used_gb": round(psutil.virtual_memory().used / (1024**3), 1),
        "uptime_seconds": uptime_s,
        "uptime_human":   _format_uptime(uptime_s),
        "model_mae":      mae_val,
    }


@app.get("/cloud/stats")
def cloud_statistics():
    """Returns aggregate stats from Supabase cloud database."""
    return {
        "connected": supabase_connected(),
        "stats": get_cloud_stats()
    }


@app.post("/cloud/archive")
async def manual_archive():
    """Manually triggers archive of local detections to Supabase."""
    all_dets = get_all_detections(limit=10000)
    if not all_dets:
        return {"status": "nothing_to_archive", "count": 0}
    result = bulk_archive_and_clear(all_dets)
    if result["error"] is None:
        clear_detections()
        return {"status": "ok", "archived": result["synced"], "local_cleared": True}
    return {"status": "error", "error": result["error"]}


@app.get("/cloud/status")
def cloud_status():
    return {
        "supabase_connected": supabase_connected(),
        "url": os.getenv("SUPABASE_URL", "not configured"),
    }


# ── Multi-camera session helpers ─────────────────────────────────────────────

def analyze_frame_for_camera(frame_bgr):
    """Lightweight wrapper around process_frame for phone camera streams."""
    try:
        _, density_result, zones, alert, flow_result, confidence, _ = process_frame(frame_bgr)
        return {
            "person_count":      density_result.get("person_count", 0),
            "risk_level":        density_result.get("risk_level", "SAFE"),
            "scene_type":        density_result.get("scene_type", "unknown"),
            "scene_fingerprint": density_result.get("scene_fingerprint", "unknown"),
            "message":           density_result.get("message", ""),
        }
    except Exception as e:
        print(f"⚠️  Camera frame analysis error: {e}")
        return {"person_count": 0, "risk_level": "SAFE", "scene_type": "unknown",
                "scene_fingerprint": "unknown", "message": ""}


# ── Session endpoints ─────────────────────────────────────────────────────────

@app.post("/session/create")
async def create_camera_session():
    """Create a new multi-camera session."""
    global _current_session
    session = create_session()
    _current_session = session["code"]
    return {
        "code":       session["code"],
        "join_url":   f"/camera/{session['code']}" ,
        "created_at": session["created_at"],
    }


@app.get("/session/current")
async def get_current_session():
    """Get current active session and all cameras."""
    global _current_session
    if not _current_session:
        return {"active": False, "cameras": [], "aggregate": {}}
    agg = get_session_aggregate(_current_session)
    return {
        "active":   True,
        "code":     _current_session,
        "join_url": f"/camera/{_current_session}",
        **agg,
    }


@app.post("/session/webrtc/offer")
async def webrtc_offer(request: Request):
    """Handle WebRTC offer from a phone camera."""
    body         = await request.json()
    session_code = body.get("session_code")
    camera_name  = body.get("camera_name", "Mobile Camera")
    sdp          = body.get("sdp")
    sdp_type     = body.get("type", "offer")

    if not session_code or not sdp:
        return JSONResponse({"error": "Missing session_code or sdp"}, status_code=400)

    answer = await handle_offer(
        session_code=session_code,
        camera_name=camera_name,
        sdp=sdp,
        sdp_type=sdp_type,
        analyze_fn=analyze_frame_for_camera,
    )
    return answer


@app.get("/session/list")
async def session_list():
    return {"sessions": list_all_sessions()}


@app.get("/session/{code}/cameras")
async def session_cameras(code: str):
    """Get all cameras in a session."""
    cameras = get_session_cameras(code)
    agg     = get_session_aggregate(code)
    return {"cameras": cameras, "aggregate": agg}


@app.get("/session/{code}/aggregate")
async def session_aggregate(code: str):
    """Get aggregate crowd count across all cameras."""
    return get_session_aggregate(code)


@app.post("/session/join")
async def session_join_http(request: Request):
    """HTTP-based camera join — no WebRTC needed."""
    body = await request.json()
    code   = body.get("session_code", "")
    name   = body.get("camera_name", "Mobile Camera")
    camera = join_session(code, name)
    if not camera:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    return camera


@app.post("/session/update-camera")
async def session_update_camera_http(request: Request):
    """Update camera stats from HTTP-based camera client."""
    body      = await request.json()
    code      = body.get("session_code", "")
    camera_id = body.get("camera_id",    "")
    if not code or not camera_id:
        return JSONResponse({"error": "Missing fields"}, status_code=400)
    update_camera(code, camera_id, {
        "person_count": int(body.get("person_count", 0)),
        "risk_level":   body.get("risk_level",   "SAFE"),
        "scene_type":   body.get("scene_type",   "unknown"),
        "last_seen":    __import__('time').time(),
        "active":       True,
    })
    return {"status": "ok"}


@app.get("/camera/{session_code}", response_class=HTMLResponse)
async def camera_page(session_code: str):
    session = get_session(session_code)
    if not session:
        return HTMLResponse(
            "<h2 style='font-family:sans-serif;text-align:center;margin-top:40px'>Session not found or expired</h2>",
            status_code=404
        )
    with open("frontend/camera.html") as f:
        html = f.read().replace("{{SESSION_CODE}}", session_code)
    return HTMLResponse(html)


# ── ngrok URL endpoint ────────────────────────────────────────────────────────

@app.get("/ngrok/url")
def ngrok_url():
    """Returns the active ngrok public URL. Checks file written by start.sh first, then falls back to ngrok API."""
    # File-first: start.sh writes the URL here after confirming ngrok is ready
    try:
        with open("/tmp/cdms_ngrok_url.txt") as f:
            url = f.read().strip()
        if url:
            return {"url": url, "active": True, "source": "file"}
    except Exception:
        pass
    # Fallback: query ngrok API directly
    try:
        with urllib.request.urlopen("http://localhost:4040/api/tunnels", timeout=2) as resp:
            data    = json.loads(resp.read())
            tunnels = data.get("tunnels", [])
            for t in tunnels:
                if t.get("proto") == "https":
                    return {"url": t["public_url"], "active": True, "source": "api"}
            if tunnels:
                return {"url": tunnels[0]["public_url"], "active": True, "source": "api"}
    except Exception:
        pass
    return {"url": None, "active": False, "source": "none"}


# ── Location capacity endpoints ───────────────────────────────────────────────

@app.get("/location/config")
def get_location_configuration():
    return get_location_config()


@app.post("/location/config")
async def save_location_configuration(request: Request):
    body = await request.json()
    save_location_config(
        name=body.get("name", "Main Location"),
        max_capacity=int(body.get("max_capacity", 100)),
        caution_pct=float(body.get("caution_pct", 0.5)),
        warning_pct=float(body.get("warning_pct", 0.75)),
        critical_pct=float(body.get("critical_pct", 0.9)),
    )
    return {"status": "ok", "message": "Location config saved"}


# ── Scheduler endpoints ───────────────────────────────────────────────────────

@app.get("/schedule/config")
def get_schedule():
    return get_schedule_config()


@app.post("/schedule/start")
async def start_scheduled_analysis(request: Request):
    body = await request.json()
    interval = int(body.get("interval_minutes", 5))
    if interval < 1 or interval > 1440:
        return JSONResponse({"error": "Interval must be 1-1440 minutes"}, status_code=400)
    start_schedule(analyze_frame_for_camera, interval)
    return {"status": "started", "interval_minutes": interval,
            "message": f"Auto-analysis every {interval} minutes"}


@app.post("/schedule/stop")
def stop_scheduled_analysis():
    stop_schedule()
    return {"status": "stopped"}


@app.post("/schedule/run-now")
async def run_analysis_now():
    """Manually trigger one scheduled analysis immediately."""
    from backend.scheduler import run_scheduled_analysis
    await run_scheduled_analysis(analyze_frame_for_camera)
    config = get_schedule_config()
    return {"status": "ok", "result": config.get("last_result")}


# ── Dead Man's Switch endpoints ───────────────────────────────────────────────

@app.get("/deadman/status")
def deadman_status():
    return get_deadman_status()


@app.post("/deadman/enable")
async def deadman_enable(request: Request, user=Depends(require_auth)):
    body = await request.json()
    minutes = int(body.get("minutes", 10))
    if minutes < 1 or minutes > 1440:
        return JSONResponse({"error": "Minutes must be 1-1440"}, status_code=400)

    def alert_cb(elapsed):
        try:
            send_danger_alert(
                int(0), float(0), "WARNING",
                f"CDMS offline: no analysis for {elapsed:.0f} seconds. System may be down."
            )
        except Exception as e:
            print(f"☠️  Dead man's email error: {e}")

    enable_deadman(minutes * 60, alert_cb)
    return {"status": "enabled", "minutes": minutes}


@app.post("/deadman/disable")
def deadman_disable():
    disable_deadman()
    return {"status": "disabled"}


# ── Analytics endpoints ───────────────────────────────────────────────────────

@app.get("/analytics/weekly")
async def analytics_weekly():
    """Week-over-week comparison using Supabase cloud data, falling back to local SQLite."""
    try:
        from backend.supabase_sync import get_client
        from datetime import datetime, timedelta, timezone
        import sqlite3

        now       = datetime.now(timezone.utc)
        week_ago  = now - timedelta(days=7)
        two_weeks = now - timedelta(days=14)

        def parse_ts(ts):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))

        def _stats(rows):
            if not rows:
                return {"avg": 0, "peak": 0, "total": 0, "alerts": 0, "alert_rate": 0}
            counts = [r["person_count"] for r in rows if r.get("person_count") is not None]
            alerts = sum(1 for r in rows if r.get("risk_level") in ("WARNING", "DANGER", "OVERCROWDED"))
            return {
                "avg":        round(sum(counts) / len(counts), 1) if counts else 0,
                "peak":       max(counts) if counts else 0,
                "total":      len(rows),
                "alerts":     alerts,
                "alert_rate": round(alerts / len(rows) * 100, 1) if rows else 0,
            }

        # Try Supabase first
        client = get_client()
        if client:
            result = client.table("detections").select(
                "person_count,timestamp,risk_level"
            ).order("timestamp", desc=True).limit(500).execute()
            rows = result.data or []
            this_week = [r for r in rows if parse_ts(r["timestamp"]) >= week_ago]
            last_week = [r for r in rows if two_weeks <= parse_ts(r["timestamp"]) < week_ago]
        else:
            # Fallback to local SQLite
            conn = sqlite3.connect("logs/cdms.db")
            conn.row_factory = sqlite3.Row
            cur  = conn.cursor()
            cur.execute(
                "SELECT person_count, risk_level, timestamp FROM detections "
                "WHERE timestamp >= ? ORDER BY timestamp",
                (two_weeks.isoformat(),)
            )
            all_rows  = [dict(r) for r in cur.fetchall()]
            conn.close()
            this_week = [r for r in all_rows if parse_ts(r["timestamp"]) >= week_ago]
            last_week = [r for r in all_rows if parse_ts(r["timestamp"]) < week_ago]

        tw = _stats(this_week)
        lw = _stats(last_week)
        return {
            "this_week": tw,
            "last_week": lw,
            "delta": {
                "avg_change":   round(tw["avg"]  - lw["avg"],  1),
                "peak_change":  round(tw["peak"] - lw["peak"], 1),
                "trend":        "up" if tw["avg"] > lw["avg"] else "down" if tw["avg"] < lw["avg"] else "stable",
                "alert_change": tw["alerts"] - lw["alerts"],
            },
            "source": "supabase" if client else "local",
        }
    except Exception as e:
        return {"error": str(e), "this_week": {}, "last_week": {}, "delta": {}}


# ── Anomaly endpoints ─────────────────────────────────────────────────────────

@app.post("/anomaly/setup")
def setup_anomaly_table():
    """Ensure the Supabase anomalies table is reachable."""
    return _setup_anomalies_table()


@app.get("/anomaly/recent")
def anomaly_recent(limit: int = 10):
    """Return the most recent anomalies."""
    return {"anomalies": get_recent_anomalies(limit=limit)}


@app.get("/anomaly/history")
def anomaly_history():
    """Return anomaly stats + recent list."""
    return {
        "stats":   get_anomaly_stats(),
        "recent":  get_recent_anomalies(limit=20),
        "flow":    get_crowd_flow_state(),
    }


# ── SMS endpoints ────────────────────────────────────────────────────────────

@app.get("/sms/status")
def sms_status():
    return get_sms_status()

@app.post("/sms/test")
async def test_sms(user=Depends(require_auth)):
    """Send a test SMS to verify configuration."""
    result = send_sms_alert(
        person_count=0,
        risk_level="WARNING",
        message="CDMS test alert — system is configured correctly",
        location="Test"
    )
    return result

@app.post("/sms/configure")
async def configure_sms(request: Request, admin=Depends(require_admin)):
    """Update SMS configuration in .env file."""
    body = await request.json()
    env_path = ".env"
    try:
        with open(env_path, "r") as f:
            lines = f.readlines()
        keys = ["TWILIO_SID", "TWILIO_TOKEN", "TWILIO_FROM", "TWILIO_TO"]
        new_lines = [l for l in lines if not any(l.startswith(k) for k in keys)]
        for key in keys:
            val = body.get(key)
            if val:
                new_lines.append(f"{key}={val}\n")
        with open(env_path, "w") as f:
            f.writelines(new_lines)
        return {"status": "ok", "message": "SMS config saved — restart server to apply"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Auth endpoints ────────────────────────────────────────────────────────────

@app.post("/auth/login")
async def auth_login(request: Request):
    body = await request.json()
    email    = body.get("email", "")
    password = body.get("password", "")
    if not email or not password:
        return JSONResponse({"error": "Email and password required"}, status_code=400)
    result = login(email, password)
    if not result:
        return JSONResponse({"error": "Invalid email or password"}, status_code=401)
    return result


@app.get("/auth/me")
def auth_me(user = Depends(require_auth)):
    profile = get_user_by_id(user["user_id"])
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return {k: v for k, v in profile.items() if k != "password_hash"}


@app.post("/auth/register")
async def auth_register(request: Request, admin = Depends(require_admin)):
    """Admin-only: create new user."""
    body = await request.json()
    try:
        user = create_user(
            email=body.get("email"),
            password=body.get("password", "changeme123"),
            name=body.get("name", "New User"),
            role=body.get("role", "operator"),
        )
        return {k: v for k, v in user.items() if k != "password_hash"}
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/auth/users")
def list_users(admin = Depends(require_admin)):
    return {"users": get_all_users()}


@app.put("/auth/users/{user_id}/role")
async def change_user_role(user_id: int, request: Request, admin = Depends(require_admin)):
    body = await request.json()
    role = body.get("role")
    if role not in ("admin", "operator", "viewer"):
        return JSONResponse({"error": "Invalid role"}, status_code=400)
    update_user_role(user_id, role)
    return {"status": "ok", "user_id": user_id, "new_role": role}


@app.delete("/auth/users/{user_id}")
def remove_user(user_id: int, admin = Depends(require_admin)):
    deactivate_user(user_id)
    return {"status": "ok"}


@app.post("/auth/change-password")
async def change_password(request: Request, user = Depends(require_auth)):
    body = await request.json()
    old_pw = body.get("old_password", "")
    new_pw = body.get("new_password", "")
    if not old_pw or not new_pw or len(new_pw) < 6:
        return JSONResponse({"error": "Invalid password"}, status_code=400)
    from backend.auth import get_user_by_id as _get_user, verify_password, hash_password, get_db as _get_db
    profile = _get_user(user["user_id"])
    if not verify_password(old_pw, profile["password_hash"]):
        return JSONResponse({"error": "Current password incorrect"}, status_code=401)
    conn = _get_db()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                 (hash_password(new_pw), user["user_id"]))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Password changed"}

@app.get("/{path:path}")
async def serve_spa(path: str):
    # Don't intercept API routes
    api_prefixes = ("stats", "system", "history", "incidents", "alerts",
        "calibration", "feedback", "zones", "location", "schedule", "thresholds",
        "analyze", "session", "cloud", "anomaly", "deadman", "sms", "analytics",
        "auth", "camera", "ngrok", "ws", "mobile", "static", "assets", "reports", "logs")
    if path.split("/")[0] in api_prefixes:
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    dist_file = f"frontend-react/dist/{path}"
    if os.path.exists(dist_file) and os.path.isfile(dist_file):
        return FileResponse(dist_file)
    return FileResponse("frontend-react/dist/index.html")
