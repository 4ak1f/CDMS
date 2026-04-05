from backend.flow_detection import CrowdFlowDetector
from backend.report_generator import generate_incident_report
from backend.email_alerts import send_danger_alert
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
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
    archive_old_detections, save_zone_config, get_zone_config)
import cv2
import numpy as np
import base64
import os
import asyncio
import time
from backend.database import init_db, log_detection, get_all_detections, get_thresholds, save_thresholds, store_feedback, get_feedback_stats, get_all_feedback
from backend.calibration import get_smart_scale
app = FastAPI(title="CDMS - Crowd Disaster Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/mobile", StaticFiles(directory="pwa"), name="pwa")

init_db()
print("🚀 Loading crowd counting model...")
crowd_model, model_device = load_model()
from backend.model_ensemble import CrowdEnsemble
ensemble = CrowdEnsemble(crowd_model, model_device)
flow_detector = CrowdFlowDetector()
print("✅ System ready!")


def process_frame(frame, crowd_mode="auto"):
    """
    Full processing pipeline for a single frame.
    Returns: annotated_frame, density_result, zones, alert, flow_result, confidence
    """
    frame_start = time.time()
    h, w = frame.shape[:2]

    # Step 1: Primary engine — custom trained model
    density_map, model_count, confidence = generate_density_map(crowd_model, model_device, frame)

    # Step 2: YOLO detection
    _, yolo_count, detections = detect_people(frame)

        # Step 3: Ensemble prediction
    ensemble_result = ensemble.predict(
            frame, yolo_count, model_count, confidence, crowd_mode
        )
    final_count = ensemble_result["count"]

        # Step 4: Heatmap + zones (must happen before drawing boxes)
    heatmap = generate_heatmap(density_map, frame.shape)
    heatmap_frame = overlay_heatmap(frame, heatmap, alpha=0.45)
    zones = analyze_zones(density_map, frame.shape, grid_rows=3, grid_cols=3)
    annotated_frame = draw_zones(heatmap_frame, zones)

        # Step 5: Crowd flow detection
    flow_result, annotated_frame = flow_detector.detect_flow(annotated_frame)

        # Step 6: Draw bounding boxes for sparse crowds
    if ensemble_result["method"].startswith("YOLO"):
            for det in detections:
                x1, y1, x2, y2 = det["bbox"]
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(annotated_frame, f"{det['confidence']:.0%}",
                        (x1, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
    # Step 7: Risk classification with thresholds
    thresholds    = get_thresholds()
    danger_label  = thresholds["danger_label"]
    warning_label = thresholds["warning_label"]
    density_result = estimate_density(int(final_count), w, h, thresholds)

    # Override if surge detected
    if flow_result.get("surge_detected"):
        density_result["risk_level"] = danger_label
        density_result["color"]      = "red"
        density_result["message"]    = f"ALERT: {danger_label} — Surge detected!"

    # Step 8: Draw info overlay
    risk = density_result["risk_level"]
    risk_colors_cv = {
        "SAFE": (0, 255, 0),
        "WARNING": (0, 165, 255),
        "DANGER": (0, 0, 255),
        "OVERCROWDED": (0, 0, 255)
    }
    color = risk_colors_cv.get(risk, (255, 255, 255))
    cv2.rectangle(annotated_frame, (0, 0), (w, 55), (0, 0, 0), -1)
    cv2.putText(annotated_frame, f"People: {int(final_count)} [{ensemble_result['method']}]",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(annotated_frame, f"Risk: {risk}", (10, 48),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    cv2.putText(annotated_frame, f"Flow: {flow_result['direction']}", (w - 220, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
    cv2.putText(annotated_frame, f"Speed: {flow_result['speed']}", (w - 220, 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # Step 9: Alert, log, report, email
    alert = generate_alert(density_result)
    log_detection(
        int(final_count),
        density_result["density_score"],
        density_result["risk_level"],
        density_result["message"]
    )
    # Log incidents separately for WARNING/DANGER only
    if risk in ["WARNING", "DANGER", "OVERCROWDED"]:
        log_incident(int(final_count), density_result["density_score"],
                    risk, density_result["message"], zones)
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
    inference_ms = round((time.time() - frame_start) * 1000)
    return annotated_frame, density_result, zones, alert, flow_result, confidence, inference_ms


@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    with open("frontend/index.html", "r") as f:
        return f.read()


@app.post("/analyze/image")
async def analyze_image(file: UploadFile = File(...), mode: str = "auto"):
    contents = await file.read()
    np_arr   = np.frombuffer(contents, np.uint8)
    frame    = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if frame is None:
        return JSONResponse({"error": "Invalid image file"}, status_code=400)

    annotated_frame, density_result, zones, alert, flow_result, confidence, inference_ms = process_frame(frame, mode)

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
        "alert":           alert,
        "inference_ms":    inference_ms,
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
    
    counts     = [r["person_count"] for r in frame_results]
    scores     = [r["density_score"] for r in frame_results]
    risk_levels = [r["risk_level"] for r in frame_results]

    overall_risk = "SAFE"
    if any(r in ["DANGER", "OVERCROWDED"] for r in risk_levels):
        overall_risk = "OVERCROWDED"
    elif "WARNING" in risk_levels:
        overall_risk = "WARNING"

    return {
        "frames_analyzed":  len(frame_results),
        "avg_person_count": round(sum(counts) / len(counts), 1),
        "max_person_count": max(counts),
        "avg_density_score": round(sum(scores) / len(scores), 4),
        "max_density_score": round(max(scores), 4),
        "overall_risk":     overall_risk,
        "danger_frames":    sum(1 for r in risk_levels if r in ["DANGER", "OVERCROWDED"]),
        "warning_frames":   risk_levels.count("WARNING"),
        "safe_frames":      risk_levels.count("SAFE")
    }


@app.websocket("/ws/webcam")
async def webcam_stream(websocket: WebSocket):
    await websocket.accept()
    print("📹 Webcam stream connected")
    try:
        while True:
            import json
            data       = await websocket.receive_text()
            payload    = json.loads(data)
            img_data   = base64.b64decode(payload["frame"])
            crowd_mode = payload.get("mode", "auto")
            np_arr     = np.frombuffer(img_data, np.uint8)
            frame      = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            annotated_frame, density_result, zones, alert, flow_result, confidence, inference_ms = process_frame(frame, crowd_mode)

            _, buffer  = cv2.imencode(".jpg", annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            result_b64 = base64.b64encode(buffer).decode("utf-8")

            await websocket.send_json({
                "frame":          result_b64,
                "person_count":   density_result["person_count"],
                "density_score":  density_result["density_score"],
                "risk_level":     density_result["risk_level"],
                "message":        density_result["message"],
                "confidence_min": confidence[0],
                "confidence_max": confidence[1],
                "alert":          alert is not None,
                "inference_ms":   inference_ms,
                "zones": [{
                    "zone":  z["zone"],
                    "count": z["count"],
                    "risk":  z["risk"]
                } for z in zones]
            })

    except WebSocketDisconnect:
        print("📹 Webcam stream disconnected")


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
    body = await request.json()
    predicted = int(body.get("predicted_count", 0))
    actual    = int(body.get("actual_count", 0))
    scene     = body.get("scene_type", "unknown")

    if actual < 0:
        return JSONResponse({"error": "Invalid count"}, status_code=400)

    store_feedback(predicted, actual, scene)

    return {
        "message": "Feedback stored successfully",
        "predicted": predicted,
        "actual": actual,
        "correction_ratio": round(actual / max(predicted, 1), 2),
        "impact": "Model will use this for future calibration"
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
    """Returns calibration statistics per scene type."""
    stats = get_feedback_stats()
    return {
        "scene_calibrations": stats,
        "total_feedback_samples": sum(
            v["sample_count"] for v in stats.values()
        )
    }
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


@app.get("/system/stats")
def get_system_stats():
    import psutil
    return {
        "cpu_percent":    psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "memory_used_gb": round(psutil.virtual_memory().used / (1024**3), 1),
        "uptime_seconds": round(time.time() - psutil.boot_time()),
    }