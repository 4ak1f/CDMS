"""
WebRTC signaling and video processing for phone cameras.
Uses aiortc for peer connections and Socket.IO for signaling.
"""

import asyncio
import cv2
import numpy as np
import time
import fractions
try:
    from av import VideoFrame
    AV_AVAILABLE = True
except ImportError:
    AV_AVAILABLE = False
    print("⚠️  av not available — WebRTC video processing disabled")

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
    from aiortc.contrib.media import MediaRelay
    AIORTC_AVAILABLE = True
except ImportError:
    AIORTC_AVAILABLE = False
    print("⚠️  aiortc not available — WebRTC disabled")

from backend.camera_session import join_session, leave_session, update_camera

relay = MediaRelay()

# Store peer connections: camera_id -> RTCPeerConnection
_peer_connections = {}


class VideoAnalysisTrack(MediaStreamTrack):
    """
    Receives video frames from a phone camera.
    Runs AI analysis every N frames.
    Sends results back via callback.
    """
    kind = "video"

    def __init__(self, track, session_code, camera_id, analyze_fn, result_callback):
        super().__init__()
        self.track           = track
        self.session_code    = session_code
        self.camera_id       = camera_id
        self.analyze_fn      = analyze_fn
        self.result_callback = result_callback
        self.frame_count     = 0
        self.last_analysis   = 0
        self.ANALYSIS_INTERVAL = 3  # analyze every 3 seconds

    async def recv(self):
        frame = await self.track.recv()
        self.frame_count += 1

        now = time.time()
        if now - self.last_analysis >= self.ANALYSIS_INTERVAL:
            self.last_analysis = now
            try:
                img = frame.to_ndarray(format="bgr24")
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self.analyze_fn, img
                )
                update_camera(self.session_code, self.camera_id, {
                    "person_count": result.get("person_count", 0),
                    "risk_level":   result.get("risk_level", "SAFE"),
                    "scene_type":   result.get("scene_type", "unknown"),
                    "scene_fingerprint": result.get("scene_fingerprint", "unknown"),
                    "frame_count":  self.frame_count,
                    "fps":          round(self.frame_count / max(now - self.last_analysis + self.ANALYSIS_INTERVAL, 1), 1),
                })
                if self.result_callback:
                    await self.result_callback(self.camera_id, result)
            except Exception as e:
                print(f"⚠️ Frame analysis error: {e}")

        return frame


async def handle_offer(
    session_code: str,
    camera_name: str,
    sdp: str,
    sdp_type: str,
    analyze_fn,
    result_callback=None
) -> dict:
    """
    Handle WebRTC offer from a phone camera.
    Returns SDP answer to send back to phone.
    """
    camera = join_session(session_code, camera_name)
    if not camera:
        return {"error": "Session not found"}

    camera_id = camera["id"]
    pc = RTCPeerConnection()
    _peer_connections[camera_id] = pc

    @pc.on("connectionstatechange")
    async def on_state():
        print(f"📡 Camera {camera_id} state: {pc.connectionState}")
        if pc.connectionState in ("failed", "closed", "disconnected"):
            leave_session(session_code, camera_id)
            if camera_id in _peer_connections:
                del _peer_connections[camera_id]

    @pc.on("track")
    def on_track(track):
        if track.kind == "video":
            analysis_track = VideoAnalysisTrack(
                relay.subscribe(track),
                session_code, camera_id,
                analyze_fn, result_callback
            )
            pc.addTrack(analysis_track)

    offer = RTCSessionDescription(sdp=sdp, type=sdp_type)
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {
        "sdp":  pc.localDescription.sdp,
        "type": pc.localDescription.type,
        "camera_id": camera_id,
        "camera_name": camera["name"],
    }


async def close_camera(camera_id: str):
    """Close a specific camera's peer connection."""
    if camera_id in _peer_connections:
        await _peer_connections[camera_id].close()
        del _peer_connections[camera_id]


async def close_all():
    """Close all peer connections."""
    for pc in _peer_connections.values():
        await pc.close()
    _peer_connections.clear()
