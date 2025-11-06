# main.py — FastAPI cloud API with fuzzy leaderboard lookup + upload-db support (simplified + future-proof)
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
import sqlite3
import os

# -------------------------------
# FASTAPI SETUP
# -------------------------------
app = FastAPI(title="MX Bikes Cloud Leaderboard API")

DB_PATH = "lap_times.db"

# -------------------------------
# DATABASE SETUP
# -------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS laps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        track TEXT,
        time REAL,
        user TEXT,
        bike TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

init_db()

# -------------------------------
# MODELS
# -------------------------------
class LapEntry(BaseModel):
    player: str
    bike: str
    laptime: float
    session: str

class LapPayload(BaseModel):
    track: str
    laps: List[LapEntry]

# -------------------------------
# ROOT TEST
# -------------------------------
@app.get("/")
def root():
    return {"status": "online", "message": "MX Bikes cloud DB ready!"}

# -------------------------------
# POST /api/ingest
# -------------------------------
@app.post("/api/ingest")
def ingest(payload: LapPayload):
    """Receive lap data from the bot and insert/update into SQLite."""
    track = payload.track.strip()  # keep exact casing and spacing
    laps = payload.laps

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for lap in laps:
        player = lap.player.strip()
        bike = lap.bike.strip()
        time = float(lap.laptime)

        # Check if player already has a record for this track
        c.execute("SELECT time FROM laps WHERE track=? AND user=?", (track, player))
        row = c.fetchone()

        if row:
            # Update if faster
            if time < row[0]:
                c.execute("UPDATE laps SET time=?, bike=?, timestamp=CURRENT_TIMESTAMP WHERE track=? AND user=?",
                          (time, bike, track, player))
        else:
            # Insert new record
            c.execute("INSERT INTO laps (track, time, user, bike) VALUES (?, ?, ?, ?)",
                      (track, time, player, bike))

    conn.commit()
    conn.close()
    return {"status": "ok", "track": track, "count": len(laps)}

# -------------------------------
# GET /leaderboard/{track}
# -------------------------------
@app.get("/leaderboard/{track}")
def leaderboard(track: str):
    """Return top 10 fastest laps for a given track (case-insensitive fuzzy match)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    like_pattern = f"%{track.lower()}%"
    c.execute("SELECT user, bike, time FROM laps WHERE lower(track) LIKE ? ORDER BY time ASC LIMIT 10", (like_pattern,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        return {"error": f"No laps found for '{track}'"}

    result = []
    for user, bike, t in rows:
        formatted = f"{int(t//60)}'{t%60:06.3f}" if t >= 60 else f"{t:.3f}"
        result.append({
            "player": user,
            "bike": bike,
            "laptime": t,
            "formatted": formatted
        })

    return {"track": track, "laps": result}

# -------------------------------
# SIMPLE + FUTURE-PROOF: GET /api/tracks
# -------------------------------
@app.get("/api/tracks")
def api_tracks():
    """Return all track names exactly as stored in the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT track FROM laps ORDER BY track ASC")
    tracks = [r[0] for r in c.fetchall() if r[0]]
    conn.close()
    return tracks

# -------------------------------
# POST /api/upload-db
# -------------------------------
@app.post("/api/upload-db")
async def upload_db(file: UploadFile = File(...)):
    """Accept an uploaded lap_times.db and replace the server database."""
    contents = await file.read()
    with open(DB_PATH, "wb") as f:
        f.write(contents)
    return {"status": "uploaded", "bytes": len(contents)}

# -------------------------------
# OPTIONAL: Serve dashboard HTML
# -------------------------------
@app.get("/dashboard", response_class=HTMLResponse)
def serve_dashboard():
    if not os.path.exists("index.html"):
        return "<h1>Dashboard not yet deployed.</h1>"
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()
