from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI()

# Temporary in-memory storage
lap_cache = []

# Data model your Discord bot will send
class LapEntry(BaseModel):
    player: str
    bike: str
    laptime: float
    session: str  # e.g. "race1", "race2", "practice"

class LapPayload(BaseModel):
    track: str
    laps: List[LapEntry]


@app.get("/")
def root():
    return {
        "status": "online",
        "message": "MX Bikes Dashboard API is running!"
    }


@app.post("/submit_laps")
async def submit_laps(payload: LapPayload):
    """
    Your Discord bot will send all parsed lap times as JSON.
    We store them in lap_cache for now.
    """
    lap_cache.clear()
    for lap in payload.laps:
        lap_cache.append(lap.dict())

    return {"status": "ok", "received": len(payload.laps)}


@app.get("/laps")
def get_laps():
    """
    Returns the most recently submitted laps.
    """
    return lap_cache
