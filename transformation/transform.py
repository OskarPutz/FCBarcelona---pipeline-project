import json
import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = "postgresql://oskar:barcelona123@localhost:5432/barcelona_db"
engine = create_engine(DATABASE_URL)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_raw(filename):
    with open(os.path.join(BASE_DIR, "data", "raw", f"{filename}.json"), "r") as f:
        return json.load(f)


def clear_tables():
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE standings, matches, teams, competitions RESTART IDENTITY CASCADE"))
        conn.commit()
    print("Tables cleared")


# ── COMPETITIONS ──
def transform_competitions():
    competitions = [
        {"code": "PD", "name": "Primera Division"},
        {"code": "CL", "name": "UEFA Champions League"},
    ]
    df = pd.DataFrame(competitions)
    df.to_sql("competitions", engine, if_exists="append", index=False)
    print(f"Loaded {len(df)} competitions")


# ── TEAMS ──
def transform_teams(barca_data, standings_data, ucl_data):
    teams = {}

    # extract from Barcelona matches
    for match in barca_data["matches"] and ucl_data["matches"]:
        for side in ["homeTeam", "awayTeam"]:
            team = match[side]
            if team["id"] not in teams:
                teams[team["id"]] = {
                    "id": team["id"],
                    "name": team["name"],
                    "short_name": team.get("shortName"),
                    "tla": team.get("tla")
                }

    # extract from La Liga standings
    for entry in standings_data["standings"][0]["table"]:
        team = entry["team"]
        if team["id"] not in teams:
            teams[team["id"]] = {
                "id": team["id"],
                "name": team["name"],
                "short_name": team.get("shortName"),
                "tla": team.get("tla")
            }


    # remove any teams with null id (TBD opponents in UCL knockouts)
    teams = {k: v for k, v in teams.items() if k is not None}

    df = pd.DataFrame(list(teams.values()))
    df.to_sql("teams", engine, if_exists="append", index=False)
    print(f"Loaded {len(df)} teams")


# ── MATCHES ──
def transform_matches(barca_data, ucl_data):
    matches = {}  # use dict keyed by id to avoid duplicates

    def extract_matches(data, matches_dict, filter_competitions=None):
        for m in data["matches"]:
            if m["status"] not in ("FINISHED", "IN_PLAY"):
                continue
            comp_code = m["competition"]["code"]
            if filter_competitions and comp_code not in filter_competitions:
                continue
            # skip if away or home team id is None (TBD knockout opponents)
            if not m["homeTeam"]["id"] or not m["awayTeam"]["id"]:
                continue
            matches_dict[m["id"]] = {
                "id": m["id"],
                "competition_code": comp_code,
                "season": m["season"]["startDate"][:4],
                "matchday": m.get("matchday"),
                "match_date": m["utcDate"],
                "status": m["status"],
                "home_team_id": m["homeTeam"]["id"],
                "away_team_id": m["awayTeam"]["id"],
                "home_score": m["score"]["fullTime"]["home"],
                "away_score": m["score"]["fullTime"]["away"],
                "winner": m["score"]["winner"]
            }

    # barca_data contains all competitions — filter to PD and CL only
    extract_matches(barca_data, matches, filter_competitions=["PD", "CL"])
    # ucl_data contains all UCL matches — no filter needed
    extract_matches(ucl_data, matches)

    df = pd.DataFrame(list(matches.values()))
    df.to_sql("matches", engine, if_exists="append", index=False)
    print(f"Loaded {len(df)} matches")


# ── STANDINGS ──
def transform_standings(standings_data):
    rows = []
    season = standings_data["season"]["startDate"][:4]

    for entry in standings_data["standings"][0]["table"]:
        rows.append({
            "season": season,
            "competition_code": "PD",
            "team_id": entry["team"]["id"],
            "position": entry["position"],
            "played_games": entry["playedGames"],
            "won": entry["won"],
            "draw": entry["draw"],
            "lost": entry["lost"],
            "points": entry["points"],
            "goals_for": entry["goalsFor"],
            "goals_against": entry["goalsAgainst"],
            "goal_difference": entry["goalDifference"]
        })

    df = pd.DataFrame(rows)
    df.to_sql("standings", engine, if_exists="append", index=False)
    print(f"Loaded {len(df)} standing rows")


if __name__ == "__main__":
    print("Loading raw data...")
    barca_data = load_raw("barca_matches")
    standings_data = load_raw("laliga_standings")
    ucl_data = load_raw("ucl_matches")

    print("\nClearing existing data...")
    clear_tables()

    print("\nTransforming and loading into PostgreSQL...")
    transform_competitions()
    transform_teams(barca_data, standings_data, ucl_data)
    transform_matches(barca_data, ucl_data)
    transform_standings(standings_data)

    print("\nAll done! Data is in PostgreSQL.")