import type { Player, AutocompleteEntry } from "./types";

let playersCache: Record<string, Player> | null = null;
let autocompleteCache: AutocompleteEntry[] | null = null;
let scheduleCache: Record<string, string> | null = null;

export async function getSchedule(): Promise<Record<string, string>> {
  if (scheduleCache) return scheduleCache;
  const res = await fetch("/data/daily_puzzles.json");
  scheduleCache = await res.json();
  return scheduleCache!;
}

export async function getPlayers(): Promise<Record<string, Player>> {
  if (playersCache) return playersCache;
  const res = await fetch("/data/approved_players.json");
  const arr: Player[] = await res.json();
  playersCache = {};
  for (const p of arr) {
    playersCache[p.id] = p;
  }
  return playersCache;
}

export async function getAutocomplete(): Promise<AutocompleteEntry[]> {
  if (autocompleteCache) return autocompleteCache;
  const res = await fetch("/data/autocomplete.json");
  autocompleteCache = await res.json();
  return autocompleteCache!;
}

export function getTodayDate(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

export async function getTodaysPuzzle(): Promise<{
  player: Player;
  date: string;
} | null> {
  const schedule = await getSchedule();
  const players = await getPlayers();

  const today = getTodayDate();
  const playerId = schedule[today];
  if (!playerId) return null;

  const player = players[playerId];
  if (!player) return null;

  return { player, date: today };
}

export async function getRandomPlayer(excludeId?: string): Promise<Player> {
  const players = await getPlayers();
  const all = Object.values(players).filter((p) => p.id !== excludeId);
  return all[Math.floor(Math.random() * all.length)];
}
