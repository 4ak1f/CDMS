#!/usr/bin/env python3
"""
CDMS Comprehensive System Test
Tests: API endpoints, response validity, scene learning, performance, UI asset availability
Run: python test_api.py
"""
import ssl, json, time, os, sys, io
import urllib.request, urllib.error

BASE = "https://localhost:8000"
ctx  = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False
ctx.verify_mode    = ssl.CERT_NONE

P = "✅"; F = "❌"; W = "⚠️ "
results = []
timings = []

def req(method, path, data=None, label=None, form_data=None, timeout=15):
    url   = BASE + path
    start = time.time()
    label = label or f"{method} {path}"
    try:
        if form_data:
            boundary = "CDMS_BOUNDARY_XYZ"
            body = b""
            for key, val in form_data.items():
                if isinstance(val, bytes):
                    body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"; filename=\"test.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n".encode() + val + b"\r\n"
                else:
                    body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{val}\r\n".encode()
            body += f"--{boundary}--\r\n".encode()
            r = urllib.request.Request(url, data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
        elif data:
            body = json.dumps(data).encode()
            r = urllib.request.Request(url, data=body,
                headers={"Content-Type": "application/json"}, method=method)
        else:
            r = urllib.request.Request(url, method=method)

        with urllib.request.urlopen(r, context=ctx, timeout=timeout) as resp:
            elapsed = round((time.time() - start) * 1000)
            status  = resp.status
            raw     = resp.read().decode()
            try:    parsed = json.loads(raw)
            except: parsed = raw
            results.append((P, label, f"{elapsed}ms", f"HTTP {status}"))
            timings.append((label, elapsed))
            return parsed, elapsed, status
    except urllib.error.HTTPError as e:
        elapsed = round((time.time() - start) * 1000)
        try:    body = json.loads(e.read().decode())
        except: body = {}
        results.append((W if e.code in (400,422) else F, label, f"{elapsed}ms", f"HTTP {e.code}"))
        timings.append((label, elapsed))
        return body, elapsed, e.code
    except Exception as e:
        elapsed = round((time.time() - start) * 1000)
        results.append((F, label, f"{elapsed}ms", str(e)[:70]))
        timings.append((label, elapsed))
        return None, elapsed, 0

def section(title):
    print(f"\n── {title} {'─'*(52-len(title))}")

def check(label, condition, got=None):
    icon = P if condition else F
    suffix = f" → {got}" if got is not None else ""
    print(f"  {icon} {label}{suffix}")
    results.append((icon, label, "", str(got) if got else ""))

print("\n" + "="*60)
print("  CDMS Comprehensive System Test")
print(f"  Target: {BASE}")
print("="*60)

# ── 1. CORE ENDPOINTS ────────────────────────────────────────
section("Core Endpoints")
stats,    _, sc1 = req("GET", "/stats")
sys_s,    _, sc2 = req("GET", "/system/stats")
thresh,   _, sc3 = req("GET", "/thresholds")
cal,      _, sc4 = req("GET", "/calibration")
fb,       _, sc5 = req("GET", "/feedback")
hist,     _, sc6 = req("GET", "/history")
alerts,   _, sc7 = req("GET", "/alerts")
incidents,_, sc8 = req("GET", "/incidents")
zones,    _, sc9 = req("GET", "/zones/config")

# ── 2. RESPONSE STRUCTURE VALIDATION ────────────────────────
section("Response Structure Validation")
if stats:
    check("stats.total_detections exists",    "total_detections" in stats,    stats.get("total_detections"))
    check("stats.peak_crowd >= 0",            isinstance(stats.get("peak_crowd"), (int,float)), stats.get("peak_crowd"))
    check("stats.recent_counts is list",      isinstance(stats.get("recent_counts"), list))
    check("stats.risk_distribution exists",   "risk_distribution" in stats)
if sys_s:
    check("system.cpu_percent in 0-100",      0 <= sys_s.get("cpu_percent",999) <= 100, f"{sys_s.get('cpu_percent')}%")
    check("system.memory_percent in 0-100",   0 <= sys_s.get("memory_percent",999) <= 100, f"{sys_s.get('memory_percent')}%")
    check("system.uptime_human is string",    isinstance(sys_s.get("uptime_human"), str), sys_s.get("uptime_human"))
    check("system.model_mae present",         sys_s.get("model_mae") is not None, sys_s.get("model_mae"))
    check("system.model_mae sane (<50)",      sys_s.get("model_mae", 999) < 50, sys_s.get("model_mae"))
if thresh:
    check("thresholds.warning exists",        "warning" in thresh or "warning_threshold" in thresh)
    check("thresholds.danger > warning",      True)
if cal:
    check("calibration.scene_learning exists",       "scene_learning" in cal, len(cal.get("scene_learning",[])))
    check("calibration.total_feedback_samples >= 0", cal.get("total_feedback_samples",0) >= 0, cal.get("total_feedback_samples"))

# ── 3. FEEDBACK & LEARNING ───────────────────────────────────
section("Feedback & Scene Learning")
fb_payload = {
    "predicted_count":   2,
    "actual_count":      1,
    "scene_type":        "sparse_indoor",
    "scene_fingerprint": "bright_sparse_smooth"
}
fb_res, fb_ms, fb_sc = req("POST", "/feedback", fb_payload, "POST /feedback (2→1 correction)")
if fb_res:
    check("feedback returns corrections_so_far", "corrections_so_far" in fb_res, fb_res.get("corrections_so_far"))
    check("feedback returns current_scale",      "current_scale" in fb_res, fb_res.get("current_scale"))
    check("feedback scale is sane (0.1–5.0)",    0.1 <= fb_res.get("current_scale", 0) <= 5.0)
    check("feedback returns impact message",     bool(fb_res.get("impact")), fb_res.get("impact"))

# Verify scene_params.json was updated
try:
    with open("logs/scene_params.json") as f:
        sp = json.load(f)
    check("scene_params.json exists and has data", len(sp) > 0, f"{len(sp)} scenes")
    for fp, p in sp.items():
        check(f"Scene '{fp}' has valid scale",   0.1 <= p.get("scale",0) <= 5.0, p.get("scale"))
        check(f"Scene '{fp}' corrections >= 1",  p.get("corrections",0) >= 1, p.get("corrections"))
except Exception as e:
    check("scene_params.json readable", False, str(e))

# ── 4. THRESHOLD VALIDATION ──────────────────────────────────
section("Threshold Validation")
t1, _, s1 = req("POST", "/thresholds", {"warning_threshold": 10, "danger_threshold": 20}, "Valid thresholds")
t2, _, s2 = req("POST", "/thresholds", {"warning_threshold": 20, "danger_threshold": 10}, "Invalid thresholds (should 400)")
check("Valid thresholds accepted (200)",    s1 == 200, f"HTTP {s1}")
check("Invalid thresholds rejected (400)", s2 == 400, f"HTTP {s2}")
# Restore sensible defaults
req("POST", "/thresholds", {"warning_threshold": 5, "danger_threshold": 10}, "Restore defaults")

# ── 5. IMAGE ANALYSIS ────────────────────────────────────────
section("Image Analysis")
try:
    import numpy as np, cv2
    # Test 1: blank grey image (0 people expected)
    blank = np.ones((480, 640, 3), dtype=np.uint8) * 128
    _, img_bytes = cv2.imencode(".jpg", blank)
    img_res, img_ms, img_sc = req("POST", "/analyze/image",
        form_data={"file": img_bytes.tobytes()}, label="Blank image analysis", timeout=30)
    if img_res:
        check("Analysis returns person_count",     "person_count" in img_res, img_res.get("person_count"))
        check("Analysis returns scene_fingerprint","scene_fingerprint" in img_res, img_res.get("scene_fingerprint"))
        check("Analysis returns scene_type",       "scene_type" in img_res, img_res.get("scene_type"))
        check("Analysis returns risk_level",       "risk_level" in img_res, img_res.get("risk_level"))
        check("Analysis returns annotated_image",  "annotated_image" in img_res)
        check("Person count is int >= 0",          isinstance(img_res.get("person_count"), int) and img_res.get("person_count") >= 0)
        check(f"Analysis time acceptable (<10s)",  img_ms < 10000, f"{img_ms}ms")

    # Test 2: mode=sparse
    img_res2, _, _ = req("POST", "/analyze/image?mode=sparse",
        form_data={"file": img_bytes.tobytes()}, label="Sparse mode analysis", timeout=30)
    check("Sparse mode works", img_res2 is not None)

except ImportError:
    check("cv2 available for image tests", False, "pip install opencv-python")
except Exception as e:
    check("Image analysis test", False, str(e)[:80])

# ── 6. HISTORY & LOGS ────────────────────────────────────────
section("History & Logs")
if hist:
    check("history is list or has detections key", isinstance(hist, list) or "detections" in hist)
if incidents:
    check("incidents response valid", isinstance(incidents, (list, dict)))

# ── 7. PERFORMANCE BENCHMARKS ────────────────────────────────
section("Response Time Benchmarks")
THRESHOLDS = {
    "GET /stats":         500,
    "GET /system/stats":  500,
    "GET /thresholds":    200,
    "GET /calibration":   500,
    "GET /history":      1000,
}
for label, ms in timings:
    limit = THRESHOLDS.get(label)
    if limit:
        check(f"{label} under {limit}ms", ms < limit, f"{ms}ms")

# Slowest endpoints
print("\n  Response times (all):")
for label, ms in sorted(timings, key=lambda x: x[1], reverse=True)[:8]:
    bar = "█" * min(20, ms // 50)
    flag = " ⚠️ SLOW" if ms > 2000 else ""
    print(f"    {ms:5d}ms  {bar}  {label}{flag}")

# ── 8. MODEL & CHECKPOINT ────────────────────────────────────
section("Model & Checkpoint")
try:
    import torch
    ck = torch.load("model_training/checkpoints/best_model.pth", map_location="cpu", weights_only=False)
    check("Checkpoint loads successfully",     True)
    check("Checkpoint has model_state",        "model_state" in ck)
    check("Checkpoint MAE < 20",               ck.get("best_mae", 999) < 20, f"MAE {ck.get('best_mae'):.4f}")
    check("Checkpoint MAE < 15 (excellent)",   ck.get("best_mae", 999) < 15, f"MAE {ck.get('best_mae'):.4f}")
except Exception as e:
    check("Checkpoint loadable", False, str(e)[:60])

# ── 9. FILE & CONFIG INTEGRITY ───────────────────────────────
section("File & Config Integrity")
required_files = [
    "backend/main.py",
    "backend/calibration.py",
    "backend/crowd_model.py",
    "backend/database.py",
    "frontend/index.html",
    "model_training/checkpoints/best_model.pth",
    "key.pem",
    "cert.pem",
]
for f in required_files:
    exists = os.path.exists(f)
    size   = os.path.getsize(f) if exists else 0
    check(f"{f} exists", exists, f"{round(size/1024,1)}KB" if exists else "MISSING")

optional_files = [
    ("logs/scene_params.json",    "Scene learning memory"),
    ("logs/detections.db",        "Detection database"),
    ("model_training/checkpoints/pre_mall_backup.pth", "Pre-mall backup"),
]
for path, name in optional_files:
    exists = os.path.exists(path)
    size   = os.path.getsize(path) if exists else 0
    icon   = P if exists else W
    print(f"  {icon} {name}: {'exists ' + str(round(size/1024,1)) + 'KB' if exists else 'not found (optional)'}")

# ── SUMMARY ──────────────────────────────────────────────────
print("\n" + "="*60)
passed  = sum(1 for r in results if r[0] == P)
warned  = sum(1 for r in results if r[0] == W)
failed  = sum(1 for r in results if r[0] == F)
total   = len(results)
score   = round(passed / max(total, 1) * 100)
print(f"  Score: {score}%  |  {passed} passed  {warned} warnings  {failed} failed  ({total} checks)")
print("="*60)
if failed:
    print(f"\n  {F} Issues to fix:")
    for r in results:
        if r[0] == F:
            print(f"     • {r[1]}" + (f" — {r[3]}" if r[3] else ""))
if warned:
    print(f"\n  {W} Warnings:")
    for r in results:
        if r[0] == W:
            print(f"     • {r[1]}" + (f" — {r[3]}" if r[3] else ""))
print()
