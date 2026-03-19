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
import cv2
import numpy as np
import base64
import os
import asyncio

app = FastAPI(title="CDMS - Crowd Disaster Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend files
app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/mobile", StaticFiles(directory="pwa"), name="pwa")

# Initialize database and load model on startup
init_db()
print("🚀 Loading crowd counting model...")
crowd_model, model_device = load_model()
flow_detector = CrowdFlowDetector()
print("✅ System ready!")


def process_frame(frame):
    """
    Full pipeline for a single frame:
    1. Trained model → density map + count
    2. Heatmap overlay
    3. Zone analysis
    4. Crowd flow detection
    5. YOLO fallback
    6. Risk classification
    7. Alert + PDF report + email if DANGER
    """
    h, w = frame.shape[:2]

    # Step 1: Primary engine
    density_map, model_count = generate_density_map(crowd_model, model_device, frame)

# Step 2: YOLO detection
    _, yolo_count, _ = detect_people(frame)

# Smart switching logic:
# - For sparse crowds (< 20 people): trust YOLO more
# - For dense crowds (20+ people): trust density model more
    if yolo_count <= 20:
    # YOLO is more reliable for sparse scenes
        final_count = float(yolo_count)
    elif yolo_count > 20 and model_count > yolo_count:
    # Dense crowd — use density model
        final_count = model_count
    else:
    # Use average of both
        final_count = (model_count + float(yolo_count)) / 2
    # Step 3: Heatmap
    heatmap = generate_heatmap(density_map, frame.shape)
    heatmap_frame = overlay_heatmap(frame, heatmap, alpha=0.45)

    # Step 4: Zone analysis
    zones = analyze_zones(density_map, frame.shape, grid_rows=3, grid_cols=3)
    annotated_frame = draw_zones(heatmap_frame, zones)

    # Step 5: Crowd flow detection
    flow_result, annotated_frame = flow_detector.detect_flow(annotated_frame)

    # Step 6: Risk classification
    thresholds = get_thresholds()
    danger_label = thresholds["danger_label"]
    warning_label = thresholds["warning_label"]
    density_result = estimate_density(int(final_count), w, h, thresholds)

    zone_risks = [z["risk"] for z in zones]
    if flow_result.get("surge_detected"):
        density_result["risk_level"] = danger_label
        density_result["color"] = "red"
        density_result["message"] = f"ALERT: {danger_label} — Surge detected!"
    # Step 7: Draw info overlay
    risk = density_result["risk_level"]
    risk_colors_cv = {"SAFE": (0,255,0), "WARNING": (0,165,255), "DANGER": (0,0,255), "OVERCROWDED": (0,0,255)}
    color = risk_colors_cv.get(risk, (255,255,255))
    cv2.rectangle(annotated_frame, (0, 0), (w, 55), (0,0,0), -1)
    cv2.putText(annotated_frame, f"People: {int(final_count)}", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
    cv2.putText(annotated_frame, f"Risk: {risk}", (10, 48),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    cv2.putText(annotated_frame, f"Flow: {flow_result['direction']}", (w-220, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200,200,200), 1)
    cv2.putText(annotated_frame, f"Speed: {flow_result['speed']}", (w-220, 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1)

    # Step 8: Alert, log, report, email
    alert = generate_alert(density_result)
    log_detection(
        int(final_count),
        density_result["density_score"],
        density_result["risk_level"],
        density_result["message"]
    )

    # Generate PDF + send email only for DANGER
    report_path = None
    if risk == "DANGER":
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

    return annotated_frame, density_result, zones, alert, flow_result


@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    with open("frontend/index.html", "r") as f:
        return f.read()


@app.post("/analyze/image")
async def analyze_image(file: UploadFile = File(...)):
    contents = await file.read()
    np_arr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if frame is None:
        return JSONResponse({"error": "Invalid image file"}, status_code=400)

    annotated_frame, density_result, zones, alert, flow_result = process_frame(frame)

    # Encode annotated frame
    _, buffer = cv2.imencode(".jpg", annotated_frame)
    img_base64 = base64.b64encode(buffer).decode("utf-8")

    return {
        "person_count": density_result["person_count"],
        "density_score": density_result["density_score"],
        "risk_level": density_result["risk_level"],
        "color": density_result["color"],
        "message": density_result["message"],
        "alert": alert,
        "zones": [{
            "zone": z["zone"],
            "count": z["count"],
            "risk": z["risk"],
            "density": z["density"]
        } for z in zones],
        "annotated_image": img_base64
    }


@app.post("/analyze/video")
async def analyze_video(file: UploadFile = File(...)):
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
    frame_num = 0
    max_frames = 20

    while cap.isOpened() and len(frame_results) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        frame_num += 1
        if frame_num % 10 != 0:
            continue

        _, density_result, zones, _, _ = process_frame(frame)
        frame_results.append(density_result)

    cap.release()

    if not frame_results:
        return JSONResponse({"error": "Could not process video"}, status_code=400)

    counts = [r["person_count"] for r in frame_results]
    scores = [r["density_score"] for r in frame_results]
    risk_levels = [r["risk_level"] for r in frame_results]

    overall_risk = "SAFE"
    if "DANGER" in risk_levels:
        overall_risk = "DANGER"
    elif "WARNING" in risk_levels:
        overall_risk = "WARNING"

    return {
        "frames_analyzed": len(frame_results),
        "avg_person_count": round(sum(counts) / len(counts), 1),
        "max_person_count": max(counts),
        "avg_density_score": round(sum(scores) / len(scores), 4),
        "max_density_score": round(max(scores), 4),
        "overall_risk": overall_risk,
        "danger_frames": risk_levels.count("DANGER"),
        "warning_frames": risk_levels.count("WARNING"),
        "safe_frames": risk_levels.count("SAFE")
    }


@app.websocket("/ws/webcam")
async def webcam_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time webcam processing.
    Client sends frames, server responds with analysis results.
    """
    await websocket.accept()
    print("📹 Webcam stream connected")

    try:
        while True:
            # Receive frame from client as base64
            data = await websocket.receive_text()
            import json
            payload = json.loads(data)
            img_data = base64.b64decode(payload["frame"])
            np_arr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            annotated_frame, density_result, zones, alert, flow_result = process_frame(frame)       

            # Encode result frame
            _, buffer = cv2.imencode(".jpg", annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            result_b64 = base64.b64encode(buffer).decode("utf-8")

            await websocket.send_json({
                "frame": result_b64,
                "person_count": density_result["person_count"],
                "density_score": density_result["density_score"],
                "risk_level": density_result["risk_level"],
                "message": density_result["message"],
                "alert": alert is not None,
                "zones": [{
                    "zone": z["zone"],
                    "count": z["count"],
                    "risk": z["risk"]
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
    """Returns summary statistics for the dashboard charts."""
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
        risk_dist[d["risk_level"]] = risk_dist.get(d["risk_level"], 0) + 1

    recent = detections[:20]
    return {
        "total_detections": len(detections),
        "total_alerts": risk_dist["WARNING"] + risk_dist["DANGER"],
        "avg_crowd": round(sum(d["person_count"] for d in detections) / len(detections), 1),
        "peak_crowd": max(d["person_count"] for d in detections),
        "risk_distribution": risk_dist,
        "recent_counts": [d["person_count"] for d in reversed(recent)],
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
    """Returns current threshold settings."""
    return get_thresholds()


@app.post("/thresholds")
async def update_thresholds(request: Request):
    """Updates threshold settings."""
    from fastapi import Request
    body = await request.json()
    warning = float(body.get("warning_threshold", 2.0))
    danger  = float(body.get("danger_threshold",  5.0))

    if warning <= 0 or danger <= 0 or warning >= danger:
        return JSONResponse(
            {"error": "Invalid thresholds. Warning must be less than danger and both must be positive."},
            status_code=400
        )

    save_thresholds(warning, danger)
    return {"message": "Thresholds updated successfully", "warning": warning, "danger": danger}