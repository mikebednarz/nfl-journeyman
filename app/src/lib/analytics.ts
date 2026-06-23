import type { HintType } from "./types";

interface DailyResult {
  playerId: string;
  guessCount: number;
  hintsUsed: HintType[];
  gaveUp: boolean;
  solvedAt: string;
}

const DAILY_KEY_PREFIX = "journeyman_daily_";

function dailyKey(date: string): string {
  return `${DAILY_KEY_PREFIX}${date}`;
}

export function saveDailyResult(
  date: string,
  playerId: string,
  guessCount: number,
  hintsUsed: Set<HintType>,
  gaveUp: boolean
) {
  const result: DailyResult = {
    playerId,
    guessCount,
    hintsUsed: Array.from(hintsUsed),
    gaveUp,
    solvedAt: new Date().toISOString(),
  };

  try {
    localStorage.setItem(dailyKey(date), JSON.stringify(result));
  } catch {
    // storage full or unavailable
  }
}

export function getDailyResult(date: string): DailyResult | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(dailyKey(date));
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}
