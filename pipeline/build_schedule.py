"""
NFL Journeyman — Phase 3 Daily Scheduler

Maps dates to randomly selected approved players.
Each day's player is chosen via a date-seeded RNG so the result is
deterministic per date but players can repeat across days.

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
END_DATE = date(2030, 1, 1)
BASE_SEED = 42


def main():
    with open(APPROVED_PATH) as f:
        players = json.load(f)

    print(f"Loaded {len(players)} approved players")

    player_ids = [p["id"] for p in players]

    schedule = {}
    current_date = START_DATE
    while current_date < END_DATE:
        rng = random.Random(f"{BASE_SEED}-{current_date.isoformat()}")
        schedule[current_date.isoformat()] = rng.choice(player_ids)
        current_date += timedelta(days=1)

    print(f"Scheduled {len(schedule)} days: {START_DATE} to {END_DATE - timedelta(days=1)}")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(schedule, f, indent=2)
    print(f"Wrote {OUTPUT_PATH}")

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

    # Check for repeats in first 30 days
    first_30 = list(schedule.values())[:30]
    unique = len(set(first_30))
    print(f"\nFirst 30 days: {unique} unique players (of 30)")


if __name__ == "__main__":
    main()
