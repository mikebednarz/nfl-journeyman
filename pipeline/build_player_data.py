"""
NFL Journeyman — Phase 1 Data Pipeline

Pulls NFL roster data from nflverse via nfl_data_py, builds per-player
franchise histories, derives all display/hint fields, and outputs:
  1. data/candidates.json — players with 3+ franchises who played in 2000+
  2. data/autocomplete.json — all NFL players for guess autocomplete
"""

import json
import os
import re
from collections import OrderedDict

import nfl_data_py as nfl
import pandas as pd

ROSTER_YEARS = list(range(1999, 2026))
WEEKLY_ROSTER_YEARS = list(range(2002, 2026))
SEASONAL_ONLY_YEARS = [1999, 2000, 2001]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Relocated franchises → current canonical abbreviation
RELOCATION_MAP = {
    "SD": "LAC",
    "OAK": "LV",
    "STL": "LA",
    "SL": "LA",
    # nflverse legacy abbreviations → current standard
    "ARZ": "ARI",
    "BLT": "BAL",
    "CLV": "CLE",
    "HST": "HOU",
}

FRANCHISE_DISPLAY_NAMES = {
    "ARI": "Cardinals",
    "ATL": "Falcons",
    "BAL": "Ravens",
    "BUF": "Bills",
    "CAR": "Panthers",
    "CHI": "Bears",
    "CIN": "Bengals",
    "CLE": "Browns",
    "DAL": "Cowboys",
    "DEN": "Broncos",
    "DET": "Lions",
    "GB": "Packers",
    "HOU": "Texans",
    "IND": "Colts",
    "JAX": "Jaguars",
    "KC": "Chiefs",
    "LA": "Rams",
    "LAC": "Chargers",
    "LV": "Raiders",
    "MIA": "Dolphins",
    "MIN": "Vikings",
    "NE": "Patriots",
    "NO": "Saints",
    "NYG": "Giants",
    "NYJ": "Jets",
    "PHI": "Eagles",
    "PIT": "Steelers",
    "SEA": "Seahawks",
    "SF": "49ers",
    "TB": "Buccaneers",
    "TEN": "Titans",
    "WAS": "Commanders",
}


def normalize_team(abbr: str) -> str:
    if abbr is None or pd.isna(abbr):
        return None
    abbr = abbr.strip().upper()
    return RELOCATION_MAP.get(abbr, abbr)


def load_weekly_rosters() -> pd.DataFrame:
    """Load weekly rosters (2002+) — gives per-week team/status."""
    print(f"Loading weekly rosters for {WEEKLY_ROSTER_YEARS[0]}-{WEEKLY_ROSTER_YEARS[-1]}...")
    df = nfl.import_weekly_rosters(WEEKLY_ROSTER_YEARS)
    print(f"  Got {len(df)} rows")
    return df


def load_seasonal_rosters() -> pd.DataFrame:
    """Load seasonal rosters for 1999-2001 (no weekly data available)."""
    print(f"Loading seasonal rosters for {SEASONAL_ONLY_YEARS}...")
    df = nfl.import_seasonal_rosters(SEASONAL_ONLY_YEARS)
    print(f"  Got {len(df)} rows")
    return df


