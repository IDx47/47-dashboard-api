from fastapi import FastAPI
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
    track = payload.track.lower().strip()
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
    """Return top 10 fastest laps for a given track."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user, bike, time FROM laps WHERE track=? ORDER BY time ASC LIMIT 10", (track.lower(),))
    rows = c.fetchall()
    conn.close()

    if not rows:
        return {"error": f"No laps found for '{track}'"}

    result = []
    for user, bike, t in rows:
        formatted = f"{int(t//60)}'{t%60:06.3f}" if t >= 60 else f"{t:.3f}"
        result.append({"player": user, "bike": bike, "laptime": t, "formatted": formatted})

    return {"track": track, "entries": result}

# -------------------------------
# OPTIONAL: Serve dashboard HTML
# -------------------------------
@app.get("/dashboard", response_class=HTMLResponse)
def serve_dashboard():
    if not os.path.exists("index.html"):
        return "<h1>Dashboard not yet deployed.</h1>"
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


from flask import Flask, jsonify
import sqlite3

app = Flask(__name__)

@app.route('/')
def home():
    return "MX Bikes cloud DB ready!"

@app.route('/leaderboard/<track>')
def leaderboard(track):
    conn = sqlite3.connect('lap_times.db')
    c = conn.cursor()
    c.execute("SELECT player, bike, laptime FROM laps WHERE track=? ORDER BY laptime ASC LIMIT 10", (track.lower(),))
    rows = c.fetchall()
    conn.close()
    if not rows:
        return jsonify({"error": f"No laps found for '{track}'"})
    laps = [{"player": r[0], "bike": r[1], "laptime": r[2]} for r in rows]
    return jsonify({"track": track, "laps": laps})

# 🆕 New endpoint for all track names
@app.route('/api/tracks')
def api_tracks():
    conn = sqlite3.connect('lap_times.db')
    c = conn.cursor()
    c.execute("SELECT DISTINCT track FROM laps ORDER BY track ASC")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return jsonify(rows)
