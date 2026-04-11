#!/usr/bin/env python3
"""
CDMS Comprehensive System Test v2
Tests every function with real requests and validates responses.
Run: python test_system.py
"""
import ssl, json, time, os, sys
import urllib.request, urllib.error
from datetime import datetime

BASE = "https://localhost:8000"
ctx  = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False
ctx.verify_mode    = ssl.CERT_NONE

PASS="✅"; FAIL="❌"; WARN="⚠️ "; INFO="ℹ️ "
results = []
token = None

def req(method, path, data=None, label=None, form_data=None, timeout=30):
    global token
    url   = BASE + path
    label = label or f"{method} {path}"
    start = time.time()
    try:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if form_data:
            boundary = "CDMS_TEST_BOUNDARY"
            body = b""
            for key, val in form_data.items():
                if isinstance(val, bytes):
                    body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"; filename=\"test.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n".encode() + val + b"\r\n"
                else:
                    body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{val}\r\n".encode()
            body += f"--{boundary}--\r\n".encode()
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
            r = urllib.request.Request(url, data=body, headers=headers, method="POST")
        elif data:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
            r = urllib.request.Request(url, data=body, headers=headers, method=method)
        else:
            r = urllib.request.Request(url, headers=headers, method=method)
        with urllib.request.urlopen(r, context=ctx, timeout=timeout) as resp:
            elapsed = round((time.time()-start)*1000)
            raw = resp.read().decode()
            parsed = json.loads(raw) if raw else {}
            results.append((PASS, label, f"{elapsed}ms", f"HTTP {resp.status}"))
            return parsed, elapsed, resp.status
    except urllib.error.HTTPError as e:
        elapsed = round((time.time()-start)*1000)
        body = {}
        try: body = json.loads(e.read().decode())
        except: pass
        icon = WARN if e.code in (400,401,403,422) else FAIL
        results.append((icon, label, f"{elapsed}ms", f"HTTP {e.code}"))
        return body, elapsed, e.code
    except Exception as e:
        elapsed = round((time.time()-start)*1000)
        results.append((FAIL, label, f"{elapsed}ms", str(e)[:60]))
        return None, elapsed, 0

def check(label, condition, value=None):
    icon = PASS if condition else FAIL
    suffix = f" → {value}" if value is not None else ""
    print(f"  {icon} {label}{suffix}")
    results.append((icon, f"  {label}", "", str(value) if value else ""))

def section(title):
    print(f"\n{'─'*55}")
    print(f"  {title}")
    print(f"{'─'*55}")

