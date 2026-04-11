"""
Background scheduled analysis for CDMS.
Automatically analyzes camera feed at configured intervals.
"""
import asyncio
import time
import threading
import cv2
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

_scheduler = None
_schedule_config = {
    "enabled": False,
    "interval_minutes": 5,
    "last_run": None,
    "last_result": None,
    "run_count": 0,
}


def get_schedule_config() -> dict:
    return _schedule_config.copy()


def init_scheduler(analyze_fn):
    """Initialize the scheduler with the analysis function."""
    global _scheduler
    _scheduler = AsyncIOScheduler()
    print("📅 Scheduler initialized")
    return _scheduler


async def run_scheduled_analysis(analyze_fn, camera_source=0):
    """Run a single scheduled analysis cycle."""
    global _schedule_config
    print(f"📅 Running scheduled analysis at {datetime.now().strftime('%H:%M:%S')}")
    try:
        cap = None
        for idx in [0, 1, 2]:
            test = cv2.VideoCapture(idx)
            if test.isOpened():
                cap = test
                break
            test.release()

        if not cap or not cap.isOpened():
            print("📅 Scheduled analysis: no camera found on indices 0,1,2 — skipping")
            _schedule_config["last_result"] = {"error": "no_camera", "timestamp": datetime.utcnow().isoformat()}
            return
        ret, frame = cap.read()
        cap.release()
        if not ret:
            print("📅 Could not read frame from camera")
            return
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, analyze_fn, frame)
        _schedule_config["last_run"] = datetime.utcnow().isoformat()
        _schedule_config["last_result"] = result
        _schedule_config["run_count"] += 1
        print(f"📅 Scheduled analysis complete: {result.get('person_count', 0)} people, {result.get('risk_level', 'SAFE')}")
    except Exception as e:
        print(f"📅 Scheduled analysis error: {e}")
        _schedule_config["last_result"] = {"error": str(e), "timestamp": datetime.utcnow().isoformat()}


def start_schedule(analyze_fn, interval_minutes: int, camera_source=0):
    """Start scheduled analysis."""
    global _scheduler, _schedule_config
    if _scheduler is None:
        init_scheduler(analyze_fn)
    _scheduler.remove_all_jobs()
    _scheduler.add_job(
        run_scheduled_analysis,
        trigger=IntervalTrigger(minutes=interval_minutes),
        args=[analyze_fn, camera_source],
        id="scheduled_analysis",
        name=f"Auto-analysis every {interval_minutes}min",
        replace_existing=True,
    )
    if not _scheduler.running:
        _scheduler.start()
    _schedule_config["enabled"] = True
    _schedule_config["interval_minutes"] = interval_minutes
    print(f"📅 Scheduled analysis started: every {interval_minutes} minutes")


def stop_schedule():
    """Stop scheduled analysis."""
    global _scheduler, _schedule_config
    if _scheduler and _scheduler.running:
        _scheduler.remove_all_jobs()
    _schedule_config["enabled"] = False
    print("📅 Scheduled analysis stopped")


# ── Dead Man's Switch ─────────────────────────────────────────────────────────
_deadman_timer: threading.Timer | None = None
_deadman_enabled = False
_deadman_timeout_sec = 300  # default 5 minutes
_deadman_last_heartbeat: float | None = None
_deadman_alert_fn = None


def update_heartbeat():
    """Call this after every successful analysis to reset the dead man's timer."""
    global _deadman_last_heartbeat
    _deadman_last_heartbeat = time.time()
    if _deadman_enabled:
        _reset_deadman_timer()


def _reset_deadman_timer():
    global _deadman_timer
    if _deadman_timer is not None:
        _deadman_timer.cancel()
    _deadman_timer = threading.Timer(_deadman_timeout_sec, _trigger_deadman_alert)
    _deadman_timer.daemon = True
    _deadman_timer.start()


def _trigger_deadman_alert():
    global _deadman_enabled
    elapsed = time.time() - (_deadman_last_heartbeat or 0)
    print(f"☠️  Dead man's switch triggered — no analysis for {elapsed:.0f}s")
    if _deadman_alert_fn:
        try:
            _deadman_alert_fn(elapsed)
        except Exception as e:
            print(f"☠️  Dead man's alert callback error: {e}")


def enable_deadman(timeout_sec: int = 300, alert_fn=None):
    """Enable the dead man's switch with given timeout in seconds."""
    global _deadman_enabled, _deadman_timeout_sec, _deadman_alert_fn
    _deadman_enabled = True
    _deadman_timeout_sec = timeout_sec
    _deadman_alert_fn = alert_fn
    _reset_deadman_timer()
    print(f"☠️  Dead man's switch enabled — timeout {timeout_sec}s")


def disable_deadman():
    """Disable the dead man's switch."""
    global _deadman_enabled, _deadman_timer
    _deadman_enabled = False
    if _deadman_timer is not None:
        _deadman_timer.cancel()
        _deadman_timer = None
    print("☠️  Dead man's switch disabled")


def get_deadman_status() -> dict:
    now = time.time()
    elapsed = round(now - _deadman_last_heartbeat, 1) if _deadman_last_heartbeat else None
    remaining = None
    if _deadman_enabled and _deadman_last_heartbeat:
        remaining = max(0, round(_deadman_timeout_sec - (now - _deadman_last_heartbeat), 1))
    return {
        "enabled": _deadman_enabled,
        "timeout_sec": _deadman_timeout_sec,
        "last_heartbeat": _deadman_last_heartbeat,
        "seconds_since_heartbeat": elapsed,
        "seconds_until_trigger": remaining,
    }
