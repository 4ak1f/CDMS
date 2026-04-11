"""
Supabase cloud sync for CDMS.
Syncs detections, feedback, and incidents to Supabase cloud database.
Auto-archives local DB to cloud every 100 detections then clears local.
"""
import os
import time
import json
from datetime import datetime

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️  supabase package not installed — cloud sync disabled")

from dotenv import load_dotenv
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

_client = None

def get_client():
    global _client
    if not SUPABASE_AVAILABLE or not SUPABASE_URL or not SUPABASE_KEY:
        return None
    if _client is None:
        try:
            _client = create_client(SUPABASE_URL, SUPABASE_KEY)
            print("✅ Supabase cloud sync connected")
        except Exception as e:
            print(f"⚠️  Supabase connection failed: {e}")
            return None
    return _client

def sync_detection(detection: dict) -> bool:
    """Sync a single detection to Supabase."""
    client = get_client()
    if not client:
        return False
    try:
        client.table("detections").insert({
            "timestamp":         detection.get("timestamp") or datetime.utcnow().isoformat(),
            "person_count":      detection.get("person_count", 0),
            "density_score":     detection.get("density_score", 0.0),
            "risk_level":        detection.get("risk_level", "SAFE"),
            "scene_type":        detection.get("scene_type", "unknown"),
            "scene_fingerprint": detection.get("scene_fingerprint", "unknown"),
            "message":           detection.get("message", ""),
            "zones":             detection.get("zones", None),
            "device_id":         os.getenv("CDMS_DEVICE_ID", "default"),
        }).execute()
        return True
    except Exception as e:
        print(f"⚠️  Supabase sync failed: {e}")
        return False

def sync_feedback(predicted: int, actual: int, scene_type: str, fingerprint: str) -> bool:
    """Sync feedback to Supabase."""
    client = get_client()
    if not client:
        return False
    try:
        client.table("feedback_log").insert({
            "predicted":         predicted,
            "actual":            actual,
            "scene_type":        scene_type,
            "fingerprint":       fingerprint,
            "correction_ratio":  round(actual / max(predicted, 1), 3),
            "device_id":         os.getenv("CDMS_DEVICE_ID", "default"),
        }).execute()
        return True
    except Exception as e:
        print(f"⚠️  Supabase feedback sync failed: {e}")
        return False

def sync_incident(incident: dict) -> bool:
    """Sync an incident to Supabase."""
    client = get_client()
    if not client:
        return False
    try:
        client.table("incidents_log").insert({
            "person_count":  incident.get("person_count", 0),
            "density_score": incident.get("density_score", 0.0),
            "risk_level":    incident.get("risk_level", "WARNING"),
            "message":       incident.get("message", ""),
        }).execute()
        return True
    except Exception as e:
        print(f"⚠️  Supabase incident sync failed: {e}")
        return False

def bulk_archive_and_clear(detections: list) -> dict:
    """
    Bulk upload detections to Supabase then signal local clear.
    Called automatically every 100 detections.
    """
    client = get_client()
    if not client:
        return {"synced": 0, "error": "Supabase not configured"}
    try:
        rows = [{
            "timestamp":         d.get("timestamp") or datetime.utcnow().isoformat(),
            "person_count":      d.get("person_count", 0),
            "density_score":     d.get("density_score", 0.0),
            "risk_level":        d.get("risk_level", "SAFE"),
            "scene_type":        d.get("scene_type", "unknown"),
            "scene_fingerprint": d.get("scene_fingerprint", "unknown"),
            "message":           d.get("message", ""),
            "device_id":         os.getenv("CDMS_DEVICE_ID", "default"),
        } for d in detections]
        # Supabase handles up to 1000 rows per insert
        for i in range(0, len(rows), 500):
            client.table("detections").insert(rows[i:i+500]).execute()
        print(f"☁️  Archived {len(rows)} detections to Supabase cloud")
        return {"synced": len(rows), "error": None}
    except Exception as e:
        print(f"⚠️  Bulk archive failed: {e}")
        return {"synced": 0, "error": str(e)}

def get_cloud_stats() -> dict:
    """Get aggregate stats from cloud database."""
    client = get_client()
    if not client:
        return {}
    try:
        result = client.table("detections").select("person_count, risk_level, timestamp").order("timestamp", desc=True).limit(1000).execute()
        rows = result.data or []
        if not rows:
            return {"total": 0}
        counts = [r["person_count"] for r in rows if r["person_count"] is not None]
        risk_dist = {}
        for r in rows:
            rl = r.get("risk_level", "SAFE")
            risk_dist[rl] = risk_dist.get(rl, 0) + 1
        return {
            "total":      len(rows),
            "avg_count":  round(sum(counts) / len(counts), 1) if counts else 0,
            "peak_count": max(counts) if counts else 0,
            "risk_distribution": risk_dist,
            "latest_timestamp": rows[0]["timestamp"] if rows else None,
        }
    except Exception as e:
        print(f"⚠️  Cloud stats failed: {e}")
        return {}

def is_connected() -> bool:
    return get_client() is not None