print(f"\n{'═'*55}")
print(f"  CDMS System Test v2 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"  Target: {BASE}")
print(f"{'═'*55}")

# ── AUTH ─────────────────────────────────────────────────
section("1. Authentication")
login_res, _, sc = req("POST", "/auth/login",
    {"email": "admin@cdms.local", "password": "admin123"}, "Login")
if login_res and "token" in login_res:
    token = login_res["token"]
    check("Login returns JWT token", True, "token received")
    check("Login returns user role", login_res.get("role") is not None, login_res.get("role"))
else:
    check("Login failed", False, "no token")

me_res, _, _ = req("GET", "/auth/me", label="GET /auth/me")
check("/auth/me returns user", me_res and "email" in (me_res or {}), (me_res or {}).get("email"))

users_res, _, sc = req("GET", "/auth/users", label="GET /auth/users (admin)")
check("Admin can list users", sc == 200, f"{len((users_res or {}).get('users', []))} users")

req("GET", "/auth/me", label="GET /auth/me (no token)")

# ── CORE API ─────────────────────────────────────────────
section("2. Core Endpoints")
for path in ["/stats", "/system/stats", "/thresholds", "/history",
             "/incidents", "/alerts", "/calibration", "/feedback",
             "/zones/config", "/location/config", "/schedule/config"]:
    res, ms, sc = req("GET", path)
    check(f"{path} responds", sc == 200, f"{ms}ms")

# ── SYSTEM STATS VALIDATION ───────────────────────────────
section("3. System Stats Validation")
sys_s, _, _ = req("GET", "/system/stats")
if sys_s:
    check("CPU % in range", 0 <= (sys_s.get("cpu_percent") or 0) <= 100,
          f"{sys_s.get('cpu_percent')}%")
    check("RAM % in range", 0 <= (sys_s.get("memory_percent") or 0) <= 100,
          f"{sys_s.get('memory_percent')}%")
    check("Uptime readable", bool(sys_s.get("uptime_human")), sys_s.get("uptime_human"))
    check("Model MAE present", sys_s.get("model_mae") is not None, sys_s.get("model_mae"))
    check("Model MAE < 20", (sys_s.get("model_mae") or 999) < 20, sys_s.get("model_mae"))

# ── IMAGE ANALYSIS ─────────────────────────────────────────
section("4. Image Analysis")
try:
    import numpy as np, cv2
    # Blank image
    blank = np.ones((480,640,3), dtype=np.uint8) * 100
    _, buf = cv2.imencode(".jpg", blank)
    res, ms, sc = req("POST", "/analyze/image",
        form_data={"file": buf.tobytes()}, label="Blank image analysis", timeout=30)
    check("Analysis returns 200", sc == 200, f"{ms}ms")
    if res:
        check("Returns person_count", "person_count" in res, res.get("person_count"))
        check("Returns risk_level",   "risk_level" in res,   res.get("risk_level"))
        check("Returns scene_type",   "scene_type" in res,   res.get("scene_type"))
        check("Returns fingerprint",  "scene_fingerprint" in res, res.get("scene_fingerprint"))
        check("Returns confidence",   "confidence_score" in res, res.get("confidence_score"))
        check("Returns flow_direction", "flow_direction" in res, res.get("flow_direction"))
        check("Returns anomaly field", "anomaly" in res, "present" if "anomaly" in res else "missing")
        check("Analysis < 15s",       ms < 15000, f"{ms}ms")
        check("Count is integer >= 0", isinstance(res.get("person_count"), int) and res.get("person_count", -1) >= 0)
        check("Count < 2000 (sane)",  (res.get("person_count") or 0) < 2000, res.get("person_count"))
    # Mode test
    for mode in ["sparse", "moderate", "dense"]:
        r2, ms2, _ = req("POST", f"/analyze/image?mode={mode}",
            form_data={"file": buf.tobytes()}, label=f"Mode={mode}", timeout=30)
        check(f"Mode {mode} works", r2 is not None, f"{ms2}ms")
except ImportError:
    print(f"  {WARN} cv2 not available for image tests")

# ── FEEDBACK & LEARNING ────────────────────────────────────
section("5. Feedback & Scene Learning")
fb_res, _, sc = req("POST", "/feedback", {
    "predicted_count": 5, "actual_count": 3,
    "scene_type": "sparse_indoor", "scene_fingerprint": "test_scene_abc"
}, "POST /feedback")
check("Feedback accepted", sc == 200, sc)
if fb_res:
    check("Returns corrections_so_far", "corrections_so_far" in fb_res,
          fb_res.get("corrections_so_far"))
    check("Returns current_scale",      "current_scale" in fb_res,
          fb_res.get("current_scale"))

cal_res, _, _ = req("GET", "/calibration", label="GET /calibration")
if cal_res:
    check("Has scene_learning", "scene_learning" in cal_res,
          f"{len(cal_res.get('scene_learning', []))} scenes")
    check("Has converged_scenes", "converged_scenes" in cal_res)

# Reset test scene
req("POST", "/calibration/reset-scene/test_scene_abc", label="Reset test scene params")

# ── THRESHOLDS ─────────────────────────────────────────────
section("6. Threshold Management")
req("POST", "/thresholds", {"warning_threshold": 15, "danger_threshold": 30},
    "Set valid thresholds")
t_res, _, _ = req("GET", "/thresholds")
check("Thresholds saved", (t_res or {}).get("warning") == 15 or
      (t_res or {}).get("warning_threshold") == 15, t_res)
_, _, bad_sc = req("POST", "/thresholds",
    {"warning_threshold": 50, "danger_threshold": 10}, "Invalid thresholds")
check("Invalid thresholds rejected", bad_sc == 400, f"HTTP {bad_sc}")
req("POST", "/thresholds", {"warning_threshold": 10, "danger_threshold": 25},
    "Restore defaults")

# ── LOCATION CAPACITY ──────────────────────────────────────
section("7. Location Capacity")
loc_res, _, sc = req("GET", "/location/config")
check("Location config readable", sc == 200, loc_res)
req("POST", "/location/config", {
    "name": "Test Location", "max_capacity": 200,
    "caution_pct": 0.5, "warning_pct": 0.75, "critical_pct": 0.9
}, "Save location config")

# ── ANOMALY DETECTION ──────────────────────────────────────
section("8. Anomaly Detection")
anom_res, _, sc = req("GET", "/anomaly/recent")
check("Anomaly endpoint works", sc == 200, sc)
if anom_res:
    check("Has anomalies list", "anomalies" in anom_res)

hist_res, _, _ = req("GET", "/anomaly/history")
check("Anomaly history works", hist_res is not None)

# ── SESSION & MULTI-CAMERA ─────────────────────────────────
section("9. Multi-Camera Session")
sess_res, _, sc = req("POST", "/session/create", label="Create session")
check("Session created", sc == 200, sc)
if sess_res:
    code = sess_res.get("code")
    check("Session has code", bool(code), code)
    check("Session has join_url", bool(sess_res.get("join_url")))
    if code:
        cams_res, _, _ = req("GET", f"/session/{code}/cameras")
        check("Session cameras endpoint", cams_res is not None)
        agg_res, _, _ = req("GET", f"/session/{code}/aggregate")
        check("Session aggregate endpoint", agg_res is not None)
cur_res, _, _ = req("GET", "/session/current")
check("Current session readable", cur_res is not None)

# ── CLOUD SYNC ─────────────────────────────────────────────
section("10. Cloud Sync (Supabase)")
cloud_res, _, _ = req("GET", "/cloud/status")
check("Cloud status reachable", cloud_res is not None)
check("Supabase connected", (cloud_res or {}).get("supabase_connected"),
      (cloud_res or {}).get("supabase_connected"))
stats_res, _, _ = req("GET", "/cloud/stats")
if stats_res and stats_res.get("connected"):
    s = stats_res.get("stats", {})
    check("Cloud has records", (s.get("total") or 0) >= 0, f"{s.get('total')} records")

# ── SCHEDULE ───────────────────────────────────────────────
section("11. Scheduled Analysis")
sch_res, _, _ = req("GET", "/schedule/config")
check("Schedule config readable", sch_res is not None, sch_res)
req("POST", "/schedule/start", {"interval_minutes": 5}, "Start schedule")
s2, _, _ = req("GET", "/schedule/config")
check("Schedule started", (s2 or {}).get("enabled"), s2)
req("POST", "/schedule/stop", label="Stop schedule")

# ── DEAD MAN'S SWITCH ──────────────────────────────────────
section("12. Dead Man's Switch")
dm_res, _, _ = req("GET", "/deadman/status")
check("Deadman status readable", dm_res is not None, dm_res)
req("POST", "/deadman/enable", {"minutes": 30}, "Enable deadman (30min)")
d2, _, _ = req("GET", "/deadman/status")
check("Deadman enabled", (d2 or {}).get("enabled"), d2)
req("POST", "/deadman/disable", label="Disable deadman")
d3, _, _ = req("GET", "/deadman/status")
check("Deadman disabled", not (d3 or {}).get("enabled"))

# ── SMS STATUS ─────────────────────────────────────────────
section("13. SMS Alert Config")
sms_res, _, _ = req("GET", "/sms/status")
check("SMS status readable", sms_res is not None)
check("SMS status field present", "enabled" in (sms_res or {}),
      (sms_res or {}).get("enabled"))

# ── WEEKLY ANALYTICS ───────────────────────────────────────
section("14. Analytics")
weekly_res, _, sc = req("GET", "/analytics/weekly")
check("Weekly comparison works", sc == 200)
if weekly_res and "error" not in weekly_res:
    check("Has this_week data", "this_week" in weekly_res)
    check("Has delta trend", "trend" in (weekly_res.get("delta") or {}),
          (weekly_res.get("delta") or {}).get("trend"))
    check("Total records", (weekly_res.get("total_records") or 0) >= 0,
          weekly_res.get("total_records"))
else:
    check("Weekly endpoint error", False, (weekly_res or {}).get("error"))

# ── AUTH SECURITY ──────────────────────────────────────────
section("15. Auth Security")
saved_token = token
token = "invalid_token_xyz"
_, _, unauth_sc = req("GET", "/auth/users", label="Users without valid token")
check("Invalid token rejected", unauth_sc in (401, 403), f"HTTP {unauth_sc}")
token = saved_token

token = None
_, _, no_auth_sc = req("GET", "/auth/users", label="Users without any token")
check("No token rejected", no_auth_sc in (401, 403), f"HTTP {no_auth_sc}")
token = saved_token

# ── RESPONSE TIMES ─────────────────────────────────────────
section("16. Performance")
LIMITS = {
    "GET /stats": 500, "GET /system/stats": 600,
    "GET /thresholds": 200, "GET /calibration": 500,
    "GET /history": 1000,
}
for path, limit in LIMITS.items():
    _, ms, _ = req("GET", path.split()[1])
    check(f"{path} under {limit}ms", ms < limit, f"{ms}ms")

# ── SUMMARY ────────────────────────────────────────────────
print(f"\n{'═'*55}")
passed  = sum(1 for r in results if r[0] == PASS)
warned  = sum(1 for r in results if r[0] == WARN)
failed  = sum(1 for r in results if r[0] == FAIL)
total   = len(results)
score   = round(passed/max(total,1)*100)
print(f"  Score: {score}%  |  {passed}✅  {warned}⚠️   {failed}❌  ({total} checks)")
print(f"{'═'*55}")
if failed:
    print(f"\n  Failed:")
    for r in results:
        if r[0] == FAIL: print(f"    • {r[1]}" + (f" — {r[3]}" if r[3] else ""))
if warned:
    print(f"\n  Warnings:")
    for r in results:
        if r[0] == WARN: print(f"    • {r[1]}" + (f" — {r[3]}" if r[3] else ""))
print()
