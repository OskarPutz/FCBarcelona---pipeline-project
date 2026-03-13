import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FOOTBALL_API_KEY")
BASE_URL = os.getenv("FOOTBALL_STATS")
HEADERS = {"X-Auth-Token": API_KEY}

BarcelonaID = 81
LaLigaCode = "PD"
ChampionsLeagueCode = "CL"

def fetch_games():
    url = f"{BASE_URL}/teams/{BarcelonaID}/matches"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def fetch_laliga_standings():
    url = f"{BASE_URL}/competitions/{LaLigaCode}/standings"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()


def fetch_ucl_matches():
    url = f"{BASE_URL}/competitions/{ChampionsLeagueCode}/matches"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()


def save_raw(data, filename):
    os.makedirs("data/raw", exist_ok=True)
    with open(f"data/raw/{filename}.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved data/raw/{filename}.json")

if __name__ == "__main__":
    print("Fetching Barcelona matches...")
    barca_matches = fetch_games()
    save_raw(barca_matches, "barca_matches")

    print("Fetching La Liga standings...")
    laliga_standings = fetch_laliga_standings()
    save_raw(laliga_standings, "laliga_standings")

    print("Fetching UCL matches...")
    ucl_matches = fetch_ucl_matches()
    save_raw(ucl_matches, "ucl_matches")

    print("Done! Check data/raw/ folder.")