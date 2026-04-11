"""
Multi-camera session management for CDMS.
Manages WebRTC connections from multiple phone cameras.
Each phone gets a peer connection, streams video, receives AI results.
"""

import asyncio
import uuid
import time
import json
from datetime import datetime
from typing import Dict, Optional

# Active sessions: session_code -> session data
_sessions: Dict[str, dict] = {}

# Active cameras per session: session_code -> {camera_id -> camera_data}
_cameras: Dict[str, Dict[str, dict]] = {}


def create_session() -> dict:
    """Create a new monitoring session. Returns session info."""
    code = str(uuid.uuid4())[:8].upper()
    session = {
        "code":         code,
        "created_at":   datetime.utcnow().isoformat(),
        "active":       True,
        "camera_count": 0,
    }
    _sessions[code] = session
    _cameras[code]  = {}
    print(f"📡 Session created: {code}")
    return session


def get_session(code: str) -> Optional[dict]:
    return _sessions.get(code)


def join_session(code: str, camera_name: str = None) -> Optional[dict]:
    """Register a new camera joining a session."""
    if code not in _sessions:
        return None
    camera_id = str(uuid.uuid4())[:8]
    idx = len(_cameras[code]) + 1
    camera = {
        "id":           camera_id,
        "session_code": code,
        "name":         camera_name or f"CAM_{idx:02d}",
        "joined_at":    datetime.utcnow().isoformat(),
        "last_seen":    time.time(),
        "person_count": 0,
        "risk_level":   "SAFE",
        "scene_type":   "unknown",
        "fps":          0,
        "active":       True,
        "frame_count":  0,
    }
    _cameras[code][camera_id] = camera
    _sessions[code]["camera_count"] = len(_cameras[code])
    print(f"📱 Camera joined session {code}: {camera['name']} ({camera_id})")
    return camera


def update_camera(code: str, camera_id: str, data: dict):
    """Update camera analysis results."""
    if code in _cameras and camera_id in _cameras[code]:
        _cameras[code][camera_id].update(data)
        _cameras[code][camera_id]["last_seen"] = time.time()


def leave_session(code: str, camera_id: str):
    """Remove a camera from session."""
    if code in _cameras and camera_id in _cameras[code]:
        name = _cameras[code][camera_id]["name"]
        del _cameras[code][camera_id]
        _sessions[code]["camera_count"] = len(_cameras[code])
        print(f"📱 Camera left session {code}: {name}")


def get_session_cameras(code: str) -> list:
    """Get all active cameras in a session."""
    if code not in _cameras:
        return []
    now = time.time()
    # Mark cameras inactive if not seen in 10s
    for cam in _cameras[code].values():
        cam["active"] = (now - cam["last_seen"]) < 10
    return list(_cameras[code].values())


def get_session_aggregate(code: str) -> dict:
    """Get aggregate stats across all cameras in session."""
    cameras = get_session_cameras(code)
    active  = [c for c in cameras if c["active"]]
    total   = sum(c["person_count"] for c in active)
    risks   = [c["risk_level"] for c in active]
    risk    = "DANGER" if "DANGER" in risks else "WARNING" if "WARNING" in risks else "SAFE"
    return {
        "total_people": total,
        "camera_count": len(active),
        "risk_level":   risk,
        "cameras":      cameras,
    }


def list_all_sessions() -> list:
    return list(_sessions.values())
