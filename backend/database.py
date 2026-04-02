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
def store_feedback(predicted_count, actual_count, scene_type, image_hash=None):
    """Stores user feedback for model improvement."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            predicted_count INTEGER,
            actual_count INTEGER,
            scene_type TEXT,
            image_hash TEXT,
            scale_factor REAL,
            correction_ratio REAL
        )
    """)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    correction_ratio = actual_count / max(predicted_count, 1)
    cursor.execute("""
        INSERT INTO feedback 
        (timestamp, predicted_count, actual_count, scene_type, image_hash, correction_ratio)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (timestamp, predicted_count, actual_count, scene_type, image_hash, correction_ratio))
    conn.commit()
    conn.close()
    print(f"✅ Feedback stored: predicted={predicted_count}, actual={actual_count}, ratio={correction_ratio:.2f}")


def get_feedback_stats():
    """Gets feedback statistics for calibration."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT scene_type, AVG(correction_ratio), COUNT(*), AVG(actual_count)
            FROM feedback
            GROUP BY scene_type
        """)
        rows = cursor.fetchall()
        conn.close()
        return {
            row[0]: {
                "avg_correction_ratio": row[1],
                "sample_count": row[2],
                "avg_actual_count": row[3]
            }
            for row in rows
        }
    except:
        conn.close()
        return {}


def get_all_feedback(limit=50):
    """Gets recent feedback entries."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT timestamp, predicted_count, actual_count, 
                   scene_type, correction_ratio
            FROM feedback
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [{
            "timestamp":        r[0],
            "predicted_count":  r[1],
            "actual_count":     r[2],
            "scene_type":       r[3],
            "correction_ratio": round(r[4], 2)
        } for r in rows]
    except:
        conn.close()
        return []    
    
def log_incident(person_count, density_score, risk_level, message, zone_data=None):
    """Logs only WARNING/DANGER events to separate incident table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            person_count INTEGER,
            density_score REAL,
            risk_level TEXT,
            message TEXT,
            zone_data TEXT
        )
    """)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO incidents (timestamp, person_count, density_score, risk_level, message, zone_data)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (timestamp, person_count, density_score, risk_level, message,
          str(zone_data) if zone_data else None))
    conn.commit()
    conn.close()


def get_incidents(limit=50):
    """Gets recent incidents."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT timestamp, person_count, density_score, risk_level, message
            FROM incidents ORDER BY id DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [{"timestamp": r[0], "person_count": r[1],
                 "density_score": r[2], "risk_level": r[3], "message": r[4]}
                for r in rows]
    except:
        conn.close()
        return []


def clear_detections():
    """Clears all detection history."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM detections")
    conn.commit()
    conn.close()


def archive_old_detections(days=30):
    """Removes detections older than X days."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM detections
        WHERE timestamp < datetime('now', ?)
    """, (f'-{days} days',))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def save_zone_config(zones_config):
    """Saves zone naming and capacity config."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT
        )
    """)
    cursor.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)",
                   ("zone_config", str(zones_config)))
    conn.commit()
    conn.close()


def get_zone_config():
    """Gets zone config."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT value FROM settings WHERE key='zone_config'")
        row = cursor.fetchone()
        conn.close()
        if row:
            import ast
            return ast.literal_eval(row[0])
    except:
        conn.close()
    return {}