CREATE TABLE IF NOT EXISTS competitions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(50),
    tla VARCHAR(5)
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY,
    competition_code VARCHAR(10) REFERENCES competitions(code),
    season VARCHAR(10),
    matchday INTEGER,
    match_date TIMESTAMP,
    status VARCHAR(20),
    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),
    home_score INTEGER,
    away_score INTEGER,
    winner VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS standings (
    id SERIAL PRIMARY KEY,
    season VARCHAR(10),
    competition_code VARCHAR(10) REFERENCES competitions(code),
    team_id INTEGER REFERENCES teams(id),
    position INTEGER,
    played_games INTEGER,
    won INTEGER,
    draw INTEGER,
    lost INTEGER,
    points INTEGER,
    goals_for INTEGER,
    goals_against INTEGER,
    goal_difference INTEGER,
    UNIQUE(season, competition_code, team_id)
);