# NFL Journeyman — v1 Build Spec

A daily NFL guessing game. Each day, every user is shown the same mystery player's career path (the franchises he played for, in order) and tries to identify him in as few guesses as possible, optionally unlocking hints. Think "Wordle for well-traveled NFL players."

This document is the source of truth for v1. Anything marked **Out of scope (v1)** should NOT be built yet — note it and move on.

---

## 1. Core gameplay loop

1. User lands on the daily puzzle (same for everyone, keyed to the calendar date).
2. The puzzle shows the day's player's **franchises in career order** (e.g. `Giants → Cardinals → Patriots → Jets`). Nothing else is shown initially.
3. User types a guess into a player-name input with autocomplete.
4. On a wrong guess, the user may **unlock the next hint** (hints unlock in a fixed order — see §3).
5. User keeps guessing until correct. **Unlimited guesses in v1.**
6. On a correct guess, show a simple win state (player name + full career summary). No score yet.

### v1 simplifications
- **Unlimited plays** — a user can replay/retry freely. No lockout, no "one attempt per day."
- **No scoring, no streaks, no leaderboard.** (See §9.)
- **No accounts required.** The daily puzzle is identical for all users, so v1 can run with no per-user state.

---

## 2. Eligibility rules (player pool)

A player qualifies for the daily pool **only if all three of the following are true**:

```
eligible =
      franchise_count >= 3
  AND played_in_2000_or_later == true
  AND ( made_pro_bowl == true
        OR started_playoff_game == true   // >= 1 career playoff start
        OR career_starts >= 30 )
```

Notes:
- The first two conditions are hard **AND** gates. The last three are an **OR** group — a player only needs to satisfy **one** of them.
- **"Played in 2000 or later"** = the player has at least one NFL season in 2000+. A career spanning 1996–2003 qualifies. A career ending in 1999 does not.
- **Franchise count** must use *franchises*, not raw team-season rows. See §5 for the relocation/cup-of-coffee normalization that makes this number correct.
- The **playoff-starter-only** players (qualify via playoff start but not Pro Bowl or 30+ starts) tend to be the most obscure. Tag them so they can be slotted as harder daily puzzles later (see `difficulty` in §4).

---

## 3. Hints

