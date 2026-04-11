import os
import time
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

TWILIO_SID    = os.getenv("TWILIO_SID", "")
TWILIO_TOKEN  = os.getenv("TWILIO_TOKEN", "")
TWILIO_FROM   = os.getenv("TWILIO_FROM", "")
TWILIO_TO     = os.getenv("TWILIO_TO", "")

# Cooldown: max 1 SMS per 5 minutes per alert type
_last_sent = {}
COOLDOWN_SECONDS = 300

SMS_ENABLED = bool(TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM and TWILIO_TO)


def _can_send(alert_key: str) -> bool:
    now = time.time()
    last = _last_sent.get(alert_key, 0)
    return (now - last) > COOLDOWN_SECONDS


def send_sms_alert(person_count: int, risk_level: str, message: str,
                   scene_type: str = "unknown", location: str = "Main Location") -> dict:
    """
    Send SMS alert via Twilio.
    Respects cooldown — max 1 per 5 minutes per risk level.
    Returns dict with status and details.
    """
    if not SMS_ENABLED:
        return {"sent": False, "reason": "Twilio not configured — add TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, TWILIO_TO to .env"}

    if risk_level == "SAFE":
        return {"sent": False, "reason": "No alert needed for SAFE"}

    alert_key = f"{risk_level}"
    if not _can_send(alert_key):
        remaining = COOLDOWN_SECONDS - (time.time() - _last_sent.get(alert_key, 0))
        return {"sent": False, "reason": f"Cooldown active — {int(remaining)}s remaining"}

    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_TOKEN)

        now_str = datetime.now().strftime("%H:%M %d/%m/%Y")
        body = (
            f"🚨 CDMS ALERT\n"
            f"Location: {location}\n"
            f"Risk: {risk_level}\n"
            f"Count: {person_count} people\n"
            f"Scene: {scene_type}\n"
            f"Time: {now_str}\n"
            f"Msg: {message[:100]}"
        )

        msg = client.messages.create(
            body=body,
            from_=TWILIO_FROM,
            to=TWILIO_TO
        )

        _last_sent[alert_key] = time.time()
        print(f"📱 SMS sent: {risk_level} alert to {TWILIO_TO} (SID: {msg.sid})")
        return {"sent": True, "sid": msg.sid, "to": TWILIO_TO}

    except Exception as e:
        print(f"⚠️  SMS send failed: {e}")
        return {"sent": False, "reason": str(e)}


def send_surge_sms(person_count: int, rate: float, location: str = "Main Location") -> dict:
    """Send SMS specifically for crowd surge detection."""
    if not SMS_ENABLED:
        return {"sent": False, "reason": "not configured"}

    alert_key = "surge"
    if not _can_send(alert_key):
        return {"sent": False, "reason": "cooldown"}

    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        now_str = datetime.now().strftime("%H:%M %d/%m/%Y")
        body = (
            f"⚡ CDMS SURGE ALERT\n"
            f"Location: {location}\n"
            f"Crowd surge: +{rate:.1f} people/min\n"
            f"Current count: {person_count}\n"
            f"Time: {now_str}\n"
            f"Immediate action required!"
        )
        msg = client.messages.create(body=body, from_=TWILIO_FROM, to=TWILIO_TO)
        _last_sent[alert_key] = time.time()
        print(f"📱 Surge SMS sent (SID: {msg.sid})")
        return {"sent": True, "sid": msg.sid}
    except Exception as e:
        return {"sent": False, "reason": str(e)}


def get_sms_status() -> dict:
    return {
        "enabled": SMS_ENABLED,
        "configured": bool(TWILIO_SID),
        "cooldowns": {
            k: max(0, int(COOLDOWN_SECONDS - (time.time() - v)))
            for k, v in _last_sent.items()
        },
        "setup_instructions": None if SMS_ENABLED else
            "1. Sign up at twilio.com (free)\n"
            "2. Get Account SID, Auth Token, phone number\n"
            "3. Add to .env: TWILIO_SID=xxx TWILIO_TOKEN=xxx TWILIO_FROM=+1xxx TWILIO_TO=+1xxx"
    }
