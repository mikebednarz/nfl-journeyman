import type { HintType } from "./types";

interface SolveEvent {
  date: string;
  playerId: string;
  guessCount: number;
  hintsUsed: HintType[];
  solvedAt: string;
}

const STORAGE_KEY = "journeyman_analytics";

function getHistory(): SolveEvent[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function logSolve(
  date: string,
  playerId: string,
  guessCount: number,
  hintsUsed: Set<HintType>
) {
  const event: SolveEvent = {
    date,
    playerId,
    guessCount,
    hintsUsed: Array.from(hintsUsed),
    solvedAt: new Date().toISOString(),
  };

  const history = getHistory();
  if (!history.some((e) => e.date === date)) {
    history.push(event);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    } catch {
      // storage full or unavailable
    }
  }

  console.log(
    `[Journeyman] Solved ${date}: ${guessCount} guesses, ${hintsUsed.size} hints`
  );
}

export function isDailyCompleted(date: string): boolean {
  return getHistory().some((e) => e.date === date);
}

export function getDailyResult(date: string): SolveEvent | null {
  return getHistory().find((e) => e.date === date) ?? null;
}

export function getStats() {
  const history = getHistory();
  if (history.length === 0) return null;

  const totalGuesses = history.reduce((sum, e) => sum + e.guessCount, 0);
  const totalHints = history.reduce((sum, e) => sum + e.hintsUsed.length, 0);

  return {
    gamesPlayed: history.length,
    avgGuesses: +(totalGuesses / history.length).toFixed(1),
    avgHints: +(totalHints / history.length).toFixed(1),
  };
}
