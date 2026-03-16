from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.detector import detect_people
from backend.density import estimate_density
from backend.alerts import generate_alert, get_recent_alerts
from backend.database import init_db, log_detection, get_all_detections
import cv2
import numpy as np
import os
import io

app = FastAPI(title="CDMS - Crowd Disaster Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Initialize database on startup
init_db()

@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    """Serves the main dashboard HTML page."""
    with open("frontend/index.html", "r") as f:
        return f.read()

@app.post("/analyze/image")
async def analyze_image(file: UploadFile = File(...)):
    """
    Accepts an uploaded image, runs detection,
    returns count, density, and risk level.
    """
    contents = await file.read()
    np_arr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if frame is None:
        return JSONResponse({"error": "Invalid image file"}, status_code=400)

    h, w = frame.shape[:2]
    annotated_frame, person_count, detections = detect_people(frame)

    # If YOLO detects very few people but image is complex,
    # fall back to visual density estimation for dense crowds
    if person_count < 5:
        from backend.density import estimate_density_from_frame
        visual_result = estimate_density_from_frame(frame)
        # Use whichever method gives higher risk
        if visual_result["risk_level"] in ["WARNING", "DANGER"]:
            density_result = visual_result
        else:
            density_result = estimate_density(person_count, w, h)
    else:
        density_result = estimate_density(person_count, w, h)
    log_detection(
        person_count,
        density_result["density_score"],
        density_result["risk_level"],
        density_result["message"]
    )

    # Encode annotated frame as JPEG to send back
    _, buffer = cv2.imencode(".jpg", annotated_frame)
    img_base64 = __import__("base64").b64encode(buffer).decode("utf-8")

    return {
        "person_count": person_count,
        "density_score": density_result["density_score"],
        "risk_level": density_result["risk_level"],
        "color": density_result["color"],
        "message": density_result["message"],
        "alert": alert,
        "annotated_image": img_base64
    }

@app.post("/analyze/video")
async def analyze_video(file: UploadFile = File(...)):
    """
    Accepts an uploaded video, processes every 10th frame,
    returns overall crowd analysis summary.
    """
    os.makedirs("uploads", exist_ok=True)
    video_path = f"uploads/{file.filename}"

    with open(video_path, "wb") as f:
        f.write(await file.read())

    cap = cv2.VideoCapture(video_path)
    frame_results = []
    frame_num = 0
    max_frames = 100  # Cap at 100 sampled frames for speed

    while cap.isOpened() and len(frame_results) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        frame_num += 1
        if frame_num % 10 != 0:  # Process every 10th frame
            continue

        h, w = frame.shape[:2]
        _, person_count, _ = detect_people(frame)
        density_result = estimate_density(person_count, w, h)
        alert = generate_alert(density_result)
        log_detection(
            person_count,
            density_result["density_score"],
            density_result["risk_level"],
            density_result["message"]
        )
        frame_results.append(density_result)

    cap.release()

    if not frame_results:
        return JSONResponse({"error": "Could not process video"}, status_code=400)

    # Summarize results
    counts = [r["person_count"] for r in frame_results]
    scores = [r["density_score"] for r in frame_results]
    risk_levels = [r["risk_level"] for r in frame_results]

    danger_count = risk_levels.count("DANGER")
    warning_count = risk_levels.count("WARNING")

    overall_risk = "SAFE"
    if danger_count > 0:
        overall_risk = "DANGER"
    elif warning_count > 0:
        overall_risk = "WARNING"

    return {
        "frames_analyzed": len(frame_results),
        "avg_person_count": round(sum(counts) / len(counts), 1),
        "max_person_count": max(counts),
        "avg_density_score": round(sum(scores) / len(scores), 4),
        "max_density_score": round(max(scores), 4),
        "overall_risk": overall_risk,
        "danger_frames": danger_count,
        "warning_frames": warning_count,
        "safe_frames": risk_levels.count("SAFE")
    }

@app.get("/history")
def get_history():
    """Returns the last 50 detection records from the database."""
    return get_all_detections(limit=50)

@app.get("/alerts")
def get_alerts():
    """Returns recent alerts from the log file."""
    return {"alerts": get_recent_alerts(limit=20)}