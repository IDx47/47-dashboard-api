from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "MX Bikes Dashboard API is running!"
    }

@app.get("/tracks")
def list_tracks():
    # Placeholder data — we'll replace this with REAL DB data later
    return [
        {"track": "tucson", "best": "1'09.971", "rider": "UD"},
        {"track": "albaida_sm", "best": "1'18.064", "rider": "TLN47"},
    ]
