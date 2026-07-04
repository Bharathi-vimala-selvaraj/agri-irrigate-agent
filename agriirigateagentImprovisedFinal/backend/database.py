"""
SQLite storage layer for AgriIrrigate AI.

No external service, no signup - the .db file is created automatically the
first time the app runs. Swappable later for a hosted Postgres by rewriting
this module only (every other module talks to it through these functions).
"""
import sqlite3
import json
import os
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.getenv("DATABASE_PATH", "agriirrigate.db")


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS farms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                crop_type TEXT NOT NULL,
                crop_variety TEXT,
                growth_stage TEXT NOT NULL DEFAULT 'vegetative',
                sowing_date TEXT,
                farm_size_acres REAL NOT NULL DEFAULT 2.0,
                irrigation_method TEXT NOT NULL DEFAULT 'drip',
                soil_type TEXT DEFAULT 'loam',
                water_source TEXT DEFAULT 'well',
                pump_capacity_hp REAL,
                ndvi REAL NOT NULL DEFAULT 0.65,
                soil_moisture REAL NOT NULL DEFAULT 55.0,
                disease_risk TEXT NOT NULL DEFAULT 'low',
                latitude REAL NOT NULL DEFAULT 11.0168,
                longitude REAL NOT NULL DEFAULT 76.9558,
                elevation REAL,
                slope REAL,
                terrain_type TEXT,
                drainage_characteristics TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
                date TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                duration_minutes INTEGER NOT NULL DEFAULT 0,
                water_quantity_mm REAL NOT NULL DEFAULT 0,
                irrigation_method TEXT NOT NULL,
                estimated_water_usage_liters REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Scheduled',
                reason TEXT,
                confidence_score REAL NOT NULL DEFAULT 0.8,
                weather_considered TEXT,
                is_manual INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER REFERENCES farms(id) ON DELETE CASCADE,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'info',
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS irrigation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
                schedule_id INTEGER REFERENCES schedules(id) ON DELETE SET NULL,
                date TEXT NOT NULL,
                water_used_mm REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )

        existing = conn.execute("SELECT COUNT(*) AS c FROM farms").fetchone()["c"]
        if existing == 0:
            now = datetime.utcnow().isoformat()
            conn.executemany(
                """INSERT INTO farms
                   (name, crop_type, growth_stage, farm_size_acres, irrigation_method,
                    ndvi, soil_moisture, disease_risk, latitude, longitude, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    ("Field A - Cotton", "Cotton", "flowering", 3.5, "drip",
                     0.68, 42.0, "low", 11.0168, 76.9558, now),
                    ("Field B - Tomato", "Tomato", "fruiting", 1.8, "sprinkler",
                     0.52, 35.0, "medium", 11.0245, 76.9310, now),
                ],
            )


# ---------- Farms ----------

def list_farms() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM farms ORDER BY id").fetchall()
        return [_row_to_dict(r) for r in rows]


def get_farm(farm_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM farms WHERE id = ?", (farm_id,)).fetchone()
        return _row_to_dict(row) if row else None


def create_farm(data: dict) -> dict:
    with get_conn() as conn:
        now = datetime.utcnow().isoformat()
        cur = conn.execute(
            """INSERT INTO farms
               (name, crop_type, crop_variety, growth_stage, sowing_date, farm_size_acres, irrigation_method,
                soil_type, water_source, pump_capacity_hp, ndvi, soil_moisture, disease_risk, latitude, longitude,
                elevation, slope, terrain_type, drainage_characteristics, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["name"], data["crop_type"], data.get("crop_variety"), data.get("growth_stage", "vegetative"),
                data.get("sowing_date"), data.get("farm_size_acres", 2.0), data.get("irrigation_method", "drip"),
                data.get("soil_type", "loam"), data.get("water_source", "well"), data.get("pump_capacity_hp"),
                data.get("ndvi", 0.65), data.get("soil_moisture", 55.0),
                data.get("disease_risk", "low"), data.get("latitude", 11.0168),
                data.get("longitude", 76.9558), data.get("elevation"), data.get("slope"),
                data.get("terrain_type"), data.get("drainage_characteristics"), now,
            ),
        )
        row = conn.execute("SELECT * FROM farms WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _row_to_dict(row)


def update_farm(farm_id: int, data: dict) -> dict | None:
    fields = {k: v for k, v in data.items() if v is not None}
    if not fields:
        return get_farm(farm_id)
    with get_conn() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(
            f"UPDATE farms SET {set_clause} WHERE id = ?",
            (*fields.values(), farm_id),
        )
    return get_farm(farm_id)


# ---------- Schedules ----------

def list_schedules(farm_id: int | None = None, date_from: str | None = None,
                    date_to: str | None = None) -> list[dict]:
    query = "SELECT * FROM schedules WHERE 1=1"
    params: list = []
    if farm_id is not None:
        query += " AND farm_id = ?"
        params.append(farm_id)
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)
    query += " ORDER BY date, start_time"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            d = _row_to_dict(r)
            if d.get("weather_considered"):
                try:
                    d["weather_considered"] = json.loads(d["weather_considered"])
                except (TypeError, json.JSONDecodeError):
                    pass
            result.append(d)
        return result


