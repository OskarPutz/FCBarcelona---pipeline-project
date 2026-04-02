import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://oskar:barcelona123@localhost:5432/barcelona_db"
engine = create_engine(DATABASE_URL)

st.set_page_config(page_title="FC Barcelona Dashboard", page_icon="🔵🔴", layout="wide")

st.title("FC Barcelona — Season Dashboard")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["La Liga Standings", "Barcelona Results", "UCL Results"])


# ── HELPERS ──────────────────────────────────────────────────────────────────

def result_badge(row, barca_id=81):
    home_id = row["home_team_id"]
    away_id = row["away_team_id"]
    winner = row["winner"]
    if winner is None:
        return "–"
    if winner == "HOME_TEAM":
        barca_won = home_id == barca_id
    elif winner == "AWAY_TEAM":
        barca_won = away_id == barca_id
    else:
        return "D"
    return "W" if barca_won else "L"


def color_result(val):
    colors = {"W": "background-color: #198754; color: white",
              "L": "background-color: #dc3545; color: white",
              "D": "background-color: #6c757d; color: white"}
    return colors.get(val, "")


def color_barca_row(row):
    if row["Club"] == "Barça":
        return ["font-weight: bold; background-color: #a8001c; color: white"] * len(row)
    return [""] * len(row)


# ── TAB 1: LA LIGA STANDINGS ──────────────────────────────────────────────────

with tab1:
    st.subheader("La Liga Standings")

    query = text("""
        SELECT
            s.position        AS "#",
            t.short_name      AS "Club",
            s.played_games    AS "P",
            s.won             AS "W",
            s.draw            AS "D",
            s.lost            AS "L",
            s.goals_for       AS "GF",
            s.goals_against   AS "GA",
            s.goal_difference AS "GD",
            s.points          AS "Pts"
        FROM standings s
        JOIN teams t ON t.id = s.team_id
        WHERE s.competition_code = 'PD'
        ORDER BY s.position
    """)

    with engine.connect() as conn:
        df_standings = pd.read_sql(query, conn)

    styled = (
        df_standings.style
        .apply(color_barca_row, axis=1)
        .set_properties(**{"text-align": "center"})
        .set_table_styles([{"selector": "th", "props": [("text-align", "center")]}])
    )

    st.dataframe(styled, use_container_width=True, hide_index=True)


# ── TAB 2: BARCA RESULTS (La Liga) ───────────────────────────────────────────

with tab2:
    st.subheader("Barcelona — La Liga Results")

    query = text("""
        SELECT
            m.matchday,
            m.match_date,
            ht.short_name   AS home_team,
            m.home_score,
            m.away_score,
            at.short_name   AS away_team,
            m.winner,
            m.home_team_id,
            m.away_team_id
        FROM matches m
        JOIN teams ht ON ht.id = m.home_team_id
        JOIN teams at ON at.id = m.away_team_id
        WHERE m.competition_code = 'PD'
          AND (m.home_team_id = 81 OR m.away_team_id = 81)
          AND m.status = 'FINISHED'
        ORDER BY m.match_date DESC
    """)

    with engine.connect() as conn:
        df_barca = pd.read_sql(query, conn)

    df_barca["Result"] = df_barca.apply(result_badge, axis=1)
    df_barca["Date"] = pd.to_datetime(df_barca["match_date"]).dt.strftime("%d %b %Y")
    df_barca["Score"] = (df_barca["home_score"].astype(int).astype(str)
                         + " – " +
                         df_barca["away_score"].astype(int).astype(str))

    display_cols = {
        "matchday": "MD",
        "Date": "Date",
        "home_team": "Home",
        "Score": "Score",
        "away_team": "Away",
        "Result": "Result",
    }
    df_display = df_barca.rename(columns=display_cols)[list(display_cols.values())]

    col1, col2, col3, col4 = st.columns(4)
    wins = (df_barca["Result"] == "W").sum()
    draws = (df_barca["Result"] == "D").sum()
    losses = (df_barca["Result"] == "L").sum()
    col1.metric("Played", len(df_barca))
    col2.metric("Wins", wins)
    col3.metric("Draws", draws)
    col4.metric("Losses", losses)

    st.markdown("")

    styled_results = (
        df_display.style
        .map(color_result, subset=["Result"])
        .set_properties(**{"text-align": "center"})
        .set_table_styles([{"selector": "th", "props": [("text-align", "center")]}])
    )
    st.dataframe(styled_results, use_container_width=True, hide_index=True)


# ── TAB 3: UCL RESULTS ────────────────────────────────────────────────────────

with tab3:
    st.subheader("Barcelona — Champions League Results")

    STAGE_LABELS = {
        "LEAGUE_STAGE":  "MD",
        "PLAYOFFS":      "Playoff Leg",
        "LAST_16":       "R16 Leg",
        "QUARTER_FINALS":"QF Leg",
        "SEMI_FINALS":   "SF Leg",
        "FINAL":         "Final",
    }

    query = text("""
        SELECT
            m.matchday,
            m.stage,
            m.match_date,
            ht.short_name   AS home_team,
            m.home_score,
            m.away_score,
            at.short_name   AS away_team,
            m.winner,
            m.home_team_id,
            m.away_team_id,
            m.status
        FROM matches m
        JOIN teams ht ON ht.id = m.home_team_id
        JOIN teams at ON at.id = m.away_team_id
        WHERE m.competition_code = 'CL'
          AND (m.home_team_id = 81 OR m.away_team_id = 81)
        ORDER BY m.match_date DESC
    """)

    with engine.connect() as conn:
        df_ucl = pd.read_sql(query, conn)

    df_ucl["Result"] = df_ucl.apply(
        lambda r: result_badge(r) if r["status"] == "FINISHED" else "–", axis=1
    )
    df_ucl["Date"] = pd.to_datetime(df_ucl["match_date"]).dt.strftime("%d %b %Y")
    df_ucl["Score"] = df_ucl.apply(
        lambda r: f"{int(r['home_score'])} – {int(r['away_score'])}" if r["status"] == "FINISHED" else "–", axis=1
    )
    df_ucl["Round"] = df_ucl.apply(
        lambda r: (
            f"MD {int(r['matchday'])}" if r["stage"] == "LEAGUE_STAGE"
            else f"{STAGE_LABELS.get(r['stage'], r['stage'])} {int(r['matchday'])}".strip()
            if pd.notna(r["matchday"]) else STAGE_LABELS.get(r["stage"], r["stage"])
        ), axis=1
    )

    display_cols = {
        "Round": "Round",
        "Date": "Date",
        "home_team": "Home",
        "Score": "Score",
        "away_team": "Away",
        "Result": "Result",
    }
    df_display_ucl = df_ucl.rename(columns=display_cols)[list(display_cols.values())]

    finished = df_ucl[df_ucl["status"] == "FINISHED"]
    if not finished.empty:
        col1, col2, col3, col4 = st.columns(4)
        wins = (finished["Result"] == "W").sum()
        draws = (finished["Result"] == "D").sum()
        losses = (finished["Result"] == "L").sum()
        col1.metric("Played", len(finished))
        col2.metric("Wins", wins)
        col3.metric("Draws", draws)
        col4.metric("Losses", losses)
        st.markdown("")

    styled_ucl = (
        df_display_ucl.style
        .map(color_result, subset=["Result"])
        .set_properties(**{"text-align": "center"})
        .set_table_styles([{"selector": "th", "props": [("text-align", "center")]}])
    )
    st.dataframe(styled_ucl, use_container_width=True, hide_index=True)
