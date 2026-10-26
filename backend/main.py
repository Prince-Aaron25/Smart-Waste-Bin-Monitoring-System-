
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import hmac
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Query, Security
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from database import get_connection, initialize_database, log_system_event

load_dotenv(Path(__file__).resolve().parent / ".env")
API_KEY = os.getenv("SMART_BIN_API_KEY")

if not API_KEY:
    raise RuntimeError("SMART_BIN_API_KEY is missing")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def authenticate(key: str | None = Security(api_key_header)):
    if not key or not hmac.compare_digest(key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Smart Waste Bin Monitoring API",
    version="1.0.0",
    lifespan=lifespan
)


class ReadingInput(BaseModel):
    device_id: int = Field(gt=0)
    raw_distance_cm: float = Field(ge=0, allow_inf_nan=False)


def get_device(conn, device_id):
    device = conn.execute(
        "SELECT * FROM devices WHERE device_id = ?",
        (device_id,)
    ).fetchone()

    if not device:
        raise HTTPException(404, "Device not registered")

    if device["status"] in ("inactive", "maintenance"):
        raise HTTPException(409, "Device not accepting readings")

    return device


@app.get("/health")
def health():
    with get_connection() as conn:
        conn.execute("SELECT 1").fetchone()
    return {"status": "healthy", "database": "connected"}


@app.post("/api/readings", dependencies=[Depends(authenticate)])
def save_reading(data: ReadingInput):
    with get_connection() as conn:
        device = get_device(conn, data.device_id)
        height = device["bin_height_cm"]
        raw = data.raw_distance_cm

        # ETL: validate physical measurement range
        if raw > height:
            raise HTTPException(
                422, "Distance exceeds configured bin height"
            )

        # Basic cleaning: retain 2 decimal places
        clean = round(raw, 2)

        # Empty bin = 23 cm; full bin = 1 cm.
        EMPTY_DISTANCE_CM = 23.00
        FULL_DISTANCE_CM = 1.0

        percentage = round(
            max(
                0,
                min(
                    100,
                    (EMPTY_DISTANCE_CM - clean)
                    / (EMPTY_DISTANCE_CM - FULL_DISTANCE_CM)
                    * 100
                )
            ),
            2
        )
        
        if percentage >= 90:
            status = "full"
        elif percentage >= 50:
            status = "half"
        else:
            status = "low"

        cursor = conn.execute(
            """
            INSERT INTO sensor_readings
            (device_id, raw_distance_cm,
             clean_distance_cm, fill_percentage, fill_status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (data.device_id, raw, clean, percentage, status)
        )
        reading_id = cursor.lastrowid

        conn.execute(
            """
            UPDATE devices
            SET last_seen = CURRENT_TIMESTAMP, status = 'active'
            WHERE device_id = ?
            """,
            (data.device_id,)
        )

        # Create alert on transition into FULL status
        previous = conn.execute(
            """
            SELECT fill_status FROM sensor_readings
            WHERE device_id = ? AND reading_id != ?
            ORDER BY reading_id DESC LIMIT 1
            """,
            (data.device_id, reading_id)
        ).fetchone()

        if status == "full" and (
            previous is None or previous["fill_status"] != "full"
        ):
            conn.execute(
                """
                INSERT INTO alerts
                (device_id, reading_id, alert_type, message)
                VALUES (?, ?, 'FULL_BIN', 'Waste bin is full')
                """,
                (data.device_id, reading_id)
            )

            conn.execute(
                """
                INSERT INTO system_logs
                (device_id, event_type, description)
                VALUES (?, ?, ?)
                """,
                (
                    data.device_id,
                    "ALERT_CREATED",
                    "Waste bin reached FULL status; alert created"
                )
            )

        conn.commit()

    log_system_event(
        event_type="SENSOR_READING",
        description=(
            f"Reading saved: {percentage}% full, "
            f"status={status}, distance={clean} cm"
        ),
        device_id=data.device_id
    )

    return {
        "reading_id": reading_id,
        "device_id": data.device_id,
        "raw_distance_cm": raw,
        "clean_distance_cm": clean,
        "fill_percentage": percentage,
        "fill_status": status
    }

@app.get("/api/readings/latest",
         dependencies=[Depends(authenticate)])
def latest_reading(device_id: int = Query(gt=0)):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM sensor_readings
            WHERE device_id = ?
            ORDER BY reading_id DESC LIMIT 1
            """,
            (device_id,)
        ).fetchone()

    if not row:
        raise HTTPException(404, "No readings found")

    return dict(row)


