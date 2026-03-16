import datetime
import os

LOG_FILE = "logs/alerts.log"

def generate_alert(density_result):
    """
    Generates an alert if risk level is WARNING or DANGER.
    Logs it to a file with a timestamp.
    Returns alert dictionary or None if safe.
    """
    risk = density_result["risk_level"]

    if risk == "SAFE":
        return None  # No alert needed

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    alert = {
        "timestamp": timestamp,
        "risk_level": risk,
        "person_count": density_result["person_count"],
        "density_score": density_result["density_score"],
        "message": density_result["message"]
    }

    # Save alert to log file
    os.makedirs("logs", exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {risk} | People: {alert['person_count']} "
                f"| Density: {alert['density_score']} | {alert['message']}\n")

    return alert


def get_recent_alerts(limit=20):
    """
    Reads the last N alerts from the log file.
    """
    if not os.path.exists(LOG_FILE):
        return []

    with open(LOG_FILE, "r") as f:
        lines = f.readlines()

    return [line.strip() for line in lines[-limit:]]
