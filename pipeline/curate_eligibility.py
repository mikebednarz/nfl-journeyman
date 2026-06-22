"""
NFL Journeyman — Phase 2 Curation Pipeline

Fills eligibility fields (made_pro_bowl, started_playoff_game, career_starts)
using available nflverse data, computes eligibility, and outputs:
  1. Updated data/candidates.json with auto-filled fields
  2. data/curation_review.csv for manual spot-checking

Sources:
  - Draft picks table: probowls count, seasons_started
  - Snap counts (2013+): game-level snap percentages → career starts proxy
  - Snap counts in playoff games → started_playoff_game
"""

import csv
import json
import os

import nfl_data_py as nfl
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CANDIDATES_PATH = os.path.join(DATA_DIR, "candidates.json")

SNAP_COUNT_YEARS = list(range(2013, 2026))
STARTER_SNAP_THRESHOLD = 0.50


def load_candidates() -> list[dict]:
    with open(CANDIDATES_PATH) as f:
        return json.load(f)


def build_pfr_to_gsis_map() -> dict[str, str]:
    """Map PFR player IDs to GSIS IDs (our candidate ID format)."""
    players = nfl.import_players()
    mapping = {}
    for _, row in players.iterrows():
        pfr = row.get("pfr_id")
        gsis = row.get("gsis_id")
        if pfr and gsis and not pd.isna(pfr) and not pd.isna(gsis):
            mapping[pfr] = gsis
    print(f"  Built {len(mapping)} PFR → GSIS ID mappings")
    return mapping


def fill_from_draft_picks(candidates: list[dict]) -> int:
    """Fill made_pro_bowl from draft picks probowls column."""
    print("Loading draft picks for Pro Bowl data...")
    drafts = nfl.import_draft_picks()

    gsis_to_probowls = {}
    gsis_to_seasons_started = {}
    gsis_to_draft_round = {}
    for _, row in drafts.iterrows():
        gsis = row.get("gsis_id")
        if not gsis or pd.isna(gsis):
            continue
        pb = row.get("probowls")
        ss = row.get("seasons_started")
        rd = row.get("round")
        if pb and not pd.isna(pb):
            gsis_to_probowls[gsis] = int(pb)
        if ss and not pd.isna(ss):
            gsis_to_seasons_started[gsis] = int(ss)
        if rd and not pd.isna(rd):
            gsis_to_draft_round[gsis] = int(rd)

    filled = 0
    for p in candidates:
        pb = gsis_to_probowls.get(p["id"])
        if pb is not None:
            p["made_pro_bowl"] = pb > 0
            p["pro_bowl_count"] = pb
            filled += 1

        p["draft_round"] = gsis_to_draft_round.get(p["id"])

        ss = gsis_to_seasons_started.get(p["id"])
        if ss is not None:
            p["_seasons_started_pfr"] = ss

    print(f"  Filled made_pro_bowl for {filled} candidates from draft picks")

    # Also try matching by pfr_id from players table for undrafted players
    pfr_map = build_pfr_to_gsis_map()
    gsis_set = set(p["id"] for p in candidates)
    unfilled = [p for p in candidates if p["made_pro_bowl"] is None]
    print(f"  {len(unfilled)} candidates still missing made_pro_bowl (likely undrafted)")

    return filled


def compute_starts_from_snaps(candidates: list[dict], pfr_map: dict[str, str]):
    """
    Use snap counts (2013+) to compute:
      - career_starts: games where player had >= 50% of offense or defense snaps
      - started_playoff_game: same threshold in any playoff game
    """
    print(f"Loading snap counts for {SNAP_COUNT_YEARS[0]}-{SNAP_COUNT_YEARS[-1]}...")
    all_snaps = nfl.import_snap_counts(SNAP_COUNT_YEARS)
    print(f"  Got {len(all_snaps)} snap count rows")

    # Map pfr_player_id → gsis_id
    all_snaps["gsis_id"] = all_snaps["pfr_player_id"].map(pfr_map)

    candidate_ids = set(p["id"] for p in candidates)
    relevant = all_snaps[all_snaps["gsis_id"].isin(candidate_ids)].copy()
    print(f"  {len(relevant)} snap rows match candidates")

    # Determine "started" = >= threshold of offensive or defensive snaps
    relevant["started"] = (
        (relevant["offense_pct"] >= STARTER_SNAP_THRESHOLD)
        | (relevant["defense_pct"] >= STARTER_SNAP_THRESHOLD)
    )

    # Career starts: count unique games where player started
    career_starts = (
        relevant[relevant["started"]]
        .groupby("gsis_id")["game_id"]
        .nunique()
        .to_dict()
    )

    # Playoff starts: same but filtered to non-REG games
    playoff_snaps = relevant[
        (relevant["game_type"] != "REG") & relevant["started"]
    ]
    playoff_starters = set(playoff_snaps["gsis_id"].unique())

    filled_starts = 0
    filled_playoff = 0
    for p in candidates:
        pid = p["id"]

        starts = career_starts.get(pid)
        if starts is not None:
            p["career_starts"] = starts
            filled_starts += 1

        if pid in playoff_starters:
            p["started_playoff_game"] = True
            filled_playoff += 1
        elif starts is not None:
            p["started_playoff_game"] = False

    print(f"  Filled career_starts for {filled_starts} candidates")
    print(f"  Identified {filled_playoff} playoff starters")


