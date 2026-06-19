"use client";

import { useState, useEffect, useCallback } from "react";
import type { Player, AutocompleteEntry, HintType } from "@/lib/types";
import {
  getTodaysPuzzle,
  getAutocomplete,
  getRandomPlayer,
} from "@/lib/game-data";
import { logSolve, getDailyResult } from "@/lib/analytics";
import { FranchisePath } from "./franchise-path";
import { HintPanel } from "./hint-panel";
import { PlayerSearch } from "./player-search";
import { WinState } from "./win-state";

type GameMode = "daily" | "practice";

export function Game() {
  const [mode, setMode] = useState<GameMode>("daily");
  const [player, setPlayer] = useState<Player | null>(null);
  const [date, setDate] = useState<string>("");
  const [autocomplete, setAutocomplete] = useState<AutocompleteEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dailyAlreadySolved, setDailyAlreadySolved] = useState(false);
  const [dailyResult, setDailyResult] = useState<{
    guessCount: number;
    hintsUsed: number;
  } | null>(null);

  const [guesses, setGuesses] = useState<string[]>([]);
  const [revealedHints, setRevealedHints] = useState<Set<HintType>>(new Set());
  const [solved, setSolved] = useState(false);
  const [gaveUp, setGaveUp] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [puzzle, auto] = await Promise.all([
          getTodaysPuzzle(),
          getAutocomplete(),
        ]);
        if (puzzle) {
          setPlayer(puzzle.player);
          setDate(puzzle.date);

          const result = getDailyResult(puzzle.date);
          if (result) {
            setDailyAlreadySolved(true);
            setDailyResult({
              guessCount: result.guessCount,
              hintsUsed: result.hintsUsed.length,
            });
            setSolved(true);
          }
        }
        setAutocomplete(auto);
      } catch {
        setError("Failed to load puzzle data. Please refresh the page.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const resetGame = useCallback(() => {
    setGuesses([]);
    setRevealedHints(new Set());
    setSolved(false);
    setGaveUp(false);
  }, []);

  const startPractice = useCallback(async () => {
    setMode("practice");
    resetGame();
    setLoading(true);
    const randomPlayer = await getRandomPlayer();
    setPlayer(randomPlayer);
    setLoading(false);
  }, [resetGame]);

  const backToDaily = useCallback(async () => {
    setMode("daily");
    resetGame();
    setLoading(true);
    const puzzle = await getTodaysPuzzle();
    if (puzzle) {
      setPlayer(puzzle.player);
      setDate(puzzle.date);
      const result = getDailyResult(puzzle.date);
      if (result) {
        setDailyAlreadySolved(true);
        setDailyResult({
          guessCount: result.guessCount,
          hintsUsed: result.hintsUsed.length,
        });
        setSolved(true);
      }
    }
    setLoading(false);
  }, [resetGame]);

  function handleGuess(entry: AutocompleteEntry) {
    if (!player || solved) return;

    setGuesses((prev) => [...prev, entry.name]);

    if (entry.id === player.id) {
      setSolved(true);
      if (mode === "daily") {
        logSolve(date, player.id, guesses.length + 1, revealedHints);
        setDailyAlreadySolved(true);
        setDailyResult({
          guessCount: guesses.length + 1,
          hintsUsed: revealedHints.size,
        });
      }
    }
  }

  function handleRevealHint(type: HintType) {
    setRevealedHints((prev) => new Set(prev).add(type));
  }

  function handleGiveUp() {
    if (!player) return;
    setGaveUp(true);
    setSolved(true);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-muted-foreground animate-pulse">
          Loading puzzle...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 px-4">
        <p className="text-destructive text-center">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-secondary text-secondary-foreground rounded-md text-sm hover:bg-secondary/80 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!player) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] px-4">
        <p className="text-muted-foreground text-center">
          No puzzle available for today. Check back tomorrow!
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-4 sm:gap-6 w-full max-w-2xl mx-auto px-4 py-6 sm:py-8">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">Journeyman</h1>
        <div className="flex items-center justify-center gap-1 text-sm">
          <button
            onClick={backToDaily}
            className={`px-3 py-1 rounded-md transition-colors ${
              mode === "daily"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Daily
          </button>
          <button
            onClick={startPractice}
            className={`px-3 py-1 rounded-md transition-colors ${
              mode === "practice"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Practice
          </button>
        </div>
        {mode === "daily" && (
          <p className="text-xs text-muted-foreground">{date}</p>
        )}
      </div>

      {mode === "daily" && dailyAlreadySolved && dailyResult ? (
        <>
          <WinState
            player={player}
            guessCount={dailyResult.guessCount}
            hintsUsed={dailyResult.hintsUsed}
          />
          <button
            onClick={startPractice}
            className="px-5 py-2.5 bg-secondary text-secondary-foreground rounded-lg text-sm font-medium hover:bg-secondary/80 transition-colors"
          >
            Play Practice Mode
          </button>
        </>
      ) : solved ? (
        <>
          <WinState
            player={player}
            guessCount={guesses.length}
            hintsUsed={revealedHints.size}
            gaveUp={gaveUp}
          />
          {mode === "practice" && (
            <button
              onClick={startPractice}
              className="px-5 py-2.5 bg-secondary text-secondary-foreground rounded-lg text-sm font-medium hover:bg-secondary/80 transition-colors"
            >
              New Player
            </button>
          )}
        </>
      ) : (
        <>
          <div className="space-y-3 text-center">
            <p className="text-sm text-muted-foreground">
              Who traveled this path?
            </p>
            <FranchisePath franchises={player.franchises} />
          </div>

          <PlayerSearch
            autocomplete={autocomplete}
            onGuess={handleGuess}
            disabled={solved}
          />

          {guesses.length > 0 && (
            <div className="w-full max-w-md space-y-2">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Guesses ({guesses.length})
              </h3>
              <div className="space-y-1">
                {guesses.map((g, i) => (
                  <div
                    key={i}
                    className="px-4 py-2 rounded-md bg-destructive/10 text-destructive text-sm"
                  >
                    {g}
                  </div>
                ))}
              </div>
            </div>
          )}

          <HintPanel
            player={player}
            revealedHints={revealedHints}
            onReveal={handleRevealHint}
            onGiveUp={handleGiveUp}
          />

          {mode === "practice" && (
            <button
              onClick={startPractice}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Skip — New Player
            </button>
          )}
        </>
      )}
    </div>
  );
}
