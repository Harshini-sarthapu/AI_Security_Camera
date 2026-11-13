"""
Database module for AI-Powered Smart Security Camera.
Handles SQLite database operations for security event storage.
"""

import sqlite3
import os
from datetime import datetime
from config import CONFIG


def get_db_connection():
    """Create and return a database connection with row factory."""
    db_path = CONFIG["database_path"]
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database and create the events table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            camera TEXT DEFAULT 'Camera 1',
            location TEXT DEFAULT 'Main Entrance',
            risk_level TEXT NOT NULL CHECK(risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
            description TEXT,
            image_path TEXT,
            status TEXT DEFAULT 'NEW'
        )
    """)
    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully.")


def add_event(event_type, camera, location, risk_level, description, image_path=None):
    """
    Insert a new security event into the database.
    Returns the ID of the newly created event.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO events (event_type, timestamp, camera, location, risk_level, description, image_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (event_type, timestamp, camera, location, risk_level, description, image_path))
    conn.commit()
    event_id = cursor.lastrowid
    conn.close()
    return event_id


def get_events(event_type=None, risk_level=None, date=None, limit=100):
    """
    Retrieve events with optional filtering.
    Returns a list of dictionaries.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM events WHERE 1=1"
    params = []

    if event_type and event_type != "all":
        query += " AND event_type = ?"
        params.append(event_type)
    if risk_level and risk_level != "all":
        query += " AND risk_level = ?"
        params.append(risk_level)
    if date:
        query += " AND DATE(timestamp) = ?"
        params.append(date)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_recent_events(limit=20):
    """Get the most recent events for dashboard display."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_event_by_id(event_id):
    """Get a single event by its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_stats():
    """Get aggregate statistics for the dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total events
    cursor.execute("SELECT COUNT(*) as total FROM events")
    total = cursor.fetchone()["total"]

    # Events by risk level
    cursor.execute("SELECT risk_level, COUNT(*) as count FROM events GROUP BY risk_level")
    risk_counts = {row["risk_level"]: row["count"] for row in cursor.fetchall()}

    # Recent events count (last hour)
    cursor.execute("""
        SELECT COUNT(*) as recent FROM events
        WHERE timestamp >= datetime('now', '-1 hour')
    """)
    recent = cursor.fetchone()["recent"]

    # Events by type
    cursor.execute("SELECT event_type, COUNT(*) as count FROM events GROUP BY event_type")
    type_counts = {row["event_type"]: row["count"] for row in cursor.fetchall()}

    conn.close()

    return {
        "total_events": total,
        "risk_counts": risk_counts,
        "recent_events": recent,
        "type_counts": type_counts,
        "high_alerts": risk_counts.get("HIGH", 0),
        "medium_alerts": risk_counts.get("MEDIUM", 0),
        "low_alerts": risk_counts.get("LOW", 0),
    }