@app.get("/api/readings/history",
         dependencies=[Depends(authenticate)])
def reading_history(
    device_id: int = Query(gt=0),
    start: str | None = None,
    end: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000)
):
    query = "SELECT * FROM sensor_readings WHERE device_id = ?"
    params = [device_id]

    for value in (start, end):
        if value is not None:
            try:
                # SQLite CURRENT_TIMESTAMP uses UTC YYYY-MM-DD HH:MM:SS.
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is not None:
                    parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
                normalized = parsed.strftime("%Y-%m-%d %H:%M:%S")
                if value == start:
                    start = normalized
                if value == end:
                    end = normalized
            except ValueError:
                raise HTTPException(422, "Use ISO date/time format")

    if start and end and start > end:
        raise HTTPException(422, "start must be before end")

    if start:
        query += " AND recorded_at >= ?"
        params.append(start)

    if end:
        query += " AND recorded_at <= ?"
        params.append(end)

    query += " ORDER BY recorded_at DESC, reading_id DESC LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return [dict(row) for row in rows]




@app.get("/api/alerts", dependencies=[Depends(authenticate)])
def list_alerts(device_id: int = Query(gt=0)):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM alerts WHERE device_id = ?
            ORDER BY alert_id DESC LIMIT 100
            """,
            (device_id,)
        ).fetchall()

    return [dict(row) for row in rows]




@app.patch("/api/alerts/{alert_id}/resolve", dependencies=[Depends(authenticate)])
def resolve_alert(alert_id: int, device_id: int = Query(gt=0)):
    """Mark one alert resolved without deleting its history."""
    with get_connection() as conn:
        alert = conn.execute(
            "SELECT * FROM alerts WHERE alert_id = ? AND device_id = ?",
            (alert_id, device_id),
        ).fetchone()
        if alert is None:
            raise HTTPException(status_code=404, detail="Alert not found for this device")
        if not alert["is_resolved"]:
            conn.execute(
                """UPDATE alerts
                   SET is_resolved = 1, resolved_at = CURRENT_TIMESTAMP
                   WHERE alert_id = ? AND device_id = ? AND is_resolved = 0""",
                (alert_id, device_id),
            )

            conn.execute(
                """
                INSERT INTO system_logs
                (device_id, event_type, description)
                VALUES (?, ?, ?)
                """,
                (
                    device_id,
                    "ALERT_RESOLVED",
                    f"Alert ID {alert_id} was resolved"
                )
            )

            conn.commit()
            
        updated = conn.execute(
            "SELECT * FROM alerts WHERE alert_id = ? AND device_id = ?",
            (alert_id, device_id),
        ).fetchone()
    return dict(updated)


@app.get("/api/devices/status",
         dependencies=[Depends(authenticate)])
def device_status(device_id: int = Query(gt=0)):
    with get_connection() as conn:
        device = conn.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
        if device is None:
            raise HTTPException(404, "Device not registered")
        result = dict(device)

    # A device is considered offline after 60 seconds
    # without a successful reading.
    if result["last_seen"] and result["status"] == "active":
        seen = datetime.fromisoformat(result["last_seen"].replace("Z", "+00:00"))
        if seen.tzinfo is None:
            seen = seen.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - seen).total_seconds()
        result["online"] = 0 <= age <= 60
    else:
        result["online"] = False

    return result


# Serve dashboard from the same origin as the API (no CORS or second server).
app.mount("/dashboard", StaticFiles(directory=Path(__file__).resolve().parent / "dashboard", html=True), name="dashboard")

@app.get("/", include_in_schema=False)
def dashboard_home():
    return RedirectResponse(url="/dashboard/")
