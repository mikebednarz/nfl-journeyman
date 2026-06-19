"""
NFL Journeyman — Phase 3 Daily Scheduler

Maps approved players to calendar dates. Random ordering for v1;
difficulty-based scheduling deferred to a later version.

Outputs data/daily_puzzles.json: { "YYYY-MM-DD": player_id, ... }
"""

import json
import os
import random
from datetime import date, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
APPROVED_PATH = os.path.join(DATA_DIR, "approved_players.json")
OUTPUT_PATH = os.path.join(DATA_DIR, "daily_puzzles.json")

START_DATE = date(2025, 7, 1)
SEED = 42


def main():
    with open(APPROVED_PATH) as f:
        players = json.load(f)

    print(f"Loaded {len(players)} approved players")

    player_ids = [p["id"] for p in players]
    rng = random.Random(SEED)
    rng.shuffle(player_ids)

    schedule = {}
    current_date = START_DATE
    for pid in player_ids:
        schedule[current_date.isoformat()] = pid
        current_date += timedelta(days=1)

    end_date = current_date - timedelta(days=1)
    print(f"Scheduled {len(schedule)} puzzles: {START_DATE} to {end_date}")
    print(f"Coverage: {(end_date - START_DATE).days + 1} days (~{len(schedule) // 365} years)")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(schedule, f, indent=2)
    print(f"Wrote {OUTPUT_PATH}")

    # Build a lookup for spot-checking
    id_to_name = {p["id"]: p["full_name"] for p in players}

    print("\n--- First 10 days ---")
    for i, (d, pid) in enumerate(schedule.items()):
        if i >= 10:
            break
        print(f"  {d}: {id_to_name.get(pid, pid)}")

    print("\n--- Sample week (today's date region) ---")
    today = date.today()
    for offset in range(7):
        d = (today + timedelta(days=offset)).isoformat()
        pid = schedule.get(d)
        if pid:
            print(f"  {d}: {id_to_name.get(pid, pid)}")
        else:
            print(f"  {d}: (no puzzle scheduled)")


if __name__ == "__main__":
    main()
