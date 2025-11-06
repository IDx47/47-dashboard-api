from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List, Dict

app = FastAPI()

# In-memory storage for simplicity
track_data: Dict[str, List[Dict]] = {}


class LapEntry(BaseModel):
    player: str
    bike: str
    laptime: float
    session: str


class LapPayload(BaseModel):
    track: str
    laps: List[LapEntry]


@app.get("/")
def root():
    return {"status": "online", "message": "MX Bikes Dashboard API is running!"}


@app.post("/api/ingest")
def ingest(payload: LapPayload):
    """Receive lap data from your Discord bot."""
    track = payload.track.lower()
    entries = []

    # Keep each rider’s best only
    best_by_player = {}
    for lap in payload.laps:
        prev = best_by_player.get(lap.player)
        if not prev or lap.laptime < prev.laptime:
            best_by_player[lap.player] = lap

    for lap in best_by_player.values():
        entries.append(lap.dict())

    track_data[track] = entries
    return {"status": "ok", "track": track, "stored": len(entries)}


@app.get("/leaderboard/{track}")
def leaderboard(track: str):
    """Return top-10 laps for a given track."""
    t = track.lower()
    if t not in track_data:
        return {"error": f"No data found for track '{track}'"}
    laps = sorted(track_data[t], key=lambda x: x["laptime"])[:10]
    for lap in laps:
        lap["formatted"] = (
            f"{int(lap['laptime']//60)}'{lap['laptime']%60:06.3f}"
            if lap["laptime"] >= 60
            else f"{lap['laptime']:.3f}"
        )
    return {"track": track, "entries": laps}

from fastapi.responses import HTMLResponse

@app.get("/dashboard", response_class=HTMLResponse)
def serve_dashboard():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