def get_schedule(schedule_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,)).fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        if d.get("weather_considered"):
            try:
                d["weather_considered"] = json.loads(d["weather_considered"])
            except (TypeError, json.JSONDecodeError):
                pass
        return d


def delete_schedules_for_farm_in_range(farm_id: int, date_from: str, date_to: str,
                                        only_status: str = "Scheduled"):
    """Clear auto-generated future schedules before regenerating, without touching
    ones the user already marked Running/Completed or edited manually."""
    with get_conn() as conn:
        conn.execute(
            """DELETE FROM schedules
               WHERE farm_id = ? AND date >= ? AND date <= ?
               AND status = ? AND is_manual = 0""",
            (farm_id, date_from, date_to, only_status),
        )


def create_schedule(data: dict) -> dict:
    with get_conn() as conn:
        now = datetime.utcnow().isoformat()
        cur = conn.execute(
            """INSERT INTO schedules
               (farm_id, date, start_time, end_time, duration_minutes, water_quantity_mm,
                irrigation_method, estimated_water_usage_liters, status, reason,
                confidence_score, weather_considered, is_manual, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["farm_id"], data["date"], data.get("start_time"), data.get("end_time"),
                data.get("duration_minutes", 0), data.get("water_quantity_mm", 0),
                data.get("irrigation_method", "drip"), data.get("estimated_water_usage_liters", 0),
                data.get("status", "Scheduled"), data.get("reason", ""),
                data.get("confidence_score", 0.8),
                json.dumps(data.get("weather_considered", {})),
                int(data.get("is_manual", False)), now, now,
            ),
        )
        row = conn.execute("SELECT * FROM schedules WHERE id = ?", (cur.lastrowid,)).fetchone()
        d = _row_to_dict(row)
        if d.get("weather_considered"):
            try:
                d["weather_considered"] = json.loads(d["weather_considered"])
            except (TypeError, json.JSONDecodeError):
                pass
        return d


def update_schedule(schedule_id: int, data: dict) -> dict | None:
    fields = {k: v for k, v in data.items() if v is not None}
    if not fields:
        return get_schedule(schedule_id)
    if "weather_considered" in fields:
        fields["weather_considered"] = json.dumps(fields["weather_considered"])
    fields["updated_at"] = datetime.utcnow().isoformat()
    with get_conn() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(
            f"UPDATE schedules SET {set_clause} WHERE id = ?",
            (*fields.values(), schedule_id),
        )
    return get_schedule(schedule_id)


def delete_schedule(schedule_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
        return cur.rowcount > 0


# ---------- Notifications ----------

def list_notifications(farm_id: int | None = None, unread_only: bool = False) -> list[dict]:
    query = "SELECT * FROM notifications WHERE 1=1"
    params: list = []
    if farm_id is not None:
        query += " AND farm_id = ?"
        params.append(farm_id)
    if unread_only:
        query += " AND is_read = 0"
    query += " ORDER BY created_at DESC"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(r) for r in rows]


def create_notification(data: dict) -> dict:
    with get_conn() as conn:
        now = datetime.utcnow().isoformat()
        cur = conn.execute(
            """INSERT INTO notifications (farm_id, type, message, severity, is_read, created_at)
               VALUES (?, ?, ?, ?, 0, ?)""",
            (data.get("farm_id"), data["type"], data["message"], data.get("severity", "info"), now),
        )
        row = conn.execute("SELECT * FROM notifications WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _row_to_dict(row)


def mark_notification_read(notification_id: int) -> dict | None:
    with get_conn() as conn:
        conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
        row = conn.execute("SELECT * FROM notifications WHERE id = ?", (notification_id,)).fetchone()
        return _row_to_dict(row) if row else None


# ---------- Irrigation history ----------

def add_history(data: dict) -> dict:
    with get_conn() as conn:
        now = datetime.utcnow().isoformat()
        cur = conn.execute(
            """INSERT INTO irrigation_history (farm_id, schedule_id, date, water_used_mm, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (data["farm_id"], data.get("schedule_id"), data["date"],
             data.get("water_used_mm", 0), data.get("status", "Completed"), now),
        )
        row = conn.execute("SELECT * FROM irrigation_history WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _row_to_dict(row)


def list_history(farm_id: int | None = None, limit: int = 60) -> list[dict]:
    query = "SELECT * FROM irrigation_history WHERE 1=1"
    params: list = []
    if farm_id is not None:
        query += " AND farm_id = ?"
        params.append(farm_id)
    query += " ORDER BY date DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(r) for r in rows]
