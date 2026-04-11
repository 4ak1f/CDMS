"""
Anomaly detection for CDMS.
Two detection modes:
  1. Statistical  — Z-score against Supabase hourly baseline (needs ≥50 records)
  2. Bootstrap    — Rate-of-change and session spike detection (always available)
Anomalies are stored in the Supabase `anomalies` table.
"""
import os
import time
from datetime import datetime, timezone
from collections import deque
from backend.supabase_sync import get_client

# ── session-level rolling window ─────────────────────────────────────────────
_recent_counts: deque = deque(maxlen=60)   # last 60 readings (≈ 3 min at 3 s interval)
_session_start_time: float = time.time()


def record_count(person_count: int) -> None:
    """Call this every time a new count arrives (webcam, image, video)."""
    _recent_counts.append({
        "count": person_count,
        "ts":    time.time(),
    })


# ── private helpers ───────────────────────────────────────────────────────────

def _get_rate_of_change() -> float:
    """People-per-minute change over the last two readings."""
    if len(_recent_counts) < 2:
        return 0.0
    latest   = _recent_counts[-1]
    previous = _recent_counts[-2]
    dt = latest["ts"] - previous["ts"]
    if dt <= 0:
        return 0.0
    delta = latest["count"] - previous["count"]
    return (delta / dt) * 60  # scale to per-minute


def _get_supabase_baseline(hour: int) -> dict | None:
    """
    Fetch the average and std-dev for the given hour-of-day from Supabase.
    Returns {"avg": float, "std": float, "n": int} or None.
    Needs ≥ 50 historical records for that hour.
    """
    client = get_client()
    if not client:
        return None
    try:
        result = (
            client.table("detections")
            .select("person_count")
            .execute()
        )
        rows = result.data or []
        if len(rows) < 50:
            return None
        counts = [r["person_count"] for r in rows if r.get("person_count") is not None]
        if not counts:
            return None
        avg = sum(counts) / len(counts)
        variance = sum((c - avg) ** 2 for c in counts) / len(counts)
        std = variance ** 0.5
        return {"avg": avg, "std": std, "n": len(counts)}
    except Exception as e:
        print(f"⚠️  Anomaly baseline fetch failed: {e}")
        return None


def _store_anomaly(anomaly_type: str, description: str, person_count: int,
                   severity: str, z_score=None, baseline_avg=None,
                   rate_of_change=None) -> None:
    """Write one anomaly record to Supabase `anomalies` table."""
    client = get_client()
    if not client:
        return
    try:
        row = {
            "timestamp":      datetime.now(timezone.utc).isoformat(),
            "anomaly_type":   anomaly_type,
            "description":    description,
            "person_count":   person_count,
            "severity":       severity,
            "device_id":      os.getenv("CDMS_DEVICE_ID", "default"),
        }
        if z_score is not None:
            row["z_score"] = z_score
        if baseline_avg is not None:
            row["baseline_avg"] = baseline_avg
        if rate_of_change is not None:
            row["rate_of_change"] = rate_of_change
        client.table("anomalies").insert(row).execute()
    except Exception as e:
        print(f"⚠️  Anomaly store failed: {e}")


# ── public API ────────────────────────────────────────────────────────────────