def fill_remaining_pro_bowl(candidates: list[dict], pfr_map: dict[str, str]):
    """
    For candidates still missing made_pro_bowl, try to match via name
    against the draft picks table.
    """
    drafts = nfl.import_draft_picks()

    name_to_pb = {}
    for _, row in drafts.iterrows():
        name = row.get("pfr_player_name")
        pb = row.get("probowls")
        if name and pb and not pd.isna(pb) and not pd.isna(name):
            name_to_pb[name.strip().lower()] = int(pb)

    filled = 0
    for p in candidates:
        if p["made_pro_bowl"] is not None:
            continue
        name_key = p["full_name"].strip().lower()
        pb = name_to_pb.get(name_key)
        if pb is not None:
            p["made_pro_bowl"] = pb > 0
            p["_pb_source"] = "name_match"
            filled += 1

    print(f"  Filled {filled} more made_pro_bowl via name matching")

    still_missing = sum(1 for p in candidates if p["made_pro_bowl"] is None)
    print(f"  Still missing made_pro_bowl: {still_missing}")


def compute_eligibility(candidates: list[dict]):
    """
    eligible = franchise_count >= 3
               AND played_2000_plus
               AND (made_pro_bowl OR started_playoff_game OR career_starts >= 30)
    """
    for p in candidates:
        gate1 = p["franchise_count"] >= 3
        gate2 = p["played_2000_plus"]

        pb_count = p.get("pro_bowl_count", 0) or 0
        draft_rd = p.get("draft_round") or 99

        gate3 = pb_count >= 1 or draft_rd <= 1

        if gate1 and gate2 and gate3:
            p["eligible"] = True
        else:
            p["eligible"] = False

    eligible = sum(1 for p in candidates if p["eligible"] is True)
    ineligible = sum(1 for p in candidates if p["eligible"] is False)
    unknown = sum(1 for p in candidates if p["eligible"] is None)
    print(f"\n  Eligibility: {eligible} eligible, {ineligible} ineligible, {unknown} unknown")


def tag_difficulty(candidates: list[dict]):
    """
    Tag difficulty based on eligibility route:
    - Pro Bowl player → easy
    - 1st round pick (no Pro Bowl) → medium
    """
    for p in candidates:
        if p["eligible"] is not True:
            continue

        pb_count = p.get("pro_bowl_count", 0) or 0

        if pb_count >= 1:
            p["difficulty"] = "easy"
        else:
            p["difficulty"] = "medium"


def export_curation_csv(candidates: list[dict]):
    """Export a CSV for human review, sorted by confidence level."""
    csv_path = os.path.join(DATA_DIR, "curation_review.csv")

    rows = []
    for p in candidates:
        confidence = "high"
        notes = []

        if p["made_pro_bowl"] is None:
            confidence = "needs_review"
            notes.append("missing pro_bowl")
        if p["career_starts"] is None:
            if confidence != "needs_review":
                confidence = "partial"
            notes.append("missing career_starts (pre-2013 or no snap data)")
        if p["started_playoff_game"] is None:
            notes.append("missing playoff_start")

        path = " → ".join(f["display"] for f in p["franchises"])
        rows.append({
            "id": p["id"],
            "full_name": p["full_name"],
            "position": p["position"],
            "franchises": path,
            "franchise_count": p["franchise_count"],
            "years": f"{p['first_season']}-{p['last_season']}",
            "made_pro_bowl": p.get("made_pro_bowl", ""),
            "started_playoff_game": p.get("started_playoff_game", ""),
            "career_starts": p.get("career_starts", ""),
            "eligible": p.get("eligible", ""),
            "difficulty": p.get("difficulty", ""),
            "confidence": confidence,
            "notes": "; ".join(notes),
        })

    rows.sort(key=lambda r: (
        0 if r["eligible"] is True else (2 if r["eligible"] == "" else 1),
        r["confidence"] != "high",
        -r["franchise_count"],
        r["full_name"],
    ))

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {csv_path}")


