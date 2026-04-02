import math
import time
import os
import requests
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = "postgresql://oskar:barcelona123@localhost:5432/barcelona_db"
engine = create_engine(DATABASE_URL)

BARCA_ID = 81
CAMP_NOU_LAT = 41.3809
CAMP_NOU_LON = 2.1228

API_KEY = os.getenv("FOOTBALL_API_KEY")
BASE_URL = os.getenv("FOOTBALL_STATS")
FOOTBALL_HEADERS = {"X-Auth-Token": API_KEY}

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {"User-Agent": "FCBarcelona-pipeline/1.0"}
WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Light showers", 81: "Showers", 82: "Heavy showers",
    95: "Thunderstorm", 96: "Thunderstorm w/ hail", 99: "Thunderstorm w/ heavy hail",
}


# ── GEOCODING ─────────────────────────────────────────────────────────────────

def fetch_venue_name(team_id: int) -> str | None:
    """Get stadium name from football-data.org team detail endpoint."""
    r = requests.get(f"{BASE_URL}/teams/{team_id}", headers=FOOTBALL_HEADERS, timeout=10)
    if r.status_code != 200:
        return None
    return r.json().get("venue")


def geocode_venue(venue_name: str) -> tuple[float, float] | None:
    """Return (lat, lon) for a stadium name via Nominatim."""
    for query in [venue_name, f"{venue_name} stadium"]:
        r = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 5},
            headers=NOMINATIM_HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        results = r.json()
        # prefer results tagged as a stadium
        stadium_hits = [x for x in results if x.get("type") == "stadium"]
        best = stadium_hits[0] if stadium_hits else (results[0] if results else None)
        if best:
            return float(best["lat"]), float(best["lon"])
        time.sleep(1)
    return None


def geocode_all_teams():
    with engine.connect() as conn:
        teams = pd.read_sql(
            text("SELECT id, name FROM teams WHERE latitude IS NULL"), conn
        )

    print(f"Geocoding {len(teams)} teams (via venue name)...")
    for _, row in teams.iterrows():
        team_id = int(row["id"])
        venue = fetch_venue_name(team_id)
        time.sleep(6)  # football-data.org free tier: 10 req/min

        if not venue:
            print(f"  {row['name']:35s} → no venue returned")
            continue

        coords = geocode_venue(venue)
        time.sleep(1)  # Nominatim rate limit

        if coords:
            lat, lon = coords
            with engine.connect() as conn:
                conn.execute(
                    text("UPDATE teams SET latitude = :lat, longitude = :lon WHERE id = :id"),
                    {"lat": lat, "lon": lon, "id": team_id}
                )
                conn.commit()
            print(f"  {row['name']:35s} | {venue:30s} → {lat:.4f}, {lon:.4f}")
        else:
            print(f"  {row['name']:35s} | {venue:30s} → not found in Nominatim")


# ── HAVERSINE DISTANCE ────────────────────────────────────────────────────────

def haversine(lat1, lon1, lat2, lon2) -> float:
    """Return great-circle distance in km."""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def enrich_travel():
    query = text("""
        SELECT m.id AS match_id, m.away_team_id,
               ht.latitude AS home_lat, ht.longitude AS home_lon
        FROM matches m
        JOIN teams ht ON ht.id = m.home_team_id
        WHERE m.away_team_id = :barca_id
          AND m.status = 'FINISHED'
          AND ht.latitude IS NOT NULL
          AND m.id NOT IN (SELECT match_id FROM travel_info)
    """)

    with engine.connect() as conn:
        away_games = pd.read_sql(query, conn, params={"barca_id": BARCA_ID})

    if away_games.empty:
        print("Travel info: nothing new to enrich")
        return

    rows = []
    for _, row in away_games.iterrows():
        dist = haversine(CAMP_NOU_LAT, CAMP_NOU_LON, row["home_lat"], row["home_lon"])
        rows.append({"match_id": int(row["match_id"]), "distance_km": round(dist, 1)})

    df = pd.DataFrame(rows)
    df.to_sql("travel_info", engine, if_exists="append", index=False)
    print(f"Travel info: loaded {len(df)} away matches")


# ── WEATHER ───────────────────────────────────────────────────────────────────

def fetch_weather_range(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    """Fetch a full date-range of hourly weather for a venue, with retries.
    Returns a dict keyed by 'YYYY-MM-DDTHH:00' -> weather snapshot."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,precipitation,windspeed_10m,weathercode",
        "timezone": "UTC",
    }
    for attempt in range(3):
        try:
            r = requests.get(WEATHER_URL, params=params, timeout=30)
            r.raise_for_status()
            hourly = r.json()["hourly"]
            return {
                ts: {
                    "temperature": hourly["temperature_2m"][i],
                    "precipitation": hourly["precipitation"][i],
                    "windspeed": hourly["windspeed_10m"][i],
                    "weather_code": hourly["weathercode"][i],
                }
                for i, ts in enumerate(hourly["time"])
            }
        except requests.exceptions.Timeout:
            wait = 10 * (attempt + 1)
            print(f"    Timeout, retrying in {wait}s... (attempt {attempt + 1}/3)")
            time.sleep(wait)
    return {}


def enrich_weather():
    query = text("""
        SELECT m.id AS match_id, m.match_date,
               ht.id AS home_team_id, ht.latitude, ht.longitude
        FROM matches m
        JOIN teams ht ON ht.id = m.home_team_id
        WHERE m.status = 'FINISHED'
          AND ht.latitude IS NOT NULL
          AND m.id NOT IN (SELECT match_id FROM weather_conditions)
    """)

    with engine.connect() as conn:
        matches = pd.read_sql(query, conn)

    if matches.empty:
        print("Weather: nothing new to enrich")
        return

    # Group matches by venue to fetch one date-range per stadium
    matches["match_date"] = pd.to_datetime(matches["match_date"])
    venues = matches.groupby(["home_team_id", "latitude", "longitude"])

    print(f"Fetching weather for {len(matches)} matches across {len(venues)} venues...")
    rows = []
    for (team_id, lat, lon), group in venues:
        start = group["match_date"].min().strftime("%Y-%m-%d")
        end = group["match_date"].max().strftime("%Y-%m-%d")
        print(f"  Venue team_id={team_id}: {len(group)} matches ({start} → {end})")

        weather_map = fetch_weather_range(lat, lon, start, end)
        if not weather_map:
            print(f"    Failed to fetch weather for team_id={team_id}, skipping")
            continue

        for _, row in group.iterrows():
            ts_key = row["match_date"].strftime("%Y-%m-%dT%H:00")
            w = weather_map.get(ts_key)
            if w:
                rows.append({"match_id": int(row["match_id"]), **w})
            else:
                print(f"    No data for match {row['match_id']} at {ts_key}")

        time.sleep(1)  # be polite to Open-Meteo between venue requests

    if rows:
        df = pd.DataFrame(rows)
        df.to_sql("weather_conditions", engine, if_exists="append", index=False)
        print(f"Weather: loaded {len(df)} matches")


# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Step 1: Geocoding team stadiums ===")
    geocode_all_teams()

    print("\n=== Step 2: Travel distances (away games) ===")
    enrich_travel()

    print("\n=== Step 3: Match weather conditions ===")
    enrich_weather()

    print("\nEnrichment complete.")