Hints unlock **one at a time, in this fixed order** (least → most revealing). Each wrong guess lets the user unlock the next one (or unlocking can be a manual button — implementer's choice, but order is fixed):

1. **Position** (e.g. `Safety`)
2. **Years active** (first season – last season, e.g. `2003–2014`)
3. **College** (e.g. `Oklahoma`)
4. **Initials** (e.g. `T.R.`)

There are exactly 4 hints in v1. Initials is intentionally near-giveaway and is the last resort.

---

## 4. Data model

### `players` (the curated pool)
| field | type | source / notes |
|---|---|---|
| `id` | string | stable key; use the nflverse `gsis_id` if available, else a slug |
| `full_name` | string | display + answer matching |
| `initials` | string | derived from `full_name` (Hint 4) |
| `position` | string | Hint 1 |
| `college` | string | Hint 3 |
| `franchises` | array | **ordered, career chronological**; each entry = canonical franchise + display label. This is the puzzle prompt. |
| `first_season` | int | for Hint 2 |
| `last_season` | int | for Hint 2 |
| `franchise_count` | int | derived from `franchises` after normalization (§5) |
| `played_2000_plus` | bool | `last_season >= 2000` |
| `made_pro_bowl` | bool | eligibility |
| `started_playoff_game` | bool | eligibility (>= 1 career playoff start) |
| `career_starts` | int | eligibility (the 30+ gate) |
| `eligible` | bool | computed from §2 |
| `difficulty` | enum? | optional: `easy` / `medium` / `hard` — for queue tiering. Playoff-starter-only ⇒ lean `hard`. |
| `approved` | bool | manual curation flag — only `approved` players can be scheduled |

### `daily_puzzles`
| field | type | notes |
|---|---|---|
| `date` | date (YYYY-MM-DD) | unique key |
| `player_id` | string | the answer for that date |

The displayed franchises, hints, etc. are all looked up from the `players` record — `daily_puzzles` only needs the date → answer mapping.

### Guess autocomplete index
Build a name-lookup list of **all** NFL players (not just eligible ones), with common aliases/nicknames, so users can type any name and have it resolve. Correctness = the resolved player matches the day's `player_id`. (Restricting autocomplete to only eligible players would leak the answer set.)

---

## 5. Data sourcing plan

### Primary source: nflverse (free)
Use the **nflverse** ecosystem via `nfl_data_py` (Python) — or `nflreadpy` / `nflreadr`. It cleanly covers every field shown to the user:

- **Rosters** give name, position, college, team, and season → derive `full_name`, `position`, `college`, the per-season team list, `first_season`, `last_season`, and `initials`.
- Aggregate a player's roster rows across seasons to produce the ordered `franchises` list.
- nflverse data goes back to 1999, which covers the 2000+ cutoff.

### The eligibility gates are the gap
`made_pro_bowl`, `started_playoff_game`, and `career_starts` are **not** cleanly available in nflverse (historical games-started in particular is spotty; snap counts only go back to 2012). The authoritative source is Pro Football Reference — but see the legal note below.

**v1 approach: manual curation.** The eligible pool (2000+, 3+ franchises) is only a few hundred players. Pull candidates + all display/hint fields from nflverse programmatically, then fill the three eligibility flags and do a final quality check by hand (a human cross-checking PFR pages in a browser is fine). Set `approved = true` only on hand-verified players. This is the curated daily queue.

### ⚠️ Do NOT scrape Pro Football Reference / Sports Reference
Their data-use policy explicitly prohibits building tools or websites on scraped data without permission, and they rate-limit/ban scrapers (~20 requests/min). A human looking things up is fine; an automated pipeline feeding the app is not. Stathead (their paid query tool, ~$9/mo) is fine as a manual research aid but has redistribution limits — don't wire it into production.

### Later / if automating or going commercial
License **SportsDataIO** (has an affordable "Discovery Lab" tier with real data, plus full commercial plans) or **Sportradar** (enterprise). These grant redistribution rights and can automate the Pro Bowl / playoff-start / starts gates. Not needed for v1.

### Field → source map
| field | v1 source |
|---|---|
| name, position, college, teams, years, initials | nflverse rosters (programmatic) |
| franchise_count | derived from normalized teams (see below) |
| made_pro_bowl | manual curation (PFR lookup by hand) / later: licensed API |
| started_playoff_game | manual curation / later: licensed API |
| career_starts | manual curation / later: licensed API |

### Data-cleaning rules (important — these prevent real bugs)
- **Normalize relocated franchises to a single canonical franchise** before counting. San Diego → LA Chargers, Oakland → LV Raiders, St. Louis → LA Rams, etc. are the *same* franchise; a player who moved with the team did **not** switch teams. nflverse provides a "norelocate" team-abbreviation mapping for this.
- **Only count a franchise where the player actually appeared in a game** (games played > 0), so practice-squad / "cup of coffee" rosterings don't inflate `franchise_count`.
- **Display label decision:** simplest v1 is to show each franchise with its *current* branding/logo. (Optional, harder, more flavorful later: show the team as it was branded during the player's stint.)

---

## 6. Tech stack

**Recommended: Next.js (App Router) + Tailwind CSS**, with **shadcn/ui** for the few components you need — notably the guess autocomplete/combobox. Why this fits *this* project specifically:

- **Share cards later.** This is a daily game you want to spread, so the share-result card matters. Next.js has first-class dynamic Open Graph image generation — exactly that surface, close to free when you get to it.
- **A clean home for the answer.** The "answer leaks to the client" issue (below) solves cleanly with a Next.js route handler: keep the day's answer server-side and check guesses against it. Same place scoring and anti-cheat will live later.
- **Custom look.** Tailwind gives full control over a distinctive, minimal, game-y feel instead of fighting a component library's defaults. (This is deliberately *not* a Material-style kit — that aesthetic reads enterprise on a consumer game.)
- **Easy hosting.** One-click Vercel deploy.

**Data layer:**
- **Pipeline:** Python + `nfl_data_py` to generate the candidate pool, display fields, and the full-player autocomplete index. Outputs CSV/JSON.
- **Storage:** v1 can read a static daily dataset (a generated JSON of `players` + `{date → player_id}`) — no database required. If you'd prefer queryable storage or expect to add accounts/scoring soon, put `players` and `daily_puzzles` in Postgres (Supabase is fine) and read from there.

**Known tradeoff:** if the day's answer ships to the browser, it's inspectable in the page source. Fine for a casual v1 test. Because you're on Next.js, the fix is cheap whenever it matters — move guess-checking into a route handler so the answer never reaches the client. Worth doing as soon as you add scoring.

The stack is a recommendation, not a mandate — swap any layer. If you want to go even lighter, **Astro** suits the "mostly-static page + one interactive island" shape of this game well; **SvelteKit** is great if you want less boilerplate and don't mind leaving React.

---

## 7. Implementation plan (phases)

Run each phase as its own focused build session, and verify its checkpoint before moving on. **Do not build the data pipeline and the UI in the same session** — data bugs are cheap to fix before the UI depends on them and expensive after.

### Phase 0 — Feel test (optional but recommended)
- **Build:** hardcode 3–5 journeymen and a throwaway version of the game screen. Play it.
- **Why:** the real risk in a daily game is whether the franchise-path-only prompt is fun and fairly difficult. Validate that before investing in the pipeline.
- **Done when:** you've played a few rounds and confirmed the mechanic feels right.

### Phase 1 — Data pipeline
- **Build:** Python + `nfl_data_py`. Pull 2000+ rosters; build per-player ordered franchise lists; derive name / position / college / years / initials; apply relocation normalization and the games-played franchise filter; compute `franchise_count` and `played_2000_plus`. Also generate the full-player autocomplete index (all players, not just eligible).
- **Done when:** you have a candidate CSV/JSON, and several journeymen you can name off the top of your head show the correct team order and counts.

### Phase 2 — Curation pass
- **Build:** fill `made_pro_bowl`, `started_playoff_game`, and `career_starts`; compute `eligible`; set `approved`; optionally tag `difficulty`. Partly manual — the tooling scaffolds the sheet, you verify. No PFR scraping.
- **Done when:** you have a vetted pool of approved players that all satisfy the §2 eligibility logic.

### Phase 3 — Daily scheduler
- **Build:** map approved players to dates (`daily_puzzles`). Decide ordering — random for now; ramp difficulty later via the `difficulty` tag.
- **Done when:** a date → answer queue exists and a given date reliably returns one player.

### Phase 4 — Frontend core
- **Build:** the daily puzzle screen — franchise-path display, guess input with full-player autocomplete, sequential hint unlock (position → years → college → initials), and win state. Wire it to the real data.
- **Done when:** you can play a full puzzle end to end on a real date.

### Phase 5 — Polish
- **Build:** mobile layout, empty/error states, and basic analytics on guesses-per-solve and hint usage (this data is what tells you how to design scoring later).
- **Done when:** it's shippable to your first testers.

---

## 8. Acceptance criteria (v1)

- Loading the app on a given date always shows the same puzzle for all users.
- The franchise path renders in correct career order.
- Autocomplete resolves any real NFL player name; only the exact answer counts as correct.
- Hints unlock strictly in order and reveal the correct values.
- Unlimited guesses and replays work with no lockout.
- Every scheduled player satisfies the §2 eligibility logic and is `approved`.

---

## 9. Out of scope (v1) — deferred, do not build yet

- **Scoring** (guesses + hints used), streaks, leaderboards.
- **One-attempt-per-day** lockout and per-user accounts/state.
- **Share grid / share card.** (Next.js OG image generation is the intended path when you get here.)
- **Difficulty curve** across the week (the `difficulty` tag is captured now but not yet used to schedule).
- **Multi-sport.** NFL only.
- **Automated eligibility** via licensed API (manual curation is the v1 plan).
- **Server-side answer validation** (cheap on Next.js, but only needed once cheating/scoring matters).