def build_player_team_seasons(weekly_df: pd.DataFrame, seasonal_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a dataframe of (player_id, team, season, first_week) where the player
    was active (ACT status) on the team. first_week tracks when they joined
    each team within a season for correct mid-season trade ordering.
    """
    # Weekly rosters (2002+): include ACT + RES (reserve players sometimes played),
    # exclude DEV (practice squad) and CUT
    weekly_active = weekly_df[weekly_df["status"].isin(["ACT", "RES", "INA"])].copy()
    weekly_active["canonical_team"] = weekly_active["team"].apply(normalize_team)
    weekly_pts = (
        weekly_active.groupby(["player_id", "canonical_team", "season"])
        .agg(
            player_name=("player_name", "first"),
            position=("position", "first"),
            college=("college", "first"),
            first_week=("week", "min"),
        )
        .reset_index()
    )

    # Seasonal rosters (1999-2001): use ACT status as proxy for played
    seasonal_active = seasonal_df[seasonal_df["status"] == "ACT"].copy()
    seasonal_active["canonical_team"] = seasonal_active["team"].apply(normalize_team)
    seasonal_pts = (
        seasonal_active.groupby(["player_id", "canonical_team", "season"])
        .agg(
            player_name=("player_name", "first"),
            position=("position", "first"),
            college=("college", "first"),
        )
        .reset_index()
    )
    seasonal_pts["first_week"] = 1  # No week data; assume start of season

    combined = pd.concat([seasonal_pts, weekly_pts], ignore_index=True)
    combined = combined.dropna(subset=["player_id", "canonical_team"])
    combined = combined.drop_duplicates(subset=["player_id", "canonical_team", "season"])
    combined = combined.sort_values(["player_id", "season", "first_week"])

    print(f"  Built {len(combined)} player-team-season rows for {combined['player_id'].nunique()} players")
    return combined


def build_franchise_histories(pts: pd.DataFrame) -> list[dict]:
    """
    For each player, build the ordered franchise list (career chronological).
    A franchise appears once per stint — if a player returns to a team,
    it appears again.
    """
    players = []

    for player_id, group in pts.groupby("player_id"):
        group = group.sort_values("season")

        name = group["player_name"].dropna().iloc[-1] if not group["player_name"].dropna().empty else None
        position = group["position"].dropna().iloc[-1] if not group["position"].dropna().empty else None
        college = group["college"].dropna().iloc[-1] if not group["college"].dropna().empty else None

        if name is None:
            continue

        # Build ordered franchise list: track stints, not unique teams.
        # If a player goes NYG → ARI → NYG, that's [NYG, ARI, NYG].
        # But consecutive seasons with the same team = one stint.
        franchises = []
        for _, row in group.iterrows():
            team = row["canonical_team"]
            if not franchises or franchises[-1]["abbr"] != team:
                franchises.append({
                    "abbr": team,
                    "display": FRANCHISE_DISPLAY_NAMES.get(team, team),
                })

        first_season = int(group["season"].min())
        last_season = int(group["season"].max())

        # Unique franchise count (for eligibility)
        unique_franchises = len(set(f["abbr"] for f in franchises))

        initials = derive_initials(name)

        players.append({
            "id": player_id,
            "full_name": name,
            "initials": initials,
            "position": position,
            "college": college,
            "franchises": franchises,
            "first_season": first_season,
            "last_season": last_season,
            "franchise_count": unique_franchises,
            "played_2000_plus": last_season >= 2000,
            # These three are manual curation fields — leave null for now
            "made_pro_bowl": None,
            "started_playoff_game": None,
            "career_starts": None,
            "eligible": None,  # Computed in Phase 2
            "difficulty": None,
            "approved": False,
        })

    print(f"  Built franchise histories for {len(players)} players")
    return players


def derive_initials(name: str) -> str:
    parts = name.split()
    if not parts:
        return ""
    return ".".join(p[0].upper() for p in parts if p) + "."


def filter_candidates(players: list[dict]) -> list[dict]:
    """Filter to players with 3+ franchises who played in 2000+."""
    candidates = [
        p for p in players
        if p["franchise_count"] >= 3 and p["played_2000_plus"]
    ]
    print(f"  {len(candidates)} candidates (3+ franchises, played 2000+)")
    return candidates


def build_autocomplete_index() -> list[dict]:
    """Build a name lookup for ALL NFL players (not just eligible ones)."""
    print("Building autocomplete index from import_players()...")
    players_df = nfl.import_players()

    autocomplete = []
    for _, row in players_df.iterrows():
        name = row.get("display_name")
        if not name or pd.isna(name):
            continue

        entry = {
            "id": row.get("gsis_id") or row.get("esb_id"),
            "name": name,
            "position": row.get("position"),
            "team": row.get("latest_team"),
        }

        # Add football_name as alias if different
        football_name = row.get("football_name")
        if football_name and not pd.isna(football_name) and football_name != name:
            first = row.get("first_name", "")
            last = row.get("last_name", "")
            if football_name != first:
                entry["alias"] = f"{football_name} {last}"

        autocomplete.append(entry)

    print(f"  Built autocomplete index with {len(autocomplete)} players")
    return autocomplete


def enrich_from_players_table(candidates: list[dict]) -> list[dict]:
    """Fill in missing college/position data from the nflverse players table."""
    print("Enriching candidates from players table...")
    players_df = nfl.import_players()

    lookup = {}
    for _, row in players_df.iterrows():
        gsis = row.get("gsis_id")
        if gsis and not pd.isna(gsis):
            lookup[gsis] = row

    filled_college = 0
    filled_position = 0
    for p in candidates:
        ref = lookup.get(p["id"])
        if ref is None:
            continue

        if not p["college"] or p["college"] == "None":
            college = ref.get("college_name")
            if college and not pd.isna(college):
                p["college"] = college
                filled_college += 1

        if not p["position"]:
            pos = ref.get("position")
            if pos and not pd.isna(pos):
                p["position"] = pos
                filled_position += 1

    print(f"  Filled {filled_college} colleges, {filled_position} positions")
    return candidates


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Step 1: Load roster data
    weekly_df = load_weekly_rosters()
    seasonal_df = load_seasonal_rosters()

    # Step 2: Build player-team-season records
    pts = build_player_team_seasons(weekly_df, seasonal_df)

    # Step 3: Build franchise histories
    all_players = build_franchise_histories(pts)

    # Step 4: Filter to candidates (3+ franchises, 2000+)
    candidates = filter_candidates(all_players)

    # Step 4b: Enrich missing fields from players table
    candidates = enrich_from_players_table(candidates)

    # Sort by franchise count descending for readability
    candidates.sort(key=lambda p: (-p["franchise_count"], p["full_name"]))

    # Step 5: Write candidates
    candidates_path = os.path.join(OUTPUT_DIR, "candidates.json")
    with open(candidates_path, "w") as f:
        json.dump(candidates, f, indent=2)
    print(f"\nWrote {len(candidates)} candidates to {candidates_path}")

    # Step 6: Build and write autocomplete index
    autocomplete = build_autocomplete_index()
    autocomplete_path = os.path.join(OUTPUT_DIR, "autocomplete.json")
    with open(autocomplete_path, "w") as f:
        json.dump(autocomplete, f, indent=2)
    print(f"Wrote {len(autocomplete)} autocomplete entries to {autocomplete_path}")

    # Step 7: Print some sample journeymen for spot-checking
    print("\n--- Sample journeymen (6+ franchises) ---")
    big_travelers = [p for p in candidates if p["franchise_count"] >= 6]
    for p in big_travelers[:15]:
        path = " → ".join(f["display"] for f in p["franchises"])
        print(f"  {p['full_name']} ({p['position']}, {p['first_season']}-{p['last_season']}): {path}")
        print(f"    Franchises: {p['franchise_count']}, College: {p['college']}, Initials: {p['initials']}")

    print("\n--- Sample 3-franchise players ---")
    three_team = [p for p in candidates if p["franchise_count"] == 3]
    for p in three_team[:10]:
        path = " → ".join(f["display"] for f in p["franchises"])
        print(f"  {p['full_name']} ({p['position']}): {path}")


if __name__ == "__main__":
    main()