def analyze_for_anomalies(person_count: int) -> dict | None:
    """
    Run both anomaly detectors against `person_count`.
    Returns an anomaly dict if one is found, else None.
    Dict shape: {type, description, severity, z_score?, rate_of_change?}
    """
    record_count(person_count)
    now_hour = datetime.now().hour
    anomaly  = None

    # ── 1. Statistical (Z-score) ─────────────────────────────────────────────
    baseline = _get_supabase_baseline(now_hour)
    if baseline and baseline["std"] > 0:
        z = (person_count - baseline["avg"]) / baseline["std"]
        if abs(z) >= 2.5:
            severity = "critical" if abs(z) >= 4.0 else "high" if abs(z) >= 3.0 else "medium"
            description = (
                f"Statistical anomaly: count {person_count} is "
                f"{z:+.1f} std-devs from hourly avg ({baseline['avg']:.0f})"
            )
            _store_anomaly(
                anomaly_type="statistical",
                description=description,
                person_count=person_count,
                severity=severity,
                z_score=round(z, 2),
                baseline_avg=round(baseline["avg"], 1),
            )
            anomaly = {
                "type":        "statistical",
                "description": description,
                "severity":    severity,
                "z_score":     round(z, 2),
            }

    # ── 2. Bootstrap (rate-of-change + session spike) ────────────────────────
    rate = _get_rate_of_change()

    # 2a — rapid surge / evacuation
    if abs(rate) >= 10:
        direction = "surge" if rate > 0 else "evacuation"
        severity  = "critical" if abs(rate) >= 30 else "high" if abs(rate) >= 20 else "medium"
        description = (
            f"Rapid {direction} detected: {rate:+.1f} people/min "
            f"(count now {person_count})"
        )
        _store_anomaly(
            anomaly_type=f"rapid_{direction}",
            description=description,
            person_count=person_count,
            severity=severity,
            rate_of_change=round(rate, 1),
        )
        if anomaly is None:
            anomaly = {
                "type":            f"rapid_{direction}",
                "description":     description,
                "severity":        severity,
                "rate_of_change":  round(rate, 1),
            }

    # 2b — session spike (≥3× session average)
    if len(_recent_counts) >= 5:
        session_counts = [r["count"] for r in _recent_counts]
        session_avg    = sum(session_counts[:-1]) / max(len(session_counts) - 1, 1)
        if session_avg > 0 and person_count >= session_avg * 3:
            description = (
                f"Session spike: count {person_count} is "
                f"{person_count / session_avg:.1f}× session avg ({session_avg:.0f})"
            )
            _store_anomaly(
                anomaly_type="session_spike",
                description=description,
                person_count=person_count,
                severity="high",
            )
            if anomaly is None:
                anomaly = {
                    "type":        "session_spike",
                    "description": description,
                    "severity":    "high",
                }

    return anomaly


def get_recent_anomalies(limit: int = 10) -> list:
    """Fetch the most recent anomalies from Supabase."""
    client = get_client()
    if not client:
        return []
    try:
        result = (
            client.table("anomalies")
            .select("*")
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        print(f"⚠️  get_recent_anomalies failed: {e}")
        return []


def get_anomaly_stats() -> dict:
    """Aggregate stats for the anomalies table."""
    client = get_client()
    if not client:
        return {"total": 0, "by_type": {}, "by_severity": {}}
    try:
        result = client.table("anomalies").select("anomaly_type, severity").execute()
        rows   = result.data or []
        by_type: dict     = {}
        by_severity: dict = {}
        for r in rows:
            t = r.get("anomaly_type", "unknown")
            s = r.get("severity", "unknown")
            by_type[t]     = by_type.get(t, 0) + 1
            by_severity[s] = by_severity.get(s, 0) + 1
        return {"total": len(rows), "by_type": by_type, "by_severity": by_severity}
    except Exception as e:
        print(f"⚠️  get_anomaly_stats failed: {e}")
        return {"total": 0, "by_type": {}, "by_severity": {}}


def get_crowd_flow_state() -> dict:
    """
    Summarise the current crowd flow from the rolling window.
    Returns direction, rate_per_min, trend.
    """
    if len(_recent_counts) < 2:
        return {"direction": "stable", "rate_per_min": 0.0, "trend": "insufficient_data"}

    rate = _get_rate_of_change()
    counts = [r["count"] for r in _recent_counts]

    if rate > 5:
        direction = "increasing"
    elif rate < -5:
        direction = "decreasing"
    else:
        direction = "stable"

    # Simple linear trend over last 10 readings
    window = counts[-10:]
    if len(window) >= 3:
        mid   = len(window) // 2
        first = sum(window[:mid]) / max(mid, 1)
        last  = sum(window[mid:]) / max(len(window) - mid, 1)
        trend = "up" if last > first * 1.1 else "down" if last < first * 0.9 else "flat"
    else:
        trend = "flat"

    return {
        "direction":    direction,
        "rate_per_min": round(rate, 1),
        "trend":        trend,
        "window_size":  len(_recent_counts),
        "latest_count": counts[-1] if counts else 0,
    }
