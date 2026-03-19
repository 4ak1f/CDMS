import sqlite3
import datetime
import os

DB_PATH = "logs/cdms.db"

def init_db():
    """Creates the database and tables if they don't exist."""
    os.makedirs("logs", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            person_count INTEGER,
            density_score REAL,
            risk_level TEXT,
            message TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_detection(person_count, density_score, risk_level, message):
    """Saves a detection result to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO detections (timestamp, person_count, density_score, risk_level, message)
        VALUES (?, ?, ?, ?, ?)
    """, (timestamp, person_count, density_score, risk_level, message))
    conn.commit()
    conn.close()

def get_all_detections(limit=50):
    """Fetches the most recent detections from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, person_count, density_score, risk_level, message
        FROM detections
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "timestamp": r[0],
            "person_count": r[1],
            "density_score": r[2],
            "risk_level": r[3],
            "message": r[4]
        }
        for r in rows
    ]
def get_thresholds():
    """Gets current threshold settings."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()

    cursor.execute("SELECT key, value FROM settings WHERE key LIKE 'threshold_%'")
    rows = cursor.fetchall()
    conn.close()

    settings = {row[0]: float(row[1]) for row in rows}

    # Default thresholds if not set
    return {
        "warning_threshold": settings.get("threshold_warning", 2.0),
        "danger_threshold":  settings.get("threshold_danger",  5.0),
        "warning_label":     "WARNING",
        "danger_label":      "OVERCROWDED",
        "safe_label":        "SAFE"
    }


def save_thresholds(warning: float, danger: float):
    """Saves custom threshold settings."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                   ("threshold_warning", str(warning)))
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                   ("threshold_danger", str(danger)))
    conn.commit()
    conn.close()