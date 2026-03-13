import os
import json
from pathlib import Path
from datetime import datetime, timezone
import requests

BASE_URL = "https://www.cinemacity.hu/hu/data-api-service/v1/quickbook"
DATA_DIR = Path.cwd() / "data"

CINEMAS_FILE = DATA_DIR / "cinemas.json"
PRESENTATIONS_FILE = DATA_DIR / "presentations.json"
HISTORY_FILE = DATA_DIR / "history.jsonl"

# --- 1. CONFIGURATION ---
MARKET_ID = os.environ.get("MARKET_ID")
FILM_ID = os.environ.get("FILM_ID")
UNTIL_DATE = os.environ.get("UNTIL_DATE")

def fetch_data():    
    groups_url = f"{BASE_URL}/{MARKET_ID}/groups/with-film/{FILM_ID}/until/{UNTIL_DATE}"
    groups_res = requests.get(groups_url)
    groups_res.raise_for_status()
    groups = groups_res.json().get("body", {}).get("groups", [])
    
    cinemas_data = []
    presentations_data = []
    
    fetch_time = datetime.now(timezone.utc).isoformat(timespec='seconds')
    
    for group in groups:
        group_id = group["id"]
        
        dates_url = f"{BASE_URL}/{MARKET_ID}/dates/in-group/{group_id}/with-film/{FILM_ID}/until/{UNTIL_DATE}"
        dates_res = requests.get(dates_url)
        dates_res.raise_for_status()
        dates = dates_res.json().get("body", {}).get("dates", [])
        
        for date in dates:
            events_url = f"{BASE_URL}/{MARKET_ID}/cinema-events/in-group/{group_id}/with-film/{FILM_ID}/at-date/{date}"
            events_res = requests.get(events_url)
            events_res.raise_for_status()
            
            body = events_res.json().get("body", {})
            events = body.get("events", [])

            for c in body.get("cinemas", []):
                if not any(cd["id"] == c["id"] for cd in cinemas_data):
                    cinemas_data.append({
                        "id": c["id"],
                        "name": c.get("displayName")
                    })

            for event in events:
                presentations_data.append({
                    "id": event["id"],
                    "date": event["eventDateTime"],
                    "cinemaId": event["cinemaId"],
                    "availabilityRatio": event.get("availabilityRatio")
                })
                
    return cinemas_data, presentations_data, fetch_time

def save_data(cinemas, presentations, fetch_time):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(CINEMAS_FILE, "w", encoding="utf-8") as f:
        cinemas.sort(key=lambda c: c["id"])
        json.dump(cinemas, f, indent=4)
        
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        history_record = {
            "fetched_at": fetch_time,
            "availabilities": {p["id"]: p["availabilityRatio"] for p in presentations}
        }
        
        f.write(json.dumps(history_record) + "\n")
    
    with open(PRESENTATIONS_FILE, "w", encoding="utf-8") as f:
        presentations.sort(key=lambda p: p["id"])
        for p in presentations:
            p.pop("availabilityRatio", None)

        json.dump(presentations, f, indent=4)
    print(f"Successfully saved {len(cinemas)} cinemas and {len(presentations)} presentations.")

if __name__ == "__main__":
    cinemas_data, presentations_data, fetch_timestamp = fetch_data()
    save_data(cinemas_data, presentations_data, fetch_timestamp)