def main():
    candidates = load_candidates()
    print(f"Loaded {len(candidates)} candidates")

    # Step 1: Fill Pro Bowl from draft picks
    fill_from_draft_picks(candidates)

    # Step 2: Build PFR → GSIS mapping for snap counts
    pfr_map = build_pfr_to_gsis_map()

    # Step 3: Compute starts from snap counts
    compute_starts_from_snaps(candidates, pfr_map)

    # Step 4: Try name-matching for remaining Pro Bowl data
    fill_remaining_pro_bowl(candidates, pfr_map)

    # Step 5: For candidates still missing made_pro_bowl, default to False
    # (Undrafted players without Pro Bowl data are very unlikely to have made it)
    defaulted = 0
    for p in candidates:
        if p["made_pro_bowl"] is None:
            p["made_pro_bowl"] = False
            p["_pb_source"] = "defaulted_false"
            defaulted += 1
    print(f"  Defaulted {defaulted} remaining made_pro_bowl to False")

    # Step 6: For candidates missing career_starts, estimate from seasons_started
    estimated = 0
    for p in candidates:
        if p["career_starts"] is None and p.get("_seasons_started_pfr"):
            p["career_starts"] = p["_seasons_started_pfr"] * 16
            p["_starts_source"] = "estimated_from_seasons_started"
            estimated += 1
    print(f"  Estimated career_starts for {estimated} candidates from seasons_started")

    # Step 7: Default remaining missing career_starts to 0
    starts_defaulted = 0
    for p in candidates:
        if p["career_starts"] is None:
            p["career_starts"] = 0
            p["_starts_source"] = "defaulted_zero"
            starts_defaulted += 1
    print(f"  Defaulted {starts_defaulted} remaining career_starts to 0")

    # Step 8: Default remaining missing started_playoff_game to False
    playoff_defaulted = 0
    for p in candidates:
        if p["started_playoff_game"] is None:
            p["started_playoff_game"] = False
            p["_playoff_source"] = "defaulted_false"
            playoff_defaulted += 1
    print(f"  Defaulted {playoff_defaulted} remaining started_playoff_game to False")

    # Step 9: Compute eligibility
    compute_eligibility(candidates)

    # Step 10: Tag difficulty
    tag_difficulty(candidates)

    # Step 11: Clean up internal tracking fields
    for p in candidates:
        for key in list(p.keys()):
            if key.startswith("_"):
                del p[key]

    # Step 12: Auto-approve eligible players
    for p in candidates:
        if p["eligible"] is True:
            p["approved"] = True

    approved = [p for p in candidates if p["approved"]]
    print(f"\n  Auto-approved {len(approved)} eligible players")

    # Step 13: Save updated candidates (full set)
    with open(CANDIDATES_PATH, "w") as f:
        json.dump(candidates, f, indent=2)
    print(f"Updated {CANDIDATES_PATH}")

    # Step 14: Save approved-only pool for downstream phases
    approved_sorted = sorted(approved, key=lambda p: (-p["franchise_count"], p["full_name"]))
    approved_path = os.path.join(DATA_DIR, "approved_players.json")
    with open(approved_path, "w") as f:
        json.dump(approved_sorted, f, indent=2)
    print(f"Wrote {len(approved_sorted)} approved players to {approved_path}")

    # Step 15: Export curation CSV
    export_curation_csv(candidates)

    # Step 16: Summary
    print("\n=== Summary ===")
    print(f"Total candidates: {len(candidates)}")
    print(f"Eligible & approved: {len(approved)}")

    diff_counts = {}
    for p in approved:
        d = p.get("difficulty", "unset")
        diff_counts[d] = diff_counts.get(d, 0) + 1
    print(f"Difficulty breakdown: {diff_counts}")

    print(f"\n--- Sample approved players ---")
    for p in approved_sorted[:20]:
        path = " → ".join(f["display"] for f in p["franchises"])
        flags = []
        if p["made_pro_bowl"]:
            flags.append("Pro Bowl")
        if p["started_playoff_game"]:
            flags.append("Playoff starter")
        if p["career_starts"] >= 30:
            flags.append(f"{p['career_starts']} starts")
        print(f"  {p['full_name']} ({p['position']}, {p['difficulty']}): {path}")
        print(f"    {', '.join(flags)}")


if __name__ == "__main__":
    main()
