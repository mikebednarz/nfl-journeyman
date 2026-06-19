"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import type { AutocompleteEntry } from "@/lib/types";

interface PlayerSearchProps {
  autocomplete: AutocompleteEntry[];
  onGuess: (entry: AutocompleteEntry) => void;
  disabled: boolean;
}

export function PlayerSearch({
  autocomplete,
  onGuess,
  disabled,
}: PlayerSearchProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<AutocompleteEntry[]>([]);
  const [open, setOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const search = useCallback(
    (q: string) => {
      if (q.length < 2) {
        setResults([]);
        setOpen(false);
        return;
      }

      const lower = q.toLowerCase();
      const matches = autocomplete
        .filter((entry) => {
          const nameMatch = entry.name.toLowerCase().includes(lower);
          const aliasMatch = entry.alias?.toLowerCase().includes(lower);
          return nameMatch || aliasMatch;
        })
        .slice(0, 8);

      setResults(matches);
      setOpen(matches.length > 0);
      setSelectedIndex(0);
    },
    [autocomplete]
  );

  useEffect(() => {
    search(query);
  }, [query, search]);

  useEffect(() => {
    const selected = listRef.current?.children[selectedIndex] as HTMLElement;
    selected?.scrollIntoView({ block: "nearest" });
  }, [selectedIndex]);

  function handleSelect(entry: AutocompleteEntry) {
    onGuess(entry);
    setQuery("");
    setOpen(false);
    inputRef.current?.focus();
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!open) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (results[selectedIndex]) {
        handleSelect(results[selectedIndex]);
      }
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div className="relative w-full max-w-md">
      <input
        ref={inputRef}
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => query.length >= 2 && results.length > 0 && setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 200)}
        disabled={disabled}
        placeholder={disabled ? "Puzzle solved!" : "Type a player name..."}
        className="w-full px-4 py-3 rounded-lg border border-input bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
        autoComplete="off"
      />
      {open && (
        <div
          ref={listRef}
          className="absolute z-50 w-full mt-1 bg-popover border border-border rounded-lg shadow-lg overflow-hidden max-h-64 overflow-y-auto"
        >
          {results.map((entry, i) => (
            <button
              key={`${entry.id}-${i}`}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => handleSelect(entry)}
              className={`w-full px-4 py-3 text-left flex items-center justify-between transition-colors ${
                i === selectedIndex
                  ? "bg-accent text-accent-foreground"
                  : "hover:bg-accent/50"
              }`}
            >
              <span className="font-medium text-sm sm:text-base">{entry.name}</span>
              <span className="text-xs text-muted-foreground ml-2 shrink-0">
                {entry.position} · {entry.team}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
