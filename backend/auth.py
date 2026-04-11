"""
Authentication system for CDMS.
JWT-based auth with roles: admin, operator, viewer.
"""
import os
import time
import bcrypt
import sqlite3
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.getenv("CDMS_SECRET_KEY", "cdms-secret-key-change-in-production-2026")
ALGORITHM  = "HS256"
TOKEN_EXPIRE_HOURS = 24

try:
    from jose import JWTError, jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    print("⚠️  python-jose not installed — auth disabled")


def get_db():
    conn = sqlite3.connect("logs/cdms.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_tables():
    """Create users and sessions tables."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name        TEXT NOT NULL,
            role        TEXT DEFAULT 'operator',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login  TIMESTAMP,
            active      INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS user_sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            token       TEXT UNIQUE,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at  TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    # Create default admin if no users exist
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0:
        create_user("admin@cdms.local", "admin123", "System Admin", "admin")
        print("✅ Default admin created: admin@cdms.local / admin123")
        print("⚠️  CHANGE THE DEFAULT PASSWORD in production!")
    conn.close()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except:
        return False


def create_user(email: str, password: str, name: str, role: str = "operator") -> dict:
    conn = get_db()
    try:
        hashed = hash_password(password)
        conn.execute(
            "INSERT INTO users (email, password_hash, name, role) VALUES (?, ?, ?, ?)",
            (email.lower().strip(), hashed, name, role)
        )
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
        return dict(user)
    except sqlite3.IntegrityError:
        raise ValueError(f"User {email} already exists")
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ? AND active = 1",
                       (email.lower().strip(),)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ? AND active = 1", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_token(user_id: int, role: str) -> str:
    if not JWT_AVAILABLE:
        return f"mock-token-{user_id}"
    payload = {
        "sub":  str(user_id),
        "role": role,
        "iat":  datetime.utcnow(),
        "exp":  datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    if not JWT_AVAILABLE:
        if token.startswith("mock-token-"):
            uid = int(token.split("-")[-1])
            return {"user_id": uid, "role": "admin"}
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"user_id": int(payload["sub"]), "role": payload["role"]}
    except JWTError:
        return None


def login(email: str, password: str) -> Optional[dict]:
    user = get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        return None
    token = create_token(user["id"], user["role"])
    # Update last login
    conn = get_db()
    conn.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))
    conn.commit()
    conn.close()
    return {
        "token":   token,
        "user_id": user["id"],
        "email":   user["email"],
        "name":    user["name"],
        "role":    user["role"],
        "expires_in": TOKEN_EXPIRE_HOURS * 3600,
    }


def get_all_users() -> list:
    conn = get_db()
    rows = conn.execute("SELECT id, email, name, role, created_at, last_login, active FROM users").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_user_role(user_id: int, role: str):
    conn = get_db()
    conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    conn.commit()
    conn.close()


def deactivate_user(user_id: int):
    conn = get_db()
    conn.execute("UPDATE users SET active = 0 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
