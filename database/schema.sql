CREATE TABLE IF NOT EXISTS competitions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(50),
    tla VARCHAR(5),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY,
    competition_code VARCHAR(10) REFERENCES competitions(code),
    season VARCHAR(10),
    matchday INTEGER,
    stage VARCHAR(30),
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

CREATE TABLE IF NOT EXISTS weather_conditions (
    match_id INTEGER PRIMARY KEY REFERENCES matches(id),
    temperature DOUBLE PRECISION,
    precipitation DOUBLE PRECISION,
    windspeed DOUBLE PRECISION,
    weather_code INTEGER
);

CREATE TABLE IF NOT EXISTS travel_info (
    match_id INTEGER PRIMARY KEY REFERENCES matches(id),
    distance_km DOUBLE PRECISION
);